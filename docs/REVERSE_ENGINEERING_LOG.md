# Reverse Engineering Log

Running log of concrete findings and working techniques, so future sessions (or other
contributors) don't have to rediscover them. Append new entries at the bottom with a date.

## ROM identification

- File: `.workspace/trm-yum6.gba` (32MB / 0x2000000, CRC32 `0xf968a196`).
- Header title: `YUGIOHWCT06`, game code `BY6E`, maker `A4` (Konami).
- This is **Yu-Gi-Oh! World Championship Tournament 2006**. "Ultimate Masters" /
  "trm-yum6" appears to be a translation/fix romhack on top of the same base — the
  card-name text table is at the *same* offset the public WC06 documentation gives
  (see below), so community docs for WC06 apply directly to this file.

## Confirmed via direct ROM inspection

- `"Blue-Eyes White Dragon"` ASCII string found at file offset `0x015BB5AC`.
  Matches Data Crystal's documented card-name table base (`~0x015BB594`,
  0x18-byte header per entry). **This confirms the public WC06 ROM map
  (Data Crystal) is valid for this exact file.**
- Card ID conversion table (per Data Crystal): file offset range
  `~0x015B7CCC`–`~0x015B917B` (~9500 x u16 entries — consistent with a large
  hacked card roster).
- Card art format is **not** documented anywhere publicly for this game. Our
  working hypothesis (from the sibling engine, see below) is fixed-size
  72x80 images, 6bpp indexed (64 colors), with a contiguous palette block
  (BGR555) after all image data — **not yet confirmed against this ROM's
  actual offsets.** Don't assume the hypothesis numbers (resolution/bpp) are
  exactly right until cross-checked against real extracted tile data.
- **Important correction from a second project working with the source card
  images** (Project Kaiba, uses the same `data/base/pics/cards/<tier>/<passcode>.jpg`
  images): WC06's in-game card art is a crop of just the illustration, not the
  full card (frame, name box, text). Our source JPGs (`sd` tier, 268x391) are
  full-card scans. Naive downscale will NOT match — the illustration needs to
  be cropped out first, and the crop region varies by card frame era. Budget
  real time for this; it's not a one-line resize.

## Reference material (not this ROM, but same engine family)

- Cloned `CosmicScribe64/eds-decomp` into `.workspace/refs/eds-decomp` — a
  byte-matching decompilation of *Yu-Gi-Oh! The Eternal Duelist Soul* (GBA),
  same Konami duel-engine lineage. **Addresses do NOT transfer** (different
  ROM, different build), but struct layouts, function names, and general
  control flow are a very useful Rosetta stone. Useful files:
  - `tools/assets.py` — exact card-art extraction logic (`x_card_art`): fixed
    `ART_SIZE` per card, then a contiguous `CARD_COUNT * 0x80`-byte palette
    block (64 x u16 BGR555 per card) right after all image data.
  - `wiki/functions/duel-cursor-c.md`, `wiki/functions/duel-field-moves-c.md` —
    cursor/navigation and field-event handling, useful for understanding what
    kind of code to look for in Ghidra, not useful for direct addresses.

## Toolchain setup notes (macOS, Homebrew)

- `brew install ghidra` and `brew install --cask mgba-app` both intermittently
  fail downloading from `ghcr.io` (HTTP/2 stream errors) — this is a registry/
  network issue, not a real problem with the formula. Just retry; it eventually
  succeeds. (A direct GitHub-release zip download is a fallback but slower.)
- Ghidra via Homebrew ships without a usable JDK pinned; it picks up whatever
  `JAVA_HOME` resolves to (e.g. via `jenv`), which may be too old (Ghidra 12.x
  needs JDK 21+). Fix: `brew install openjdk@21`, then edit
  `/opt/homebrew/Cellar/ghidra/<version>/libexec/support/launch.properties`
  and set `JAVA_HOME_OVERRIDE=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home`.
  Exporting `JAVA_HOME` in the shell is not reliable (something re-resolves it
  to the jenv-managed version first), the properties file is what actually sticks.
