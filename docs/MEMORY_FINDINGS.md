# Memory & ROM findings

Concrete, verified facts about `trm-yum6.gba`. Separate from methodology
(see `LUA_AUTOMATION.md`, `GHIDRA_WORKFLOW.md`) — this file is just what we
know to be true, with the evidence for each claim.

## ROM identity

- File: `.workspace/trm-yum6.gba`, 32MB (`0x2000000`), CRC32 `0xf968a196`.
- Header title `YUGIOHWCT06`, game code `BY6E`, maker `A4` (Konami) →
  **Yu-Gi-Oh! World Championship Tournament 2006**. "Ultimate Masters" /
  `trm-yum6` is a translation/fix patch on top of this base, not a
  restructured hack — confirmed below, public WC06 documentation lines up
  byte-for-byte with this file.
- Same Konami duel-engine lineage as *Yu-Gi-Oh! The Eternal Duelist Soul*
  (GBA). A full matching decompilation of EDS exists
  (`CosmicScribe64/eds-decomp`, cloned into `.workspace/refs/eds-decomp`) and
  is a useful Rosetta stone for *struct layout and naming hypotheses*, but
  **addresses do not transfer** — it's a different build with a different
  card roster.

## Text / card-ID tables (confirmed against this exact ROM)

- `"Blue-Eyes White Dragon"` ASCII string found at file offset `0x015BB5AC`.
  This matches Data Crystal's documented WC06 card-name table base
  (`~0x015BB594`, plus a ~0x18-byte per-entry header) — i.e. **the public
  WC06 ROM map is valid for this file**, not just the base game.
- Card ID→number conversion table (per Data Crystal): file offset range
  `~0x015B7CCC`–`~0x015B917B` (~9500 x u16 entries, consistent with a large
  hacked roster — real WC06 2006 roster is much smaller).

## Card graphics — still NOT located in this ROM

No offset found yet. What we have is a *hypothesis*, not a confirmed fact,
imported from the EDS decomp's asset-extraction tool (`tools/assets.py`,
`x_card_art`): fixed-size image per card, 72×80 px, 6bpp indexed (64 colors),
followed by a contiguous palette block (BGR555, 64 colors × 2 bytes = 0x80
bytes per card) right after all image data for every card.

A naive scan for "runs of plausible 64-color-palette-shaped 0x80 byte blocks"
across the whole ROM produced hundreds of false-positive candidate regions —
the heuristic was too loose (anything non-empty and non-uniform matched) and
was abandoned. **This needs a real approach**: either search for a specific
known card's expected pixel pattern, or (more reliably) use Ghidra to trace
forward from the confirmed card-ID table to find what code indexes into a
graphics table using that same ID, and read the table base from there.

**Important correction, from a second project working with the same card
image source** (Project Kaiba, `data/base/pics/cards/<tier>/<passcode>.jpg`):
WC06's in-game card art is a crop of just the illustration, not the full
card (frame, name box, stat text). Our source JPGs (`sd` tier, 268×391) are
full-card scans. A naive downscale will not match what the ROM expects — the
illustration needs to be cropped out first, and the crop rectangle varies by
card-frame era (old frame vs. newer frames have different border geometry).

## Duel state: EWRAM after all (Session 3 conclusion retracted)

**Session 3 concluded "duel state lives in IWRAM, not EWRAM". That is
wrong.** Static disassembly (Session 4) shows game code reading *and
writing* EWRAM duel structures constantly — e.g. the struct at
`0x0201E2A0` has 442 literal-pool references in the first 3MB of ROM, with
stores into it (`0x0802940C`: `str r0, [r2, #4]`; `0x080937E8` zeroes its
first three words). A per-player block at `0x0201C4EC` with stride `0x868`
is indexed by player number in the same code. This matches the EDS decomp,
where every duel struct (`gDuel` `0x020192E0`, `gAiState` `0x02015EF0`,
`gDuelCtrl` `0x02015EE8`, ...) is in EWRAM.

Why the 240-frame EWRAM capture came out all-identical is **unknown**.
Candidates, unranked because nothing distinguishes them yet: the capture
script read a stale/cached buffer instead of fresh memory each frame;
`emu:readRange` silently truncated or failed on a 256KB read; or the
snapshots were written to the same file / compared wrongly. Anyone re-doing
EWRAM captures should first sanity-check that two snapshots taken across a
visible change (e.g. LP drop) actually differ.

