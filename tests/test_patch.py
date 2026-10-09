#!/usr/bin/env python3
"""Tests for the opponent-turn-navigation ROM patch (tools/build_patch.py).

Run:  python3 tests/test_patch.py      (plain, prints PASS/FAIL/SKIP)
 or:  pytest tests/test_patch.py

The tests cover what can be checked without an emulator:
  - the stub assembles and is valid ARMv4T Thumb (16-bit, except BL),
  - the hook re-encodes to `bl <stub>`,
  - applying the patch to a clean ROM gives the expected CRC32,
  - the generated IPS, applied to a clean ROM, reproduces the patched ROM,
  - exactly the stub + hook bytes change, nowhere else,
  - the stub's literal pool holds the documented RAM/ROM addresses.

Tests that need the base ROM skip cleanly if it is absent (it is gitignored at
.workspace/trm-yum6.gba). Tests that need keystone/capstone skip if unavailable.
The expected base ROM is WC06 `trm-yum6.gba`, CRC32 0xF968A196.
"""
import os
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

CLEAN_CRC = 0xF968A196
PATCHED_CRC = 0xE0C3D7F0

try:
    import build_patch as bp
    HAVE_BP = True
except Exception as e:                       # keystone/capstone missing
    HAVE_BP = False
    BP_ERR = str(e)

ROM_PATH = os.path.join(ROOT, '.workspace', 'trm-yum6.gba')


class Skip(Exception):
    pass


def skip(msg):
    """Skip in a way both the plain runner and pytest understand."""
    if 'pytest' in sys.modules:              # only true when running under pytest
        import pytest
        pytest.skip(msg)
    raise Skip(msg)


def _need_bp():
    if not HAVE_BP:
        skip('keystone/capstone not importable: %s' % BP_ERR)


def _clean_rom():
    _need_bp()
    if not os.path.exists(ROM_PATH):
        skip('base ROM not present at %s' % ROM_PATH)
    data = open(ROM_PATH, 'rb').read()
    if zlib.crc32(data) & 0xFFFFFFFF != CLEAN_CRC:
        skip('ROM at %s is not the expected base (CRC mismatch)' % ROM_PATH)
    return data


def apply_ips(src, patch):
    """Apply an IPS patch to src bytes; return the result."""
    assert patch[:5] == b'PATCH', 'not an IPS file'
    out = bytearray(src)
    i = 5
    while True:
        rec = patch[i:i + 3]
        if rec == b'EOF':
            break
        off = int.from_bytes(patch[i:i + 3], 'big'); i += 3
        size = int.from_bytes(patch[i:i + 2], 'big'); i += 2
        if size == 0:                        # RLE record
            rle = int.from_bytes(patch[i:i + 2], 'big'); i += 2
            val = patch[i]; i += 1
            data = bytes([val]) * rle
        else:
            data = patch[i:i + size]; i += size
        if off + len(data) > len(out):
            out.extend(b'\x00' * (off + len(data) - len(out)))
        out[off:off + len(data)] = data
    return bytes(out)


# ---- tests ----

def test_stub_is_valid_thumb1():
    _need_bp()
    stub, hook = bp.assemble()
    code_len = bp.verify(stub)               # raises on a non-Thumb-1 code insn
    assert 0 < code_len < len(stub)
    assert len(hook) == 4                     # a single Thumb BL


def test_hook_encodes_to_bl_stub():
    _need_bp()
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
    _, hook = bp.assemble()
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    ins = list(md.disasm(hook, bp.HOOK_ADDR))[0]
    assert ins.mnemonic == 'bl'
    assert int(ins.op_str.lstrip('#'), 16) == bp.STUB_ADDR


def test_literal_pool_has_documented_addresses():
    _need_bp()
    import struct
    stub, _ = bp.assemble()
    words = set(struct.unpack_from('<I', stub, o)[0]
                for o in range(0, len(stub) - 3, 2))
    for addr in (bp.TURN, bp.CTL, bp.MODE, bp.NEWKEYS, bp.LOCAL,
                 bp.DUEL + 0x1D54, bp.DUEL + 0x1D64):
        assert addr in words, 'missing literal 0x%08X' % addr


def test_stub_calls_readkeys():
    _need_bp()
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
    stub, _ = bp.assemble()
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    targets = [int(i.op_str.lstrip('#'), 16)
               for i in md.disasm(stub, bp.STUB_ADDR) if i.mnemonic == 'bl']
    assert bp.READKEYS in targets, 'stub does not call ReadKeys (0x%08X)' % bp.READKEYS


def test_patched_rom_has_expected_crc():
    clean = _clean_rom()
    patched, _ips, _changes = bp.build_patched(clean)
    assert len(patched) == len(clean)
    assert zlib.crc32(patched) & 0xFFFFFFFF == PATCHED_CRC


def test_ips_reproduces_patched_rom():
    clean = _clean_rom()
    patched, ips, _ = bp.build_patched(clean)
    assert apply_ips(clean, ips) == patched


def test_only_stub_and_hook_bytes_change():
    clean = _clean_rom()
    patched, _ips, changes = bp.build_patched(clean)
    allowed = set()
    for off, data in changes:
        allowed.update(range(off, off + len(data)))
    diff = set(i for i in range(len(clean)) if clean[i] != patched[i])
    assert diff <= allowed, 'unexpected bytes changed: %s' % sorted(diff - allowed)[:8]
    assert diff, 'no bytes changed at all'


def test_stub_region_was_free():
    clean = _clean_rom()
    s = bp.STUB_ADDR - bp.ROM_BASE
    stub, _ = bp.assemble()
    assert all(b == 0 for b in clean[s:s + len(stub)]), 'stub landing zone not zero-filled'


def _run():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith('test_') and callable(v)]
    n_pass = n_skip = n_fail = 0
    for t in tests:
        try:
            t()
            print('PASS', t.__name__)
            n_pass += 1
        except Skip as s:
            print('SKIP', t.__name__, '--', s)
            n_skip += 1
        except AssertionError as a:
            print('FAIL', t.__name__, '--', a)
            n_fail += 1
    print('\n%d passed, %d skipped, %d failed' % (n_pass, n_skip, n_fail))
    return 1 if n_fail else 0


if __name__ == '__main__':
    sys.exit(_run())
