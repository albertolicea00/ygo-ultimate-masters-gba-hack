# Journey

Append-only, chronological, one section per session: what day, what was
found. Durable reference material lives elsewhere — this file is "what
happened when", not "what's true".

Don't write new findings here — put them in the relevant technical doc, then
add a dated entry below.

---

## 2026-10-03 — Session 1

ROM identified (WC06/Ultimate Masters, `BY6E`). Confirmed public WC06 text-
table documentation applies to this exact file. Cloned `eds-decomp` as a
structural reference (not address-compatible). Installed Ghidra + mGBA.
Built the first version of the live mGBA+Lua+Accessibility automation
harness and proved it end to end (Start button advances the title screen).

## 2026-10-03/04 — Session 2

Reached a real duel in-game via the automation harness. Attempted to find
the turn-flag by burst-sampling EWRAM around the end-of-turn transition —
didn't work (too coarse a sampling stride relative to how fast the CPU
opponent plays; see `MEMORY_FINDINGS.md`). Lost significant time to a
discard-prompt cursor misunderstanding and an intermittent window-focus
issue, both now documented in `LUA_AUTOMATION.md` gotchas.

## 2026-10-04 — Session 3

**Found that the live duel state lives in IWRAM, not EWRAM** (proven via a
240-frame all-identical EWRAM capture spanning a full duel ending). Re-ran
the capture against IWRAM instead and found a very clean candidate for the
turn/input-lock flag at `0x0300018F` (`252` during the player's turn, `0`
during the opponent's). Installed a live Lua patch forcing it back to `252`.
**Not yet proven** that the patch actually restores navigation — the CPU
opponent's turn is faster than any human-speed test loop can verify by hand.
Also found and fixed a real blocker: macOS was denying the Accessibility
permission to the terminal running the automation scripts the whole time,
which explained most of Session 2's flakiness. Split the single findings log
into topic docs per the user's request, instead of one growing file.

## 2026-10-06 — Session 4

Static pass with capstone instead of more live testing. **Disproved
Session 3's turn flag**: found the game's `ReadKeys` (`0x080F4764`) and
`0x0300018F` is the high byte of a key-repeat field in `gMain`; its `0xFC`
is the always-set unused `KEYINPUT` bits. The live patch was a no-op.
**Also retracted "duel state is in IWRAM"**: code reads/writes EWRAM duel
structs constantly (as in EDS); why Session 3's EWRAM capture looked
static is still unexplained. New, unverified turn-owner candidate
`0x0201E2A4`. EDS suggests the CPU turn swaps out the human cursor handler
entirely, so the eventual patch is probably a hook, not a branch flip.
Added `tools/disasm_thumb.py`.

## 2026-10-07 — Session 5

Static pass with capstone (plus Ghidra re-imported with proper base/RAM
blocks and Thumb seeding). **Disproved Session 3's turn flag**: found the
game's `ReadKeys` (`0x080F4764`), and `0x0300018F` is the high byte of a
key-repeat field in `gMain`. The live patch was a no-op. **Also retracted
"duel state is in IWRAM"**: the duel structs are in EWRAM, as in EDS. Then
mapped the duel loop: per-frame tick `0x08094CD4`, phase table
`0x09E5AAC0`, turn player `0x0201E1C8`, field mode `0x0201E22C`, field
cursor `0x02023340`. There is no lock flag. The field screen just never
gets switched on during the CPU's turn, and while it's on the duel logic
pauses. Proposed fix: pause-and-browse (Select on the CPU's turn turns on
field mode 1, B resumes, A blocked). Wrote a Lua prototype for it; it
hasn't been run yet. Added `tools/disasm_thumb.py`, `tools/ghidra/`,
`tools/opp_turn_browse.lua`, `docs/OPPONENT_TURN_NAVIGATION.md`.

## 2026-10-08 — Session 6

**Live-validated the pause-and-browse mechanism** in a real Free Duel, using
an in-Lua frame-exact harness (no screenshot timing). Confirmed the address
map on the player's turn (controller 0 = human, 1 = CPU; field mode 1 during
your turn, 0 during the CPU's). Then on the CPU's turn: forcing field mode 1
froze the phase (pause works), injected Right moved the cursor once the field
task started (`000e→000d→000c→0005`), and clearing mode handed the turn back
(resume works). ~4 turns of repeated mode-forcing caused no desync. The only
nuance is a ~0.5s startup delay before the cursor becomes live, while an
in-progress CPU animation finishes. Evidence: `docs/browse_diag_run.log`,
harness `tools/browse_diag.lua`. Also spawned a subagent that wrote
`docs/GAME_NAVIGATION.md` and `tools/nav.py` (menu-flow automation). 
Then built and shipped the **permanent ROM patch**: after finding that
hooking the duel tick fails (its field-cursor chain is skipped for most of the
CPU's turn), hooked the per-frame `ReadKeys` call (`0x080F4B7A`) instead. The
120-byte Thumb stub (at `0x0800F700`, assembled with keystone, verified with
capstone) sets field mode 1 on Select during the CPU's turn, blocks A, and lets
B exit. **Validated on the patched ROM with real input**: cursor moved across
the field during the CPU's turn, CPU paused and resumed, no desync, no graphics
glitch. Shipped `patch/oppnav.ips` (clean CRC32 `0xF968A196` → `0xE0C3D7F0`),
`tools/build_patch.py`, `patch/README.md`.