# Opponent-turn navigation patch

`oppnav.ips` lets you move the field cursor and view cards **during the CPU's
turn** in Yu-Gi-Oh! Ultimate Masters (WC06, `trm-yum6.gba`).

## Apply

Apply `oppnav.ips` to a clean `trm-yum6.gba` with any IPS patcher
(Lunar IPS, Flips, `ips.py`, rom-patcher-js, …).

- Clean ROM CRC32: `0xF968A196`
- Patched ROM CRC32: `0xE0C3D7F0`

The patch changes 124 bytes total: a 120-byte code stub in unused space at
`0x0800F700`, and one redirected call at `0x080F4B7A`.

## Use

During the opponent's turn, press **Select**. The field cursor appears and the
opponent's turn pauses while you browse:

- **D-pad** — move the cursor over any zone, both sides of the field.
- **Start** — view the selected card's detail.
- **B** — stop browsing; the opponent's turn resumes.
- **A is intentionally blocked** while browsing, so you can't act out of turn.

There is a ~0.5 s delay after pressing Select before the cursor appears, while
any animation the CPU was mid-way through finishes. This is expected.

## How it works

See `../docs/OPPONENT_TURN_NAVIGATION.md`. In short: the game never turns on the
field-cursor screen during the CPU's turn (field-mode value stays 0). The stub
hooks the per-frame input read (`ReadKeys`), and on the CPU's turn, when you
press Select, it sets field mode to 1 — exactly what your own turn uses. The
field screen then opens and, because it reports "busy", the duel logic pauses
until you leave with B.

Rebuild from source: `python3 ../tools/build_patch.py` (needs keystone-engine).
Tests: `python3 ../tests/test_patch.py`.

**Full guide** (patchers step-by-step, controls, rebuild, tests, internals,
troubleshooting): `../docs/PATCH_GUIDE.md`.
