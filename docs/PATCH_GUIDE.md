# Opponent-turn navigation patch — full guide

Move the field cursor and view cards during the CPU's turn in Yu-Gi-Oh!
Ultimate Masters (WC06, `trm-yum6.gba`). This guide covers applying it, playing
with it, rebuilding it, testing it, and how it works.

- Quickstart: `patch/README.md`
- Design / reverse-engineering write-up: `docs/OPPONENT_TURN_NAVIGATION.md`

---

## 1. What you need

- A clean `trm-yum6.gba` — **CRC32 `0xF968A196`** (the WC06 / "Ultimate
  Masters" base this project targets).
- The patch: `patch/oppnav.ips` (142 bytes).
- Any IPS patcher (see below).

The patch changes **124 bytes**: a 120-byte code stub in unused space at ROM
`0x0800F700`, and one redirected call (4 bytes) at `0x080F4B7A`. It touches no
save data, so existing `.sav` files keep working.

---

## 2. Apply the patch

Pick one patcher. All produce the same output — **patched CRC32 `0xE0C3D7F0`**.

### Option A — rom-patcher-js (browser, nothing to install)
1. Open <https://www.marcrobledo.com/RomPatcher.js/>.
2. ROM file → your clean `trm-yum6.gba`.
3. Patch file → `patch/oppnav.ips`.
4. **Apply patch** → it downloads the patched ROM.

### Option B — Flips (Floating IPS), GUI, Win/Linux/macOS
1. Run Flips → **Apply Patch**.
2. Choose `patch/oppnav.ips`, then your clean ROM.
3. Save the output as `trm-yum6-oppnav.gba`.

### Option C — command line (this repo's own applier)
The test file ships a tiny, dependency-free IPS applier:
```bash
python3 - <<'PY'
import sys; sys.path.insert(0, 'tests')
from test_patch import apply_ips
clean = open('.workspace/trm-yum6.gba','rb').read()
patch = open('patch/oppnav.ips','rb').read()
open('trm-yum6-oppnav.gba','wb').write(apply_ips(clean, patch))
print('done')
PY
```

### Verify
```bash
python3 -c "import zlib;print(hex(zlib.crc32(open('trm-yum6-oppnav.gba','rb').read())))"
# expect 0xe0c3d7f0
```
If you don't want to patch at all, a pre-built ROM is written to
`.workspace/output/trm-yum6-oppnav.gba` when you run the builder (section 4).

---

## 3. Play

Load the patched ROM in any GBA emulator (tested on mGBA 0.10.5). During the
**opponent's turn**, press **Select**:

| Button | Effect while browsing the opponent's turn |
|---|---|
| **Select** | start browsing — the cursor appears, the CPU's turn pauses |
| **D-pad**  | move the cursor over any zone, both sides of the field |
| **Start**  | view the highlighted card's detail |
| **B**      | stop browsing — the CPU's turn resumes |
| **A**      | intentionally blocked (you cannot act out of turn) |

There is a ~0.5 s pause after Select before the cursor appears, while any
animation the CPU was mid-way through finishes. The turn is already frozen then;
only the cursor is waiting. This is expected.

---

## 4. Rebuild from source

```bash
pip install keystone-engine capstone      # assembler + disassembler
python3 tools/build_patch.py
# writes .workspace/output/trm-yum6-oppnav.gba and .workspace/output/oppnav.ips
```
On macOS, if `import keystone` fails with "fail to load the dynamic library",
install the native lib too: `brew install keystone`.

The builder reads the clean ROM from `.workspace/trm-yum6.gba`. All patch
parameters (hook address, stub address, the RAM addresses the stub reads) are
named constants at the top of `tools/build_patch.py`.

---

## 5. Test

```bash
python3 tests/test_patch.py        # plain runner, prints PASS/FAIL/SKIP
pytest tests/test_patch.py         # if you prefer pytest
```
Tests that need the base ROM skip cleanly when it is absent. See
`tests/README.md`.

---

## 6. How it works

The game never turns on the field-cursor screen during the CPU's turn: the
"field mode" value at `0x0201E22C` is 1 on your turn and 0 on the CPU's, and
while it is 0 the cursor code never runs. There is no "input locked" flag to
flip — the screen is simply off.

The fix uses the game's **own** field screen. The stub hooks the main loop's
per-frame input read, `ReadKeys` (`0x080F4764`, called once at `0x080F4B7A`),
because that runs every frame regardless of whose turn it is — unlike the duel
tick, whose cursor code is skipped for most of the CPU's turn. Each frame the
stub calls `ReadKeys` first, then:

- on the CPU's turn, if field mode is 0 and **Select** was just pressed, it sets
  field mode to 1 (the same `SetFieldMode(1)` writes your own turn uses). The
  field screen opens and, because it reports "busy", the duel logic pauses.
- while browsing, it clears **A** from the just-pressed keys, so the
  summon/activate menu can't open.
- **B** is the game's own exit: the field handler sets field mode back to 0, the
  stub stops interfering, and the CPU's turn resumes.

Full address map, the reverse-engineering path, and the live-capture evidence
are in `docs/OPPONENT_TURN_NAVIGATION.md`.

---

## 7. Troubleshooting

- **Patcher says CRC/size mismatch** — your base ROM isn't `0xF968A196`. This
  patch targets that exact ROM; a different dump or an already-patched ROM won't
  take.
- **Nothing happens on Select** — make sure it's actually the opponent's turn,
  and press Select (not Start). Remember the ~0.5 s delay while a CPU animation
  finishes.
- **Can't leave browsing** — press **B** (A is blocked by design).
- **`import keystone` fails when rebuilding** — see section 4 (install the native
  library).
