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