IWRAM does change every frame — but much of what changes is `gMain`
(`0x03000040`, same address as EDS): key state, frame counters, OAM/BG
shadow buffers. That's system state, not duel state.

## `0x0300018F` is NOT a turn flag (retracted)

Session 3's "turn-owner / input-lock flag" candidate is **disproven by
disassembly**. `0x0300018F` is the high byte of a key-input bookkeeping
field inside `gMain`, written by the game's `ReadKeys` routine.

`ReadKeys` is at **`0x080F4764`** (found via the only literal-pool hit for
`KEYINPUT` `0x04000130` in code, at `0x080F47CC`). It reads `~KEYINPUT` and
writes, relative to `gMain` = `0x03000040`:

| Address | gMain+ | Type | Meaning (from the code) |
|---|---|---|---|
| `0x03000186` | `0x146` | u16 | held keys (`~KEYINPUT`) |
| `0x03000188` | `0x148` | u16 | newly pressed (+ auto-repeat) |
| `0x0300018A` | `0x14A` | u16 | newly released |
| `0x0300018C` | `0x14C` | u16 | previous key state (repeat tracking) |
| `0x0300018E` | `0x14E` | u16 | key state when auto-repeat last fired; set to `0` on any key change |
| `0x03000190` | `0x150` | u16 | mask of keys that auto-repeat |
| `0x03000192` | `0x152` | bitfield | bits 0-4 repeat counter, bits 5-9 repeat delay |
| `0x03000193` | `0x153` | u8 | key-history ring index (history buffer follows at `0x194`) |

(Same layout family as EDS `gMain.heldKeys/newKeys/prevKeys/keyRepeatTimer`,
just at a different offset inside `gMain`.)

Why the value is `0xFC` / `0`: `KEYINPUT` bits 10-15 are unused and read
`0`, so `~KEYINPUT` always has them set — the high byte of any "full key
state" u16 is `0xFC` when L/R aren't held. `0x0300018E` holds that full
state after an auto-repeat fires, and is reset to `0` whenever the key
state changes. So `0x18F` going `252 → 0 → 252` just means "key state
changed, then stayed unchanged long enough to repeat". The other one-frame
"pulses" at `0x186/0x188/0x18A/0x18C` were the A-press/release of the End
Phase confirm. Inference (not verified) on why it stayed `0` for 42
frames: either the harness changed key state again mid-window, or the game
changes the repeat config during the CPU turn. Either way it carries no
turn information, and the Session 3 live patch (force `0x18F = 252`) writes
a field nothing else reads — a no-op.

Static facts from the same function: `0x0300018E` is only *written* in
`ReadKeys`; field input handlers read `0x03000186` (e.g. `0x080C3C26`:
`ldrh` + `& 0x20` = Left, `& 0x10` = Right).

## Duel loop, turn player, field cursor

Mapped in Session 4. Full write-up and address table:
`OPPONENT_TURN_NAVIGATION.md`. Short version:

- Turn player: **`0x0201E1C8`** (`& 1`). Every phase handler uses it as
  the current player.
- `0x0201E2A4` is **not** the turn owner. An earlier draft of this file
  said it was. It is written once, at duel init, and holds this GBA's own
  player index. `0x0201E2A8[2]` = controller type per player (inferred:
  0 human, 1 CPU, 2 link).
- Field cursor: u16 at **`0x02023340`** (bit 7 player, bits 0-6 area,
  high byte index).
- Field mode: **`0x0201E22C`**. While it's non-zero the field screen
  runs and the duel logic pauses. Only the human path sets mode 1, so
  nothing turns it on during the CPU's turn. That is the actual "lock".

The EDS comparison was useful for structure, but WC06 doesn't have a
separate `AiRunTurn` path. The same phase handlers run for both players
and branch on controller type inside.

### Not yet found

- What the other subsystems in the duel tick chain do (`0x08093598`,
  `0x080A1658`, `0x080AB200`, `0x08095348`, `0x0804F2E0`).
- Confirmed DP/SP/M1/BP/M2/EP order of the phase table `0x09E5AAC0`.
