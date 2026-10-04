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

## Duel state lives in IWRAM, not EWRAM

**Verified empirically.** Captured 240 consecutive emulator frames of full
EWRAM (`0x02000000`–`0x02040000`, every byte) spanning an entire opponent
turn, including the duel actually ending (win/loss results screen appeared
within the capture window). Every one of the 240 EWRAM snapshots was
byte-for-byte identical, despite the visible game state changing completely.
Conclusion: EWRAM in this build holds static data (card tables, text, menu
assets); the *mutable* per-duel state (phase, turn owner, LP, hand/field
contents, cursor position) lives in **IWRAM** (`0x03000000`–`0x03007FFF`,
32KB) instead. Confirmed the opposite is true there: sampling IWRAM every
frame shows real, frequent byte-level changes.

This matters a lot practically: IWRAM is 32KB vs. EWRAM's 256KB, i.e. an 8x
smaller haystack, which is why the turn-flag search below was tractable.

## Turn-owner / input-lock flag: strong candidate found

**IWRAM offset `0x18F` (absolute address `0x0300018F`).**

Method: armed a Lua `callbacks:add('frame', ...)` hook that dumps all 32KB of
IWRAM to a numbered file every single emulator frame (no stride — earlier
attempts at 1-sample-per-2-or-3-frames missed the entire transition because
the CPU opponent's whole turn resolves in under ~45 frames, well under a
second). Captured 300 consecutive frames spanning: confirming my own End
Phase → the opponent's entire turn → back to my own Draw Phase.

Per-offset transition analysis across those 300 frames found `0x18F` is the
*only* byte in all of IWRAM with this exact clean pattern:

| Frames | Value | Game state |
|---|---|---|
| 1–32 | `252` (`0xFC`) | still resolving my End Phase |
| 33–74 | `0` | opponent's entire turn (draw, main phase, attack) |
| 75–300 | `252` | back to my turn (Draw Phase onward) |

A handful of other offsets (`0x186`, `0x188`, `0x18a`, `0x18c` — all nearby,
suggestively part of the same struct) also flip near frame 32, but only for
a single frame each (0→1→0 immediately) — those look like one-shot
transition-event pulses (e.g. "a turn-change animation just started"), not
the persistent state flag. `0x18F` is the one that stays at its new value for
the entire duration of the side it represents.

Likely semantics: `0xFC` = "it's your (the human player's) turn",
`0x00` = "it's not" — a sentinel-style boolean rather than a literal 0/1,
which is a common pattern in GBA-era C code (`if (turnFlag)` where the
compiler was given a non-1 truthy constant by the original source, or the
byte is reused for multiple purposes with 0xFC specifically meaning "player
side active").

**Live patch installed (not yet proven causal — see below)**:
```lua
callbacks:add('frame', function()
  if emu:read8(0x0300018F) == 0 then emu:write8(0x0300018F, 252) end
end)
```
This fires correctly every time the flag would have dropped to 0 (confirmed
via an incrementing counter in the same callback). **What's NOT yet
confirmed**: whether forcing this byte actually re-enables field cursor
navigation during the opponent's turn. Every attempt to test this by hand
(press a direction key via the external automation harness, then screenshot)
landed after the opponent's turn had already finished naturally — the AI
turn is faster than a human-speed external test loop. The next step is to
run the whole test (force + inject input + read back cursor position) inside
a single Lua frame callback with no round-trip to the outside world, so it's
frame-exact instead of reaction-time-exact. See `LUA_AUTOMATION.md` for the
in-progress script for this.

### Not yet found

- The cursor-position byte in IWRAM (needed to verify the patch, see above).
- The actual ARM/Thumb instruction(s) in ROM that read `0x0300018F` — a raw
  byte search for the address as a little-endian literal-pool constant
  (`0xb2 0x01 0x00 0x03`) found 2 hits, but both are **not 4-byte-aligned**
  (file offsets `0x1fd21` and `0x20179`, both `≡ 1 mod 4`), which a real
  Thumb/ARM literal pool word can never be — both are almost certainly
  coincidental byte patterns inside unrelated code or data, not real
  references. The address is probably constructed arithmetically
  (base-register + offset) rather than loaded as a raw literal, which means
  finding the real reference needs proper disassembly from Ghidra (with
  correct code/data separation), not a raw byte grep. See
  `GHIDRA_WORKFLOW.md`.
