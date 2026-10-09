# Opponent-turn field navigation: how the duel loop works, and the fix

Static analysis only (Session 4, capstone). Nothing here has been run yet.
Each claim is tagged **[code]** (read directly from the disassembly) or
**[inferred]** (a reading of the code that a live test still needs to
confirm).

## How a duel frame runs

`0x08094CD4`, the duel tick (entry 1 of the 3-entry table at `0x09E5AADC`),
runs once per frame. It calls a chain of subsystems in a fixed order and
stops at the first one that returns non-zero ("busy") **[code]**:

```
0x08093598   ?                (first; probably animations/messages)
0x080951CC   field screen     <- the human's cursor lives here
0x080A1658   ?
0x080AB200   ?
0x08095348   ?
0x0804F2E0   ?
then, if all returned 0:   0x0809495C (win/LP check) and the duel logic
```

The duel logic includes the phase dispatcher `0x08094C60`: phase index
`0x0201E1F8` indexes the 6-entry table `0x09E5AAC0`. The step inside the
phase is `0x0201E1FC`, reset to 0 on each phase change **[code]**.
**[inferred]** The six entries are DP/SP/M1/BP/M2/EP; the order isn't
confirmed. Both players use the same phase handlers. Inside a handler the
code branches on the controller type of the turn player (below), so the
CPU isn't on a separate path.

## The field screen and why it's dead on the CPU's turn

`0x080951CC` **[code]** (cross-checked against the Ghidra decompiler,
which produced the same control flow):
- calls task dispatcher `0x0801EF94(3)`; task 3 is the field input handler
  `0x080CCA80`. If that's busy, it returns 1.
- otherwise, if **field mode** `0x0201E22C` ≠ 0 and the task isn't
  running yet (`0x0201E230` = 0), it starts task 3 (`0x0801EC9C(3,0,0,0)`)
  and returns 1.
- if field mode is 0, it clears `0x0201E230` and returns 0.

Field mode is set only through `SetFieldMode` `0x08096988`. That setter
also zeroes `+0x1D7C/+0x1D58/+0x1D54` and copies the local side into
`+0x1D64` **[code]**. Callers and values: 1 at `0x0809C322`, 2 at
`0x0809E2EE`, 3 at `0x080979EA`, 4/5 in `0x08085D4C`/`0x0808611C`, 5 in
`0x0804CE78`, 6 in `0x08069E40` **[code]**. The mode-1 call is reached only
when the turn player's controller isn't type 1 (`0x0809C2F8`), so it never
happens on the CPU's turn **[code]**. That's the whole "lock": nobody turns
the field screen on for the CPU's turn, so there's no flag to flip.

While field mode is on, `0x080CCA80` always returns 1 (`0x080CCDEC`) **[code]**.
So **the duel logic doesn't advance while the player is browsing**.
Field handler state 0 (`0x02023130` byte = 0) does this each frame **[code]**:
- A → open the command menu (`0x080C55DC`, state 1). Out of turn this would
  be dangerous.
- B → `0x08096ECC`: field mode = 0, `+0x1D5C` = 0. This is the game's own
  exit.
- otherwise move the cursor (`0x080C716C`: Up/Down `0x080C6B04`,
  Left/Right `0x080C6E9C`), then `0x080C5444` and `0x080C8AA8` (redraw /
  info panel **[inferred]**).
- Start → `0x080C707C(cursor)`, then state 3 (card detail **[inferred]**).
- Select (with a sub-condition) → state 4.

## Addresses

