#!/usr/bin/env python3
"""Build the opponent-turn-navigation ROM patch for trm-yum6.gba.

What it does, permanently in the ROM:
  - Adds a small Thumb stub in free space (a zero-padding run inside a graphics
    bank at STUB_ADDR, within BL range of the hook).
  - Redirects the duel tick's call to the field-step function
    (`bl 0x080951CC` at HOOK_ADDR) through the stub.

The stub, on the CPU's turn (controller[turnPlayer] == 1):
  - if field mode is 0 and Select is newly pressed, turns field mode on
    (the SetFieldMode(1) side-writes), so the field screen opens and the duel
    logic pauses — you can move the cursor and view cards;
  - while field mode is on, strips A from newKeys so the command menu can't
    open (no acting out of turn). B is the game's own exit (sets mode 0).
Then it tail-calls the original field-step, preserving its return value.

This mechanism was validated live first (see docs/OPPONENT_TURN_NAVIGATION.md).

Requires keystone-engine (assembler) and capstone (verification).
Usage: python3 tools/build_patch.py
Outputs (next to the ROM, under .workspace/output/):
  trm-yum6-oppnav.gba   patched ROM
  oppnav.ips            IPS patch (apply to a clean trm-yum6.gba)
"""
import os
import struct

from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB

ROM_BASE = 0x08000000
# Hook the FIRST bl of the duel tick (`bl 0x08093598` at 0x08094D1C). That call
# runs every frame the tick runs — unlike the later `bl 0x080951CC`, which is
# gated behind a busy-check and is often skipped during the CPU's turn. The
# stub does its work, then tail-calls 0x08093598 (which takes no args and sets
# its own r0, so clobbering r0-r3 is safe) so its return still drives the
# tick's busy-check.
HOOK_ADDR = 0x08094D1C
ORIG_TARGET = 0x08093598
STUB_ADDR = 0x0800F700      # aligned, inside a 0x6C1-byte zero run; unreferenced

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ROM = os.path.join(ROOT, '.workspace', 'trm-yum6.gba')
OUTDIR = os.path.join(ROOT, '.workspace', 'output')

STUB_SRC = '''
.thumb
start:
    ldr  r0, Lturn
    ldr  r0, [r0]
    lsls r0, r0, #31
    lsrs r0, r0, #29          /* r0 = turnPlayer * 4 */
    ldr  r1, Lctl
    ldr  r0, [r1, r0]         /* controller[turnPlayer] */
    cmp  r0, #1
    bne  Lcall                /* not the CPU's turn */
    ldr  r2, Lmode
    ldr  r3, [r2]
    cmp  r3, #0
    bne  Lbrowse              /* already browsing -> strip A */
    ldr  r0, Lnewkeys
    ldrh r1, [r0]
    movs r3, #4               /* Select */
    tst  r1, r3
    beq  Lcall                /* Select not pressed */
    movs r3, #1               /* engage: SetFieldMode(1) writes */
    ldr  r0, Lmode
    str  r3, [r0]
    movs r3, #0
    ldr  r0, L1d54
    str  r3, [r0]
    ldr  r0, L1d58
    str  r3, [r0]
    ldr  r0, L1d7c
    str  r3, [r0]
    ldr  r0, Llocal
    ldr  r3, [r0]
    ldr  r0, L1d64
    str  r3, [r0]
    b    Lcall
Lbrowse:
    ldr  r0, Lnewkeys
    ldrh r1, [r0]
    movs r3, #1               /* A */
    bics r1, r3
    strh r1, [r0]
Lcall:
    ldr  r3, Lorig
    bx   r3
.align 2
Lturn:    .word 0x0201E1C8
Lctl:     .word 0x0201E2A8
Lmode:    .word 0x0201E22C
Lnewkeys: .word 0x03000188
L1d54:    .word 0x0201E234
L1d58:    .word 0x0201E238
L1d7c:    .word 0x0201E25C
Llocal:   .word 0x0201E2A4
L1d64:    .word 0x0201E244
Lorig:    .word %d
''' % (ORIG_TARGET | 1)


def assemble():
    ks = Ks(KS_ARCH_ARM, KS_MODE_THUMB)
    stub, _ = ks.asm(STUB_SRC, STUB_ADDR)
    stub = bytes(stub)
    hook, _ = ks.asm('bl #0x%X' % STUB_ADDR, HOOK_ADDR)
    hook = bytes(hook)
    return stub, hook


def verify_thumb1(stub):
    """Every code instruction (before the literal pool) must be 16-bit."""
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    bx_off = None
    for i in md.disasm(stub, STUB_ADDR):
        if i.mnemonic == 'bx':
            bx_off = i.address - STUB_ADDR + 2
            break
    assert bx_off is not None, 'no bx (tail call) found'
    for i in md.disasm(stub[:bx_off], STUB_ADDR):
        assert len(i.bytes) == 2, 'non-Thumb-1 instruction: %x %s' % (
            i.address, i.mnemonic)
    return bx_off


def make_ips(changes):
    """changes: list of (offset, bytes). IPS, no RLE."""
    out = bytearray(b'PATCH')
    for off, data in changes:
        assert off < 0x1000000, 'IPS offset too large'
        i = 0
        while i < len(data):
            chunk = data[i:i + 0xFFFF]
            out += struct.pack('>I', off + i)[1:]      # 3-byte offset
            out += struct.pack('>H', len(chunk))       # 2-byte size
            out += chunk
            i += len(chunk)
    out += b'EOF'
    return bytes(out)


def main():
    rom = bytearray(open(ROM, 'rb').read())
    stub, hook = assemble()
    bx_off = verify_thumb1(stub)
    print('stub %d bytes (code %d + pool), hook %d bytes' %
          (len(stub), bx_off, len(hook)))

    # sanity: the hook site really is the original bl to ORIG_TARGET
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    orig = list(md.disasm(bytes(rom[HOOK_ADDR - ROM_BASE:HOOK_ADDR - ROM_BASE + 4]),
                          HOOK_ADDR))[0]
    assert orig.mnemonic == 'bl' and int(orig.op_str.lstrip('#'), 16) == ORIG_TARGET, \
        'hook site is not `bl 0x%X` (found %s %s)' % (ORIG_TARGET, orig.mnemonic, orig.op_str)

    # sanity: stub region is free (all zero) and long enough
    s = STUB_ADDR - ROM_BASE
    assert all(b == 0 for b in rom[s:s + len(stub)]), 'stub region not empty'

    # apply
    rom[s:s + len(stub)] = stub
    h = HOOK_ADDR - ROM_BASE
    rom[h:h + len(hook)] = hook

    # verify applied
    newhook = list(md.disasm(bytes(rom[h:h + 4]), HOOK_ADDR))[0]
    print('hook now: %08x %s %s' % (newhook.address, newhook.mnemonic, newhook.op_str))
    assert newhook.mnemonic == 'bl' and int(newhook.op_str.lstrip('#'), 16) == STUB_ADDR

    os.makedirs(OUTDIR, exist_ok=True)
    out_rom = os.path.join(OUTDIR, 'trm-yum6-oppnav.gba')
    open(out_rom, 'wb').write(rom)
    ips = make_ips([(s, stub), (h, hook)])
    out_ips = os.path.join(OUTDIR, 'oppnav.ips')
    open(out_ips, 'wb').write(ips)
    print('wrote', out_rom)
    print('wrote', out_ips, '(%d bytes)' % len(ips))


if __name__ == '__main__':
    main()
