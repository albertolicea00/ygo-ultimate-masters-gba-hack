# Roadmap

Two independent objectives. Status as of this writing.

## 1. Card graphics (SD/HD replacement)

**Status: not started on the real ROM.** We have a hypothesis for the format
(from a sibling engine, not confirmed against this ROM's actual bytes) and a
source image set, but have not located the real offset or verified the format
against actual extracted tile data.

Remaining work, in order:
1. Locate the card-art block's real file offset in `trm-yum6.gba` (see
   `MEMORY_FINDINGS.md` — nothing found yet; naive entropy/palette-signature
   scanning didn't work, needs either a known card's expected pixel pattern to
   search for, or Ghidra xref-tracing from the card-ID table).
2. Confirm resolution/bpp/palette-count against that real data (the 72x80
   6bpp/64-color hypothesis is from EDS, a different build).
3. Figure out the illustration-crop rectangle per card-frame era (our source
   JPGs are full-card scans; WC06 art is illustration-only — see
   `MEMORY_FINDINGS.md`).
4. Write the extraction + re-encode + injection pipeline once the above are
   known.

## 2. Opponent-turn field navigation

**Status: back to locating the turn state. Session 3's flag was wrong.**

1. ❌ Retracted: "duel state lives in IWRAM". Code reads/writes EWRAM duel
   structs (`0x0201E2A0`, `0x0201C4EC`) constantly, same as EDS.
2. ❌ Retracted: `0x0300018F` as turn/input-lock flag. Disassembly of
   `ReadKeys` (`0x080F4764`) shows it is the high byte of a key-repeat
   field in `gMain`; `0xFC` is just the always-set unused `KEYINPUT` bits.
   The live patch forcing it to `252` is a no-op. See `MEMORY_FINDINGS.md`.
3. New turn-owner candidate (static only): `0x0201E2A4`.
4. Working hypothesis (from EDS): the CPU turn runs its own per-frame state
   machine instead of the human cursor handler, so there's probably no
   single "lock" branch — the fix is likely a hook that also runs the
   cursor/view handler during the CPU turn.
5. **Next actions**, in order:
   1. Live: log `0x0201E2A4` every frame across a turn change (one Lua
      frame callback writing to a file — no human-speed loop needed, since
      it's passive logging). Also sanity-check that EWRAM snapshots differ
      across a visible change, to find out why Session 3's capture didn't.
   2. Static: find WC06's CPU-turn dispatcher (`AiRunTurn` equivalent) and
      the human field-cursor handler — readers of `0x03000188` (newKeys)
      near readers of the turn-owner field are the place to start.
   3. Decide the patch shape once both are known (hook vs. branch).
6. Ghidra is still useful for xrefs, but `tools/disasm_thumb.py` (capstone)
   was enough for everything in Session 4 — try it first, it's instant.

## Longer-term / not started

- Packaging the final patch (IPS/BPS) once both objectives are solved.
- Deciding whether the turn-navigation patch should still forbid *acting*
  out of turn (playing cards, ending phases) — right now the plan is only to
  unlock cursor movement/viewing, not actual input the AI doesn't expect.
