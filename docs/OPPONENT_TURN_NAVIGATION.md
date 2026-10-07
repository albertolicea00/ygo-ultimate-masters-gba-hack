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

### Step 2 — ROM patch

Redirect the `bl 0x080951CC` at **`0x08094D26`** to a small Thumb stub:

```
stub:                                   ; replaces bl 0x080951CC
    push {r4, lr}
    ldr  r0, =0x0201E1C8 ; ldr r0,[r0] ; movs r1,#1 ; ands r0,r1 ; lsls r0,#2
    ldr  r1, =0x0201E2A8 ; ldr r0,[r1,r0]
    cmp  r0, #1          ; CPU's turn?
    bne  call
    ldr  r1, =0x0201E22C ; ldr r2,[r1]
    cmp  r2, #0
    bne  browsing
    ldr  r3, =0x03000188 ; ldrh r3,[r3] ; movs r4,#4 ; tst r3,r4   ; Select?
    beq  call
    movs r0, #1 ; bl SetFieldMode(0x08096988)
    b    call
browsing:                               ; only when we set mode 1 ourselves
    cmp  r2, #1 ; bne call              ; (track with a spare RAM byte to be exact)
    ldr  r3, =0x03000188 ; ldrh r4,[r3] ; movs r2,#1 ; bics r4,r2 ; strh r4,[r3] ; drop A
call:
    bl   0x080951CC
    pop  {r4} ; pop {r1} ; bx r1
```

About 80 bytes. The ROM is the full 32MB and has no `0xFF` padding. There
are zero-filled runs of up to ~16KB above `0x09800000` (e.g. `0x0994F8FC`,
`0x09E052D0`). Before using one, check that nothing references it; zeros
inside data aren't automatically free. Package the result as a BPS/IPS patch.

### Open questions / risks

- **[inferred]** CPU = controller 1. Prototype check 1 settles it.
- Does starting field mode mid-CPU-turn leave stale state? The setter zeroes
  `+0x1D54` ("finished"). If a CPU phase handler is waiting on that field
  for its own reasons, entering browse could confuse it. The prototype logs
  the old values.
- The B exit zeroes `+0x1D5C` (result code). This needs the same check.
- If the CPU never gives the duel tick an idle frame (the chain always busy
  during its actions), Select only takes effect between actions. That's
  acceptable and arguably desirable.
- The alternative, browsing while the CPU keeps playing, isn't proposed. It
  would need the cursor separated from the CPU's own selection display.
