#!/usr/bin/env python3
"""Quick Thumb disassembly of a ROM address range, with literal-pool values
resolved inline. Not a substitute for Ghidra (no code/data separation:
literal pools between functions disassemble as garbage), but fast for
reading one function once you know where it starts.

Also finds every 4-byte-aligned literal-pool word equal to a given value
(e.g. a RAM address), which is how the real code that touches a RAM
address is usually found in this ROM.

usage:
  disasm_thumb.py <rom> dis <start_addr> <end_addr>
  disasm_thumb.py <rom> lit <value> [<value_hi>]

Addresses are GBA bus addresses (ROM mapped at 0x08000000).
Requires capstone (`pip install capstone`).
"""
import struct
import sys

import capstone

ROM_BASE = 0x08000000


def disassemble(rom, start, end):
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    for ins in md.disasm(rom[start - ROM_BASE:end - ROM_BASE], start):
        extra = ''
        if ins.mnemonic == 'ldr' and '[pc' in ins.op_str:
            imm = int(ins.op_str.split('#')[-1].rstrip(']'), 16)
            pool = ((ins.address + 4) & ~3) + imm
            extra = ' ; =%08x' % struct.unpack_from('<I', rom, pool - ROM_BASE)[0]
        print('%08x: %-8s %s%s' % (ins.address, ins.mnemonic, ins.op_str, extra))


def find_literals(rom, lo, hi):
    for off in range(0, len(rom) - 3, 4):
        word = struct.unpack_from('<I', rom, off)[0]
        if lo <= word <= hi:
            print('%08x: %08x' % (off + ROM_BASE, word))


def main():
    rom = open(sys.argv[1], 'rb').read()
    mode = sys.argv[2]
    args = [int(a, 16) for a in sys.argv[3:]]
    if mode == 'dis':
        disassemble(rom, args[0], args[1])
    elif mode == 'lit':
        find_literals(rom, args[0], args[1] if len(args) > 1 else args[0])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