- `analyzeHeadless` rejects project paths with a leading-dot path segment
  (e.g. `.workspace/ghidra_project`) — "Path element starting with '.' is not
  permitted". Use a plain path like `/tmp/ghidra_project` instead.
- Importing + auto-analyzing this 32MB ROM as raw `ARM:LE:32:v4t` took **~46
  minutes** headless on this machine. Budget for that; it's not interactive.

## Live automation harness (mGBA, no manual interaction)

Built because neither direct memory pokes nor a Python mGBA binding were
available (there is no `pip install mgba`; the real bindings are built from
source via SWIG and aren't on PyPI). What actually works, end to end:

1. **Input injection**: mGBA's GDB stub (`--gdb` CLI flag) does *not* let you
   write the `KEYINPUT` I/O register (`0x04000130`) via debugger memory writes
   — confirmed empirically: writes to plain EWRAM (`0x02000000`) stick, writes
   to the I/O region silently don't. mGBA's own **Lua scripting console**
   (`Tools > Scripting...` in the GUI) is the real way: `emu:setKeys(mask)`
   actually drives input. Standard GBA key bitmask: A=1, B=2, Select=4,
   Start=8, Right=16, Left=32, Up=64, Down=128, R=256, L=512.
2. **Driving the Lua console without touching the mouse/keyboard**: macOS
   Accessibility (`osascript` + System Events) can type into the Scripting
   window's input field and click its "Run" button programmatically —
   `tell application "System Events" to tell process "mGBA" to ...`. This
   works on an app with *no* AppleScript dictionary of its own, because
   System Events drives any app's UI via the Accessibility API.
   - Gotcha: if more than one "Scripting" window is open (e.g. opened twice
     by mistake), window-by-name references become ambiguous. Keep exactly one.
   - Gotcha: referencing `window 1` is only reliable if focus/z-order is
     predictable. Querying the window list once per call and asserting on the
     expected title is more robust than hardcoding an index blindly.
3. **Seeing the screen without manual interaction**: `python3 -c
   "import Quartz; ..."` (pyobjc, already available on this machine) with
   `CGWindowListCopyWindowInfo` + `CGWindowListCreateImage` grabs a specific
   window's framebuffer by matching its `kCGWindowName`/`kCGWindowOwnerName`,
   independent of what's frontmost. Match on a specific, distinctive title
   substring (e.g. `"mGBA -"`) — a generic substring like `"Yu-Gi-Oh"` can
   accidentally match an unrelated window (e.g. an IDE with the project name
   in its title bar).
4. **Critical gotcha**: while the GDB stub has the CPU **interrupted**
   (`process interrupt` and no matching `c`/continue yet), mGBA's own windows
   stop compositing entirely — `CGWindowListCopyWindowInfo` returns *zero*
   mGBA windows during that window, for the whole app, not just rendering
   garbage. Always resume (`c`) before trying to screenshot or otherwise
   interact with the GUI.
5. **Reading memory live**: connect with `lldb` (no plain `gdb`/`gdb-multiarch`
   on this machine, but `lldb` speaks the GDB remote protocol fine):
   `lldb` → `gdb-remote localhost:2345`. Avoid lldb's `expression` command for
   anything target-memory-related on this bare/no-executable-module target —
   it silently no-ops (assignment "succeeds" and prints a value, but nothing
   is actually written, confirmed by immediate readback). Plain `memory read`
   / `memory write` commands work correctly. Default read size cap is small;
   raise it once per session: `settings set target.max-memory-read-size 1048576`.
   Dump a full region to a file with
   `memory read --outfile <path> --binary <start> <end>`.
6. **Keeping one lldb session alive across many separate tool calls**: a
   named FIFO (`mkfifo`) fed by a long-lived no-op holder process
   (`bash -c 'exec 9>fifo; sleep 100000' &`) keeps the write end open so the
   reader (`lldb < fifo`) never sees EOF. Then `echo "cmd" > fifo` from any
   later, unrelated shell invocation drives the same persistent lldb session.
   Without the holder process, each `echo >` open-and-close cycle delivers an
   EOF to lldb's stdin and kills its command loop.
7. **In-game navigation learned for this build** (Free Duel / Campaign vs.
   Kuriboh, level 1): title screen → Start → name entry (on-screen keyboard,
   arrow keys + A to pick letters, navigate to "OK") → "Ok?" Yes/No → icon
   select → first-deck select → main menu (Deck Edit / Free Duel / Challenge /
   Get Cards / Forb-Ltd Lists / Options) → Free Duel → opponent select →
   coin toss → real duel. **Phase control**: pressing **B** while a field zone
   (not a card) is selected opens a direct "Select phase to enter" menu
   (M1 / BP / EP) — this is the real way to skip straight to End Phase,
   not Start (Start opens card-detail when a card is selected) and not the
   L/R shoulder buttons (tried, no effect). At 7+ cards in hand, End Phase
   triggers a mandatory "Discard from your hand" prompt first.
8. **Open problem, in progress**: pinpointing the exact RAM address of the
   active-turn/input-lock flag. A naive "end turn, then poll-interrupt-dump
   every ~150ms for ~1.5s" burst was too slow relative to how fast the CPU
   opponent actually plays — all samples landed before anything changed
   (same LP, same hand). The CPU's whole turn (draw, main phase play, attack)
   seems to resolve in well under a second once any blocking prompt (like
   the discard above) is out of the way. Next attempt: use an in-process Lua
   `callbacks:add("frame", fn)` hook to sample from *inside* mGBA (no
   screenshot/AppleScript round-trip latency) rather than an external bash
   polling loop.

## Session 2 update — turn-flag hunt, still open

Spent a long session trying to pin down the exact moment of "opponent's turn active"
via burst-sampling EWRAM. Concrete findings, still unresolved:

- A plain bash polling loop (interrupt → dump → continue → sleep ~150ms, repeated)
  is **too slow**: the CPU opponent's entire turn (draw, main phase play, attack)
  resolves in well under a second once no blocking prompt is in the way. All 12
  samples in one such burst showed identical state (same LP, same hand) — the
  real transition happened in the gap *after* the burst loop, before the next
  screenshot.
- Switched to an in-process Lua `callbacks:add('frame', fn)` sampler (armed via
  the Scripting console, writes `emu:readRange(0x02000000,0x40000)` to a new file
  every N frames) — this avoids external polling latency entirely. Confirmed
  working: `luaFrameN` global increments correctly frame-by-frame even across
  many separate `osascript` calls (checked by reading the variable back twice a
  second apart: advanced ~67 frames in ~1s, i.e. the core really is running at
  roughly full speed throughout).
- At 7 cards in hand, End Phase triggers a mandatory **"Discard from your hand"**
  prompt. This uses the *same full-board cursor grid* as normal play (confirmed:
  Up/Down cycles through all zone rows on both sides, wrapping top-to-bottom) —
  it is NOT restricted to the hand row. Pressing A while the cursor sits on a
  zone that isn't a valid discard target (e.g. an opponent zone, or an empty
  slot) is silently ignored — nothing visibly changes, no error, which looks
  identical to "input not being delivered" and cost a lot of back-and-forth to
  rule out. **Before touching A here, confirm via screenshot that the cursor
  box is actually sitting on one of your own hand cards.**
