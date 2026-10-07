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
3. ✅ (static) Mapped the duel loop: turn player `0x0201E1C8`, field
   mode `0x0201E22C`, field cursor `0x02023340`, duel tick `0x08094CD4`.
   There is no input-lock flag. The field screen just never gets switched
   on during the CPU's turn. See `OPPONENT_TURN_NAVIGATION.md`.
4. Proposed fix: **pause-and-browse**. During the CPU's turn, Select turns
   on field mode 1. The game's own field screen runs and pauses the duel
   logic while it's open, B (the native exit) resumes, and A is blocked.
5. **Next actions**, in order:
   1. Live-test the prototype `tools/opp_turn_browse.lua` (checklist in
      `OPPONENT_TURN_NAVIGATION.md`).
   2. If it holds, write the ~80-byte Thumb stub that replaces
      `bl 0x080951CC` at `0x08094D26`, after verifying a free-space region.
   3. Package as BPS/IPS.

## Longer-term / not started

- Packaging the final patch (IPS/BPS) once both objectives are solved.
- Deciding whether the turn-navigation patch should still forbid *acting*
  out of turn (playing cards, ending phases) — right now the plan is only to
  unlock cursor movement/viewing, not actual input the AI doesn't expect.
