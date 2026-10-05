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

**Status: flag candidate found, causal proof pending.**

1. ✅ Confirmed live duel state lives in IWRAM (`0x03000000`, 32KB), not EWRAM.
2. ✅ Found a strong candidate for the turn/input-lock flag: IWRAM `0x18F`
   (absolute `0x0300018F`). Clean `252 → 0 → 252` transition exactly on the
   turn boundaries across a 300-frame, every-frame capture. See
   `MEMORY_FINDINGS.md` for the full evidence.
3. ✅ Installed a live Lua frame-callback that forces this byte to `252`
   whenever it reads `0`.
4. ❌ **Not yet verified** that forcing the flag actually restores cursor
   navigation during the opponent's turn. The CPU opponent's entire turn
   resolves in well under a second, too fast for any human-speed
   screenshot-then-keypress test loop to land inside the window and observe
   anything meaningful.
5. **Next action**: run the whole test inside one Lua frame-callback (force
   the flag + inject a direction key + read back a cursor-position byte), no
   round-trip to the outside world at all, so timing is frame-exact instead
   of human-reaction-exact. See `LUA_AUTOMATION.md` for the harness and the
   in-progress script (`cursor_diff_result.txt` test — first attempt didn't
   produce output, needs debugging).
6. Once confirmed: find the actual ARM/Thumb instruction in ROM that reads
   `0x0300018F` and gates the d-pad handler on it (via Ghidra — see
   `GHIDRA_WORKFLOW.md`), and turn the live memory-patch into a real
   IPS/BPS ROM patch (likely just NOP-ing or inverting one conditional
   branch).

## Longer-term / not started

- Packaging the final patch (IPS/BPS) once both objectives are solved.
- Deciding whether the turn-navigation patch should still forbid *acting*
  out of turn (playing cards, ending phases) — right now the plan is only to
  unlock cursor movement/viewing, not actual input the AI doesn't expect.
