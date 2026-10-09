#!/usr/bin/env python3
"""Build the opponent-turn-navigation ROM patch for trm-yum6.gba.

Permanent change in the ROM:
  - A small Thumb stub in free space (a zero-padding run at STUB_ADDR).
  - The main loop's per-frame call to ReadKeys (`bl 0x080F4764` at HOOK_ADDR)
    is redirected through the stub. ReadKeys is polled once per frame regardless
    of whose turn it is, so the stub runs every single frame — the duel tick,
    by contrast, is skipped for most of the CPU's turn.

Each frame the stub calls ReadKeys (so newKeys is fresh), then, on the CPU's
turn (controller[turnPlayer] == 1):
  - if field mode is 0 and Select was just pressed, turns field mode on (the
    SetFieldMode(1) side-writes). The field screen then opens and the duel logic
    pauses, so you can move the cursor and view cards.
  - while field mode is on, strips A from newKeys so the command menu can't open
    (no acting out of turn). B is the game's own exit (it sets mode back to 0).

The mechanism was validated live first (docs/OPPONENT_TURN_NAVIGATION.md).

Requires keystone-engine (assembler) and capstone (verification).
Usage: python3 tools/build_patch.py
Outputs under .workspace/output/:
  trm-yum6-oppnav.gba   patched ROM
  oppnav.ips            IPS patch (apply to a clean trm-yum6.gba)
"""
import os
import struct

from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB

ROM_BASE = 0x08000000
HOOK_ADDR = 0x080F4B7A      # the main loop's `bl 0x080F4764` (ReadKeys), per frame
READKEYS = 0x080F4764       # the stub calls this itself, then does its work
STUB_ADDR = 0x0800F700      # aligned, inside a 0x6C1-byte zero run; unreferenced

# Live-confirmed addresses (docs/OPPONENT_TURN_NAVIGATION.md "Live validation")
TURN = 0x0201E1C8           # & 1 = turn player
CTL = 0x0201E2A8            # u32[2] controller type; 0 human, 1 CPU
MODE = 0x0201E22C           # field mode (0 off, 1 free browse)
NEWKEYS = 0x03000188        # gMain newKeys (just-pressed)
LOCAL = 0x0201E2A4          # this console's player index
DUEL = 0x0201C4E0           # +0x1D54/0x1D58/0x1D64/0x1D7C are SetFieldMode's fields

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ROM = os.path.join(ROOT, '.workspace', 'trm-yum6.gba')
OUTDIR = os.path.join(ROOT, '.workspace', 'output')

STUB_SRC = '''
.thumb
start:
    push {{lr}}
    bl   #{readkeys}          /* ReadKeys: refresh newKeys for this frame */
    ldr  r0, Lturn
    ldr  r0, [r0]
    lsls r0, r0, #31
    lsrs r0, r0, #29          /* r0 = turnPlayer * 4 */
    ldr  r1, Lctl
    ldr  r0, [r1, r0]         /* controller[turnPlayer] */
    cmp  r0, #1
    bne  Ldone                /* not the CPU's turn */
    ldr  r2, Lmode
    ldr  r3, [r2]
    cmp  r3, #0
    bne  Lbrowse              /* already browsing -> strip A */
    ldr  r0, Lnewkeys
    ldrh r1, [r0]
    movs r3, #4               /* Select */
    tst  r1, r3
    beq  Ldone                /* Select not just pressed */
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
    b    Ldone
Lbrowse:
    ldr  r0, Lnewkeys
    ldrh r1, [r0]
    movs r3, #1               /* A */
    bics r1, r3
    strh r1, [r0]
Ldone:
    pop  {{pc}}
.align 2
Lturn:    .word {turn}
Lctl:     .word {ctl}
Lmode:    .word {mode}
Lnewkeys: .word {newkeys}
L1d54:    .word {d1d54}
L1d58:    .word {d1d58}
L1d7c:    .word {d1d7c}
Llocal:   .word {local}
L1d64:    .word {d1d64}
'''.format(readkeys=READKEYS, turn=TURN, ctl=CTL, mode=MODE, newkeys=NEWKEYS,
           d1d54=DUEL + 0x1D54, d1d58=DUEL + 0x1D58, d1d7c=DUEL + 0x1D7C,
           local=LOCAL, d1d64=DUEL + 0x1D64)


def assemble():
    ks = Ks(KS_ARCH_ARM, KS_MODE_THUMB)
    stub, _ = ks.asm(STUB_SRC, STUB_ADDR)
    stub = bytes(stub)
    hook, _ = ks.asm('bl #0x%X' % STUB_ADDR, HOOK_ADDR)
    return stub, bytes(hook)


def verify(stub):
    """Code instructions must be 16-bit Thumb-1, except BL (the one valid
    32-bit Thumb-1 instruction). Returns the byte length of the code."""
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    end = None
    for i in md.disasm(stub, STUB_ADDR):
        if i.mnemonic == 'pop' and 'pc' in i.op_str:
            end = i.address - STUB_ADDR + len(i.bytes)
            break
    assert end is not None, 'no `pop {pc}` found'
    for i in md.disasm(stub[:end], STUB_ADDR):
        assert len(i.bytes) == 2 or i.mnemonic in ('bl', 'blx'), \
            'bad instruction: %x %s (%d bytes)' % (i.address, i.mnemonic, len(i.bytes))
    return end


def make_ips(changes):
    out = bytearray(b'PATCH')
    for off, data in changes:
        assert off < 0x1000000, 'IPS offset past 16 MiB'
        i = 0
        while i < len(data):
            chunk = data[i:i + 0xFFFF]
            out += struct.pack('>I', off + i)[1:]
            out += struct.pack('>H', len(chunk))
            out += chunk
            i += len(chunk)
    out += b'EOF'
    return bytes(out)


def main():
    rom = bytearray(open(ROM, 'rb').read())
    stub, hook = assemble()
    code_len = verify(stub)
    print('stub %d bytes (code %d + pool), hook %d bytes' % (len(stub), code_len, len(hook)))

    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    orig = list(md.disasm(bytes(rom[HOOK_ADDR - ROM_BASE:HOOK_ADDR - ROM_BASE + 4]), HOOK_ADDR))[0]
    assert orig.mnemonic == 'bl' and int(orig.op_str.lstrip('#'), 16) == READKEYS, \
        'hook site is not `bl 0x%X` (found %s %s)' % (READKEYS, orig.mnemonic, orig.op_str)

    s = STUB_ADDR - ROM_BASE
    assert all(b == 0 for b in rom[s:s + len(stub)]), 'stub region not empty'

    rom[s:s + len(stub)] = stub
    h = HOOK_ADDR - ROM_BASE
    rom[h:h + len(hook)] = hook

    newhook = list(md.disasm(bytes(rom[h:h + 4]), HOOK_ADDR))[0]
    print('hook now: %08x %s %s' % (newhook.address, newhook.mnemonic, newhook.op_str))
    assert newhook.mnemonic == 'bl' and int(newhook.op_str.lstrip('#'), 16) == STUB_ADDR

    os.makedirs(OUTDIR, exist_ok=True)
    out_rom = os.path.join(OUTDIR, 'trm-yum6-oppnav.gba')
    open(out_rom, 'wb').write(rom)
    open(os.path.join(OUTDIR, 'oppnav.ips'), 'wb').write(make_ips([(s, stub), (h, hook)]))
    print('wrote', out_rom)
    print('wrote oppnav.ips')


if __name__ == '__main__':
    main()