| Address | Meaning | Basis |
|---|---|---|
| `0x0201C4E0` | duel struct base; per-player blocks at `+0xC`, stride `0x868` | code |
| `0x0201E1C8` (`+0x1CE8`) | turn player (`& 1`) | code (every phase handler reads it as "current player") |
| `0x0201E1F8` (`+0x1D18`) | phase index | code |
| `0x0201E1FC` (`+0x1D1C`) | step within phase | code |
| `0x0201E22C` (`+0x1D4C`) | field mode (0 off, 1 free browse, 2–10 other) | code |
| `0x0201E230` (`+0x1D50`) | field task running | code |
| `0x0201E234` (`+0x1D54`) | field interaction finished | inferred |
| `0x0201E2A4` | this GBA's player index (set once at duel init) | code |
| `0x0201E2A8` | controller type per player, u32[2] | code |
| `0x02023130` | field-screen state struct; byte +0 = handler state | code |
| `0x02023340` | cursor, u16: bit 7 player, bits 0–6 area, high byte index | code |

Controller types: generic duel init `0x080937D4` writes `[0]=0, [1]=1`.
The init at `0x0802940C`, which looks like link setup, writes 0 for the
local side and 2 for the other. **[inferred]** 0 = local human, 1 = CPU,
2 = link partner. Area `0xB` = hand, the same as EDS.

## Proposed fix: pause-and-browse

During the CPU's turn the player presses a button (prototype: Select). We
set field mode 1, the same mode the human gets in their own turn. The
game's own field screen then runs, and because it returns "busy" the CPU's
turn freezes until the player presses B, which is the game's own exit.
This is the same model as EDS's link-duel "interrupt" (`DuelPhase_OpponentTurn`
runs `DuelScreen_HandleInput` for the non-turn player).

Why pause rather than browse while the CPU keeps playing:
- No concurrency. The CPU's own selections move the same cursor
  (`0x02023340`). Browsing while it plays would fight over it.
- Safe entry points for free. The chain only reaches the field screen when
  `0x08093598` isn't busy, so field mode can't start in the middle of an
  animation.
- The game already has the code for all of it: cursor, card detail, exit.
  The patch only adds an entry condition and blocks A.

Out-of-turn actions must stay blocked. A opens the command menu and must be
filtered while browsing on the CPU's turn.

**Card inspection is on Start, A stays fully blocked (by choice).** The field
handler already gives card inspection two ways: Start (state 3, card detail) and
the magnifying-glass "inspect" item inside the A command menu. Since Start
already shows the full card, the patch blocks A wholesale rather than allowing
only the inspect item — allowing one menu item while filtering summon/set/
activate would be extra logic for no user-visible gain. So inspection works
during the CPU's turn; it is just mapped to Start.

## Live validation (2026-10-08)

Run against a live Free Duel (vs Kuriboh & Friends) with an in-Lua
frame-exact harness (`tools/browse_diag.lua`; raw log
`docs/browse_diag_run.log`). No screenshot timing was involved — all reads,
the mode write and the input injection happen inside frame callbacks, so the
CPU's sub-second turn is fully observable.

First, the address map was confirmed on the player's own turn:
`turn=0, ctl0=0, ctl1=1, mode=1, localside=0` — i.e. controller 0 = human,
**controller 1 = CPU (the inference was right)**, and field mode is 1 during
your own turn. On ending the turn: `turn=1, mode=0` — field mode is 0 for the
whole CPU turn, which is exactly why the cursor is dead.

Then, forcing field mode 1 on the CPU's turn (the `SetFieldMode`-equivalent
writes) and injecting Right edges, logged per frame:

- **Pause works.** `phase` stayed frozen for the entire forced-browse window;
  it only advanced (to the next phase) after mode was set back to 0.
- **Resume works.** Setting mode 0 handed the turn back; the CPU finished and
  play continued normally.
- **Cursor moves.** Once the field task was running (`task=1`), each injected
  Right moved the cursor: `000e → 000d → 000c → 0005`. The injected keys showed
  up in `newKeys` (`0x0010`) as expected, so the normal input path is used.
- **Startup delay.** For the first ~32 frames the field task had not started
  yet (`task=0`) because a CPU animation was still in flight; the cursor held
  still but the screen was already paused. The task started on its own and the
  cursor became live. An earlier, cruder test checked too early (inside that
  window) and wrongly concluded the cursor didn't move.
