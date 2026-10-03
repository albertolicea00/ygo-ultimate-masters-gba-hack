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

## Open questions

- Exact ROM offset of the card-art block in *this* file (not EDS).
- Exact RAM address (and controlling code) of the active-player/input-lock
  flag.
- Exact illustration-crop rectangle needed per card-frame era, to go from the
  Project Kaiba full-card `sd` JPGs to just the artwork.