- Belt-and-suspenders fix applied: `run_lua.sh` now targets
  `window "Scripting"` by name (was `window 1`, which is only correct when the
  Scripting window happens to be frontmost/first — not guaranteed) and retries
  up to 5x on transient System-Events window-enumeration errors (these happen
  occasionally and seem environmental — e.g. this Mac is in active interactive
  use by its owner at the same time — not caused by anything in our scripts).
- **Still not found**: the actual RAM address of the active-player/input-lock
  flag. Next session should pick this back up either by (a) retrying the
  frame-callback capture now that the discard-prompt confusion is understood
  and documented, ideally arming the sampler right as End Phase is confirmed
  and *before* fighting with any discard prompt, or (b) going straight to
  Ghidra: the ROM is already imported and fully auto-analyzed in
  `/tmp/ghidra_project/wct06` (not in the repo — regenerate with
  `analyzeHeadless /tmp/ghidra_project wct06 -import <rom> -processor "ARM:LE:32:v4t"`
  if that scratch dir is gone), search for code that reads I/O register
  `0x04000130` (KEYINPUT) and trace which callers gate on a turn/side check
  before acting on it.

## Session 2 end-of-session status (stopped mid-attempt, resume here)

Root cause confirmed from this session, two blockers that ate most of the time:

1. **The CPU opponent's entire turn resolves in well under 4 frames** once no
   prompt is blocking it (draw, main-phase play, attack all happen near-instantly
   at this difficulty). A 2-frames-per-sample Lua callback already missed it
   entirely (LP had already changed by the very first sample). **Sampling must
   be every single frame (`luaSampleEvery=1`), armed immediately before the
   keypress that confirms End Phase** — not after, not a coarser stride.
