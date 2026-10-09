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
# The duel-tick function (0x08094CD4) is invoked every frame through a
# function-pointer table: the dispatcher at 0x08094DAC reads table[subState]
# (table base 0x09E5AADC) and calls it via the trampoline 0x0810E5C8. We
# repoint table[1] (at 0x09E5AAE0, originally 0x08094CD5) to our stub, so the
# stub runs at the very top of every duel frame — before the tick's internal
# gates that otherwise skip the field-cursor chain during the CPU's turn. The
# stub then tail-calls the real tick (0x08094CD5), preserving its return value.
# (Hooking the tick's inner `bl`s does not work: they sit behind those gates.)
TABLE_PTR = 0x09E5AAE0      # table[1]; holds 0x08094CD5
ORIG_TARGET = 0x08094CD4    # the real duel tick the stub tail-calls
STUB_ADDR = 0x0800F700      # aligned, inside a 0x6C1-byte zero run; unreferenced

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ROM = os.path.join(ROOT, '.workspace', 'trm-yum6.gba')
OUTDIR = os.path.join(ROOT, '.workspace', 'output')

STUB_SRC = '''
.thumb
start:
    ldr  r0, Lmark           /* DEBUG marker: count stub executions */
    ldrb r1, [r0]
    adds r1, #1
    strb r1, [r0]
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
Lmark:    .word 0x03007F00
Lorig:    .word %d
''' % (ORIG_TARGET | 1)


def assemble():
    ks = Ks(KS_ARCH_ARM, KS_MODE_THUMB)
    stub, _ = ks.asm(STUB_SRC, STUB_ADDR)
    return bytes(stub)


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
    stub = assemble()
    bx_off = verify_thumb1(stub)
    print('stub %d bytes (code %d + pool)' % (len(stub), bx_off))

    # sanity: table[1] really holds ORIG_TARGET|1
    t = TABLE_PTR - ROM_BASE
    cur = struct.unpack_from('<I', rom, t)[0]
    assert cur == (ORIG_TARGET | 1), \
        'table[1] is 0x%08X, expected 0x%08X' % (cur, ORIG_TARGET | 1)

    # sanity: stub region is free (all zero) and long enough
    s = STUB_ADDR - ROM_BASE
    assert all(b == 0 for b in rom[s:s + len(stub)]), 'stub region not empty'

    # apply: write stub, repoint table[1] -> stub (Thumb)
    rom[s:s + len(stub)] = stub
    struct.pack_into('<I', rom, t, STUB_ADDR | 1)
    print('table[1] now: 0x%08X' % struct.unpack_from('<I', rom, t)[0])

    os.makedirs(OUTDIR, exist_ok=True)
    out_rom = os.path.join(OUTDIR, 'trm-yum6-oppnav.gba')
    open(out_rom, 'wb').write(rom)
    print('wrote', out_rom)

    # IPS can only address the first 16 MiB; the table pointer is past that, so
    # IPS cannot represent this patch. Emit a BPS instead (handles any offset).
    changes = [(s, stub), (t, struct.pack('<I', STUB_ADDR | 1))]
    if all(off < 0x1000000 for off, _ in changes):
        open(os.path.join(OUTDIR, 'oppnav.ips'), 'wb').write(make_ips(changes))
        print('wrote oppnav.ips')
    else:
        src = open(ROM, 'rb').read()
        open(os.path.join(OUTDIR, 'oppnav.bps'), 'wb').write(make_bps(src, bytes(rom)))
        print('wrote oppnav.bps (patch offset past 16 MiB -> BPS, not IPS)')


def make_bps(src, dst):
    """Minimal BPS: whole target as literal TargetRead chunks. Valid and simple."""
    import zlib

    def varint(n):
        out = bytearray()
        while True:
            x = n & 0x7F
            n >>= 7
            if n == 0:
                out.append(0x80 | x)
                break
            out.append(x)
            n -= 1
        return bytes(out)

    assert len(src) == len(dst), 'BPS diff assumes same length'
    body = bytearray(b'BPS1')
    body += varint(len(src))
    body += varint(len(dst))
    body += varint(0)                     # no metadata
    # Walk the output: SourceRead (action 0) over runs equal to source,
    # TargetRead (action 1) over runs that differ.
    i, n = 0, len(dst)
    while i < n:
        same = src[i] == dst[i]
        j = i + 1
        while j < n and (src[j] == dst[j]) == same:
            j += 1
        length = j - i
        if same:
            body += varint(((length - 1) << 2) | 0)       # SourceRead
        else:
            body += varint(((length - 1) << 2) | 1)       # TargetRead
            body += dst[i:j]
        i = j
    body += struct.pack('<I', zlib.crc32(src) & 0xFFFFFFFF)
    body += struct.pack('<I', zlib.crc32(dst) & 0xFFFFFFFF)
    body += struct.pack('<I', zlib.crc32(bytes(body)) & 0xFFFFFFFF)
    return bytes(body)


if __name__ == '__main__':
    main()