- **No desync.** The duel ran coherently across ~4 turns of repeated
  mode-forcing (LP, phases and prompts all normal, no softlock). The two side
  fields `SetFieldMode` zeroes (`+0x1D54`, and the B-exit's `+0x1D5C`) caused no
  observable trouble.

So the pause-and-browse mechanism is proven on real hardware-accurate
emulation. What remains for the prototype is only the trigger wiring (Select to
engage, B the native exit, A blocked) — the same writes and input path already
validated above.

### Step 1 — live prototype (no ROM change)

`tools/opp_turn_browse.lua` does the above from Lua. It uses a `frame`
callback for entry and a `keysRead` callback with `emu:clearKey` to
strip A (mGBA 0.10.5 has both). It logs to `/tmp/opp_turn_browse.log`.
What to check:
1. The log's `ctl0/ctl1` show `0` and `1` in a Free Duel. If not, the
   controller-type reading is wrong.
2. Select on the CPU's turn brings up the cursor and the CPU stops.
3. The D-pad moves over both sides, and Start shows detail for
   face-up/opponent cards. Face-down opponent cards should stay hidden;
   the native handler should already refuse them.
4. B resumes the CPU's turn and the duel finishes normally (no softlock,
   no desync of phase or LP).
5. Edge cases: Select during battle damage, during a chain, and when the
   CPU's turn is about to end.

### Step 2 — ROM patch (DONE, validated)

Shipped: `patch/oppnav.ips` (124 bytes changed). Built by `tools/build_patch.py`
(keystone assembler + capstone verification).

**Hook point — not the field-step.** The obvious hook, the duel tick's
`bl 0x080951CC`, does *not* work: the tick skips that call for most of the CPU's
turn (an internal busy-check early-returns), and the duel tick itself
(`table[1]` at `0x09E5AADC`) is only dispatched intermittently during the CPU's
turn. Both were tried and confirmed dead by live logging (the stub ran ~2x in
50 frames). What runs **every** frame regardless of turn is the input poll
`ReadKeys` (`0x080F4764`), called once from the main loop at `0x080F4B7A`. The
patch redirects that one call through the stub.

**The stub** (120 bytes at `0x0800F700`, an unreferenced zero-padding run;
caused no graphics glitch anywhere across a full play-test):
```
push {lr}
bl   0x080F4764          ; ReadKeys — refresh newKeys first
if controller[turnPlayer] != 1: goto done      ; only the CPU's turn
if fieldMode != 0:                              ; already browsing
    newKeys &= ~A                               ; block A, then done
if (newKeys & Select):                          ; engage
    fieldMode = 1
    gDuel.+1D54 = +1D58 = +1D7C = 0
    gDuel.+1D64 = localSide                     ; = SetFieldMode(1)
done:
pop {pc}
```

**Live result (pure ROM, no Lua logic — Lua only pressed the buttons):** on the
CPU's turn, Select set field mode 0→1 on the next frame; the injected D-pad then
walked the cursor across the whole field
(`050b→000d→000c→0005→0105→0205→0305→0405`, crossing to the opponent's side); B
set mode back to 0 and the CPU resumed and finished its turn; A stayed blocked;
the duel continued to the next turn with no desync. Field mode held 1 for the
whole browse (92 of ~110 logged frames).

### Apply / use

See `patch/README.md`. Clean CRC32 `0xF968A196`, patched `0xE0C3D7F0`.

### Resolved by validation / remaining notes

- CPU = controller 1: **confirmed** live (`ctl0=0, ctl1=1`).
- Entering field mode mid-CPU-turn left no stale-state problem: the duel ran
  coherently across many turns of engaging/exiting, no desync or softlock.
- Startup delay (~0.5 s) before the cursor is live, while an in-flight CPU
  animation finishes. Pausing is immediate; only the cursor waits. Expected.
- Not done (possible future work): let the player *act* in a limited way out
  of turn, or browse without pausing the CPU (would need the cursor separated
  from the CPU's own selection display). Current design is view-only + pause,
  which is what was asked for.