2. **Another environmental gotcha found this session, likely the root cause of
   most of the earlier "input isn't registering" confusion**: this is the
   user's actively-used Mac, and when they switch Spaces/apps away from mGBA,
   both `CGWindowListCopyWindowInfo` (Quartz, screenshot capture) and System
   Events UI scripting stop seeing mGBA's windows at all (not an error, just
   genuinely not there — `CGWindowListOptionOnScreenOnly` only sees windows on
   the active Space). Fix applied: `run_lua.sh` now runs
   `osascript -e 'tell application "mGBA" to activate'` first, which switches
   back to mGBA's Space automatically. Do this (or check it already happened)
   before trusting any "button press had no visible effect" observation.

Still true from earlier: discard-prompt cursor needs ~5 Down presses from a
fresh prompt to reach the hand row (it starts somewhere over the board, not
the hand) before A does anything.

**Exact point to resume from**: mid-way through handling a "Discard from your
hand" prompt (hand was back up to 7 after drawing "Creature Swap"). Plan for
next session, in order:
1. Press Down ~5x (screenshot-verify the cursor box lands on an actual hand
   card, not a field zone) and discard with A.
2. *Immediately* arm the Lua sampler with `luaSampleEvery=1`,
   `luaSampleMax` around 90–120 (1.5–2s at 60fps) via the Scripting console
   REPL — this is the actual capture window, no more messing with phase
   menus after this point.
3. Let it run untouched for ~2s real time, then pull the dumped frame files
   from `.workspace/claude_session/screenshots/luaburst/` (named `fNNNNNN.bin`,
   raw 256KB EWRAM each) and diff consecutive frames in Python
   (`struct`/byte-compare) to find exactly which frame the LP value changes on
   (search for the known pre-attack and post-attack LP as u16 little-endian,
   same technique as the `6300`/`4600`/`2900` searches earlier in this file) —
   then look at what *else* changed in that same frame or the few frames
   right before it. That's the turn-flag candidate.
4. Cross-check any candidate address against Ghidra (already imported +
   analyzed at `/tmp/ghidra_project/wct06` — regenerate if that scratch dir
   is gone) by finding what code reads it and confirming it also gates the
   d-pad/cursor-movement handler, not just something incidental.

## Session 3 — found the turn-state flag, causal proof still pending

**Root cause: the live duel state is in IWRAM (`0x03000000`, 32KB), not EWRAM.**
Proven by capturing 240 consecutive frames of EWRAM (`0x02000000`-`0x02040000`)
spanning an entire duel turn, including a full duel ending (win/loss screen) —
every single byte was identical across all 240 frames, despite the game state
changing enormously. EWRAM in this build holds static data (card tables,
text); the mutable per-duel state (whose turn, phase, LP, etc.) lives in
IWRAM instead. This single finding is why earlier EWRAM-based burst-sampling
attempts (Session 2) could never have worked, no matter how fine the timing.

