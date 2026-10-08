# Game navigation map (menus → duel)

How to reach every section of *Yu-Gi-Oh! World Championship Tournament 2006*
(`trm-yum6.gba`) from boot, as exact `press_key.sh` sequences. Written for
the live automation harness (`LUA_AUTOMATION.md`); the reusable driver that
encodes these flows is `tools/nav.py`.

**Fact-vs-inference convention of this doc:** each flow is tagged
**[VERIFIED]** (observed live by screenshot this session) or **[INFERRED]**
(deduced from menu layout / prior notes, not driven end-to-end yet). Do not
trust an [INFERRED] sequence blindly — screenshot after each step the first
time you run it.

## Button masks (from `press_key.sh` / `emu:setKeys`)

| Button | Mask | | Button | Mask |
|---|---|---|---|---|
| A | 1 | | Right | 16 |
| B | 2 | | Left | 32 |
| Select | 4 | | Up | 64 |
| Start | 8 | | Down | 128 |
| R | 256 | | L | 512 |

Invocation: `press_key.sh <mask> [times] [hold_s] [gap_s]`.

## CRITICAL gotcha: d-pad auto-repeat double-moves the cursor

A single d-pad press held for the `press_key.sh` **default hold (0.12s)**
is long enough to trigger the game's key auto-repeat, so the cursor moves
**two slots, not one**. This is the same auto-repeat bookkeeping documented
in `MEMORY_FINDINGS.md` (`gMain` key-repeat fields at `0x03000190`–`0x0300018E`).

**Fix:** use a short hold of **~0.08s** for every d-pad move. At 0.08s each
press advances exactly one slot. Example (one slot down):
`press_key.sh 128 1 0.08`. A/B/Start confirms are not direction-repeated, so
their hold time does not matter for cursor position.

`tools/nav.py` bakes `hold=0.08` into its `press()` default so every helper
moves one slot per press. If you call `press_key.sh` by hand for d-pad
movement, pass the hold explicitly.

## Boot → Title screen  [VERIFIED]

Boot with an SRAM save present lands on the **Title screen** with two
options: **Continue** / **New Game**, cursor defaulting on **Continue**.

- **Continue** (default): `press_key.sh 1` (A). → Main menu.
- **New Game**: move cursor to New Game, then A. One slot down at short hold:
  `press_key.sh 128 1 0.08` then `press_key.sh 1`.
  New Game leads into profile creation — on-screen name-entry keyboard
  (arrows move highlight, A picks a letter, select "OK" + A) → "Ok?" Yes/No
  → icon select (A on default) → first-deck select (A on default) → Main
  menu. This New-Game sequence is **[INFERRED]** here from a prior session's
  notes (`LUA_AUTOMATION.md` in-game map); it was not re-driven this session.
  Continue is the path the automation uses.

## Main menu  [layout VERIFIED, non-FreeDuel destinations INFERRED]

6 rows, cursor starts on **row 0 (Deck Edit)**:

| Row | Entry | Reach from top of menu |
|---|---|---|
| 0 | Deck Edit | `A` |
| 1 | Free Duel | `Down ×1`, `A` |
| 2 | Challenge! | `Down ×2`, `A` |
| 3 | Get Cards | `Down ×3`, `A` |
| 4 | Forb/Ltd Card Lists | `Down ×4`, `A` |
| 5 | Options | `Down ×5`, `A` |

Each `Down` is `press_key.sh 128 1 0.08` (one slot). The row order and the
row-0 start are **[VERIFIED]** by screenshot. Only **Free Duel** has been
followed past the menu this session; what the other four entries open is
**[INFERRED]** (named screens below are expectations, not confirmations):

- **Deck Edit** [INFERRED]: deck-list / card-pool editor.
- **Challenge!** [INFERRED]: submenu, see below.
- **Get Cards** [INFERRED]: card shop / pack opening.
- **Forb/Ltd Card Lists** [INFERRED]: read-only banlist viewer.
- **Options** [INFERRED]: settings.

### Challenge! submenu  [INFERRED]

Reported entries, order assumed as listed (not screenshot-confirmed this
session; cursor start position unknown — verify before relying on counts):

0. Duel Puzzle
1. Limited Duel
2. Theme Duel
3. Survival Duel

Assuming cursor starts on row 0, reach row N with `Down ×N` (short hold)
then `A`.

## Free Duel → Main Phase 1  [VERIFIED]

Free Duel reuses the current/last profile, deck and opponent — so it jumps
**straight to the Coin Toss**, skipping opponent/deck pickers. In the live
run the opponent was **"Kuriboh & Friends"** and the deck **"DRAGON'S ROAR"**;
a different last-used selection would duel a different opponent, but the
button sequence is identical.

From the Main menu (cursor on row 0):

1. Select Free Duel: `press_key.sh 128 1 0.08` (Down ×1), `press_key.sh 1` (A).
2. **Coin Toss Selection:** appears — "Heads" / "Tails", cursor on **Heads**.
   Accept Heads: `press_key.sh 1` (A).
3. Coin animation plays (~2–3s). **Wait** before the next input.
4. **"START DUEL"** banner appears: `press_key.sh 1` (A).
5. Duel field loads on **your Main Phase 1**.

To pick Tails instead: before step 2's A, `press_key.sh 16 1 0.08` (Right
one slot) — **[INFERRED]** direction; Heads is the verified default.

## Phase control inside a duel (ending your turn)  [partly VERIFIED]

**[VERIFIED]:** pressing **B** while a **field zone** (an empty/selected
zone, not a card) is highlighted opens a **"Select phase to enter."** menu.
Options depend on the current phase (e.g. **M1 / EP** in Main Phase 1, or
**BP / M2 / EP** later). Navigate the options with **Left/Right** and
confirm with **A**. This is the fast way to end your turn: open the menu,
land on **EP** (End Phase), press A.

**[INFERRED]** detail: the exact number of Left/Right presses to land on EP
varies with the phase (EP is the rightmost option in the observed menus, so
pressing Right until it stops, then A, is the robust move). `end_turn()` in
`tools/nav.py` presses Right a couple of times (short hold) to reach the
rightmost option, then A — screenshot to confirm EP is highlighted the first
time, since option sets differ by phase.

**Known non-controls** (from `LUA_AUTOMATION.md`, confirmed there): **Start**
does *not* open the phase menu (it opens card detail if a card is selected,
else nothing). **L/R shoulders** do nothing for phase control.

### Discard-prompt caveat  [VERIFIED elsewhere]

At 7+ cards in hand, ending a turn triggers a mandatory "Discard from your
hand" prompt whose cursor roams the *whole board grid*, not just your hand
row, and does not reliably start on a hand card. Pressing A off a valid
discard target is silently ignored. Any automated end-turn that can hit this
must screenshot and confirm the cursor is on one of your own hand cards
before pressing A (see `LUA_AUTOMATION.md` gotcha #7).

## Full boot → duel sequence (what `tools/nav.py full-duel` runs)

```
# Title: Continue
press_key.sh 1                 # A
# Main menu: down to Free Duel, enter
press_key.sh 128 1 0.08        # Down one slot
press_key.sh 1                 # A
# Coin Toss: accept Heads
press_key.sh 1                 # A
# (wait ~3s for coin animation)
# START DUEL banner
press_key.sh 1                 # A
# -> your Main Phase 1
```

Everything above the phase-control section is [VERIFIED] as a single live
run; re-verify after any ROM change, save-state change, or if the last-used
Free Duel selection differs.
