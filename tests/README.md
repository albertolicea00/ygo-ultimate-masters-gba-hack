# Tests

## Run

```bash
python3 tests/test_patch.py     # plain runner: prints PASS / FAIL / SKIP
pytest tests/test_patch.py      # same tests under pytest, if installed
```

## What's covered

`test_patch.py` tests the opponent-turn-navigation ROM patch
(`tools/build_patch.py`) — everything checkable without an emulator:

- the Thumb stub assembles and is valid ARMv4T (16-bit instructions, except the
  one legal 32-bit `BL`);
- the hook re-encodes to `bl <stub>`;
- the stub actually calls `ReadKeys`, and its literal pool holds the documented
  RAM addresses;
- applying the patch to a clean ROM gives the expected CRC32 (`0xE0C3D7F0`);
- the generated IPS, applied to a clean ROM, reproduces the patched ROM exactly;
- **only** the stub + hook bytes change, nowhere else;
- the stub's landing zone in the ROM was genuinely free (zero-filled).

## Requirements & skipping

- Needs `keystone-engine` and `capstone` (`pip install keystone-engine capstone`;
  on macOS also `brew install keystone` for the native lib). Tests that need them
  skip cleanly if they're missing.
- Tests that need the base ROM read it from `.workspace/trm-yum6.gba`
  (gitignored). They skip — not fail — if it's absent or has the wrong CRC32,
  so the suite is safe to run in CI without the copyrighted ROM.

The emulator-level behaviour (Select engages, cursor moves, B exits, A blocked,
no desync) was validated live; the evidence and method are in
`docs/OPPONENT_TURN_NAVIGATION.md`. Those steps aren't automated here because they
need a running emulator and a reached duel.