**Strong candidate for the active-turn/input-lock flag: IWRAM offset `0x18F`
(absolute address `0x0300018F`).** Found by sampling IWRAM every single frame
(no stride) across a full End-Phase → opponent-turn → back-to-me cycle (300
frames). Value sequence: `252` (frames 1–32, my End Phase still resolving) →
`0` (frames 33–74, opponent's entire turn) → `252` (frames 75–300, back on my
turn). This is the cleanest signal found — a single step down and a single
step back up, landing exactly on the turn boundaries. No other byte in all of
IWRAM showed a pattern this clean (checked all offsets with ≤6 value
transitions across the capture; most of those were 1-frame animation pulses
tied to the transition *event*, not a persistent state — `0x18F` is the one
persistent value that tracks the *state*). Likely encoding: `0xFC` (252) =
"it's your turn", `0x00` = "not your turn" (sentinel-style boolean, not a
literal 0/1 — common in this era of GBA code).

A live frame-callback patch was installed via the Lua console and left
running:
```lua
callbacks:add('frame', function()
  if emu:read8(0x0300018F) == 0 then emu:write8(0x0300018F, 252) end
end)
```
This correctly fires (confirmed non-zero `luaForceCount`), but **we have not
yet confirmed it actually restores field navigation during the opponent's
turn.** The blocker is purely practical: the CPU opponent's entire turn
resolves in well under a second (consistent with Session 2's finding), which
is faster than any human-speed loop of "press a direction key via
AppleScript → screenshot → look" can react to. Every attempt this session to
manually test "can I move the cursor right now" landed after the turn had
already passed back to the human player naturally, so the screenshots prove
nothing either way about whether the patch worked.

**Next step, concretely**: don't test this by hand. Write the whole
test — force the flag, inject a direction key via `emu:setKeys()`, and check
whether some cursor-position byte actually moved — as one self-contained Lua
script run from a single frame callback, so it all happens at emulator frame
granularity with no AppleScript/screenshot round-trip in the loop at all. That
requires first finding the cursor-position byte in IWRAM the same way `0x18F`
was found: diff IWRAM frame-by-frame while manually pressing a direction key
during a normal (player) turn, and look for the byte whose value changes
exactly on those frames. A first attempt at this today was contaminated — the
two scripted Right-presses landed on a phase-select menu instead of moving
the field cursor (the cursor context from a prior step was already on a
menu-opening icon, not a field zone) — so the capture didn't isolate the right
byte. Redo this cleanly: confirm via screenshot that the ally cursor is on a
plain field/hand zone (not a special icon) *before* arming the sampler and
pressing Right.

### Environment gotcha found this session: macOS Accessibility permission

A big chunk of this session's early flakiness (`"Can't get window ... of
process mGBA"`, inputs silently not registering) turned out to be **macOS
revoking/never-granting the Accessibility permission** for the terminal app
running these scripts, not a Spaces/focus issue as first suspected in Session
2. The actual error when this happens is explicit and unambiguous:
`"osascript is not allowed assistive access."` — if that string appears,
stop debugging the script logic and go straight to **System Settings →
Privacy & Security → Accessibility** and check the terminal app is toggled
on. Symptoms *without* that explicit error (just "can't get window", window
lists coming back empty) are more likely the Spaces/focus issue from Session
2 — `run_lua.sh` now self-heals that by activating mGBA before every call.

## Open questions

- Exact ROM offset of the card-art block in *this* file (not EDS).
- Exact RAM address (and controlling code) of the active-player/input-lock
  flag.
- Exact illustration-crop rectangle needed per card-frame era, to go from the
  Project Kaiba full-card `sd` JPGs to just the artwork.
