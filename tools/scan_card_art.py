import struct, sys

ROM_PATH = ".workspace/trm-yum6.gba"

def bgr555_plausible(u16):
    # top bit often unused/ignored; rest is 5-5-5 BGR. Reject all-0xFFFF or all-0x0000 runs as uninformative.
    return True

def scan_palette_like_blocks(data, block=0x80, min_run=8):
    """Look for runs of 0x80-byte blocks (64 x u16) that look like plausible BGR555 palettes:
    first entry often 0x0000 or 0x7FFF (transparent/white), values within sane range, not pure 0xFF filler."""
    n = len(data)
    candidates = []
    i = 0
    run_start = None
    while i + block <= n:
        chunk = data[i:i+block]
        vals = struct.unpack_from('<64H', chunk, 0)
        nonzero = sum(1 for v in vals if v != 0)
        allFF = all(v == 0xFFFF for v in vals)
        allsame = len(set(vals)) == 1
        plausible = (nonzero > 10) and not allFF and not allsame
        if plausible:
            if run_start is None:
                run_start = i
        else:
            if run_start is not None:
                run_len = (i - run_start) // block
                if run_len >= min_run:
                    candidates.append((run_start, i, run_len))
                run_start = None
        i += block
    if run_start is not None:
        run_len = (i - run_start) // block
        if run_len >= min_run:
            candidates.append((run_start, i, run_len))
    return candidates

def main():
    data = open(ROM_PATH, 'rb').read()
    print("ROM size:", hex(len(data)))
    cands = scan_palette_like_blocks(data)
    print(f"found {len(cands)} palette-like run candidates (>= 8 consecutive 0x80-byte blocks)")
    for start, end, runlen in cands[:50]:
        print(f"  file_offset {hex(start)}-{hex(end)}  runlen(cards)={runlen}")

if __name__ == "__main__":
    main()
