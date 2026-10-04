# Live automation harness (mGBA + Lua + macOS Accessibility)

How we drive and inspect a running duel with no manual interaction, and
the gotchas that cost the most time to figure out. Read this before
re-deriving any of it.

## Why this exists

There's no `pip install mgba` — the real Python bindings for mGBA are built
from source via SWIG and aren't published to PyPI. mGBA's GDB stub
(`--gdb` CLI flag) also does **not** let you write the `KEYINPUT` I/O
register (`0x04000130`) via debugger memory writes (confirmed empirically:
writes to plain EWRAM stick, writes to the I/O region silently don't). So
there's no simple "just script memory writes" path to simulated input.

What *does* work end to end: mGBA's own **Lua scripting console**
(`Tools > Scripting...` in the GUI) plus macOS Accessibility (driving that
GUI's text field and Run button from the outside, headlessly).

## Components

### 1. Launching mGBA with the GDB stub (for live memory reads via lldb)

```
/Applications/mGBA.app/Contents/MacOS/mGBA --gdb <path-to-rom> > /tmp/mgba_run.log 2>&1 &
```
`--gdb` starts the CPU **halted**, waiting for a debugger to connect, so the
game window stays black until something connects and issues `continue`.

### 2. Connecting with lldb (there's no plain `gdb` on this Mac, but lldb
speaks the GDB remote protocol fine)

```
lldb
(lldb) gdb-remote localhost:2345
(lldb) c
```
Gotchas:
- Avoid lldb's `expression` command for target-memory writes on this bare
  target (`Target 0: (No executable module.)`) — it silently no-ops: the
  assignment "succeeds" and prints a value, but a readback immediately after
  shows nothing was actually written. Use plain `memory read` / `memory
  write` instead, which work correctly.
- Default read size cap is small (1024 bytes). Raise it once per session:
  `settings set target.max-memory-read-size 1048576`.
- Dump a whole region to a file: `memory read --outfile <path> --binary
  <start> <end>`.
- **Keeping one lldb session alive across many separate shell invocations**:
  a named FIFO fed by a long-lived no-op holder process keeps the write end
  open so the reader never sees EOF:
  ```bash
  mkfifo /tmp/lldb_in
  bash -c 'exec 9>/tmp/lldb_in; sleep 100000' &    # holder, keeps fifo open
  lldb < /tmp/lldb_in > /tmp/lldb_out.log 2>&1 &
  echo "memory read ..." > /tmp/lldb_in             # from any later shell
  ```
  Without the holder, each `echo >` open-and-close cycle delivers an EOF to
  lldb's stdin and kills its command loop.

### 3. Driving the Lua console headlessly (the real input-injection path)

mGBA's Lua API (confirmed from the bundled `pokemon.lua` sample and direct
testing):
- `emu:setKeys(mask)` — force the input state for the next poll. Standard
  GBA bitmask: A=1, B=2, Select=4, Start=8, Right=16, Left=32, Up=64,
  Down=128, R=256, L=512.
- `emu:read8/16/32(addr)`, `emu:readRange(addr, len)` (returns a raw Lua
  string), `emu:write8(addr, val)` — full address-space memory access,
  including IWRAM/EWRAM directly (no special "which region" ceremony needed,
  just pass the real address like `0x03000000` or `0x02000000`).
- `io.open(path, mode)` works — the Lua sandbox allows real file I/O, used
  for dumping memory snapshots and writing results.
- `callbacks:add('frame', fn)` registers a per-frame hook. There is no
  documented "remove callback" we've used — once armed, a hook keeps running
  until it self-disables via a guard variable (e.g. `if count >= max then
  return end`). **Multiple armed hooks from different experiments run
  concurrently and can share global variables accidentally** — always use
  fresh, distinctly-named globals per experiment rather than reusing
  `luaSampleCount` etc., or old hooks interfere with new ones.
- `console:log(msg)` writes to the in-app console pane only — it does
  **not** appear in the process's redirected stdout/stderr log file. If you
  need output visible from outside, write to a file with `io.open`, or
  screenshot the Scripting window's console pane.

Driving the console's input field and Run button from outside, with no
mouse/keyboard, via macOS Accessibility:
```applescript
tell application "System Events"
    tell process "mGBA"
        set value of text field 1 of splitter group 1 of window "Scripting" to "<lua code>"
        click button "Run" of splitter group 1 of window "Scripting"
    end tell
end tell
```
This works on an app with **no AppleScript dictionary of its own**, because
System Events drives any app's UI via the Accessibility API, not the app's
own scripting support.

### 4. Screenshotting a specific window (no mouse, no frontmost assumptions)

```python
import Quartz
windows = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
# match on kCGWindowName or kCGWindowOwnerName, then:
image = Quartz.CGWindowListCreateImage(Quartz.CGRectNull, Quartz.kCGWindowListOptionIncludingWindow, wid, Quartz.kCGWindowImageBoundsIgnoreFraming)
```
pyobjc (the `Quartz` module) is already available on this machine, no install
needed.

## Gotchas that cost real time

1. **`osascript is not allowed assistive access.` (error -10006, sometimes
   phrased as "Can't set/get window ... of process mGBA")** — this is macOS
   **revoking or never granting the Accessibility permission** for the
   terminal app running these scripts. Fix: **System Settings → Privacy &
   Security → Accessibility**, toggle the terminal app on (toggle it off and
   back on if it's already listed but still failing, to force a refresh).
   This is a real permission a human has to click — it cannot be granted
   from a script. If you see this exact error string, stop debugging script
   logic and go straight to that settings pane.
2. **Window titles/CGWindowListCopyWindowInfo results can blank out or
   vanish transiently** even with permission correctly granted — on a Mac
   actively being used interactively by its owner (Spaces switches, other
   apps gaining focus), mGBA's windows briefly stop being enumerable by
   Quartz and System Events. Fix applied: `run_lua.sh` runs
   `osascript -e 'tell application "mGBA" to activate'` first, which
   switches back to mGBA's Space/brings it forward automatically. Retry a
   few times with a short sleep rather than treating one failure as fatal.
3. **While the GDB stub has the CPU interrupted (`process interrupt`, no
   matching `c` yet), mGBA's own windows stop compositing entirely** —
   `CGWindowListCopyWindowInfo` returns zero mGBA windows for the *whole
   app* during that window, not just garbled output. Always resume (`c`)
   before trying to screenshot or otherwise interact with the GUI.
4. **Matching windows by a generic title substring is dangerous** — e.g.
   matching `"Yu-Gi-Oh"` once accidentally grabbed an unrelated IDE window
   that had the project's name in its own title bar. Match on something
   specific and distinctive, like `"mGBA -"` (the actual emulator window
   title always starts with that), and explicitly exclude/avoid the
   `"Scripting"` window by name when you want the game view, not the console.
5. **Two "Scripting" windows open at once makes window-by-name references
   ambiguous.** Keep exactly one open; close duplicates before continuing.
6. **The CPU opponent's entire turn can resolve in well under a second**
   (confirmed: under ~45 frames, i.e. under 0.75s at 60fps) once no blocking
   prompt (like a mandatory discard) is in the way. Any test that relies on
   an external human-speed round trip (AppleScript call → sleep → screenshot
   → look) will usually land *after* the turn has already passed back,
   proving nothing. **Do time-sensitive verification entirely inside a
   single Lua frame callback** (inject input, read results, all on
   consecutive frames) instead of bouncing out to the shell.
7. **Discard-prompt cursor quirk**: at 7+ cards in hand, End Phase triggers a
   mandatory "Discard from your hand" prompt. Its cursor uses the *same
   full-board grid* as normal play (confirmed: Up/Down cycles through every
   zone row on both sides, wrapping top-to-bottom) — it is not restricted to
   the hand row, and it doesn't reliably start there either. Pressing A
   while the cursor sits on a zone that isn't a valid discard target is
   silently ignored (no error, nothing visibly changes), which is easy to
   mistake for "my input isn't being delivered at all". Verify via
   screenshot that the cursor box is actually on one of your own hand cards
   before pressing A.

## Helper scripts (in `.workspace/claude_session/scripts/`, gitignored)

- `run_lua.sh <lua code>` — sends one line of Lua to the Scripting console
  and clicks Run. Activates mGBA first, retries a few times on transient
  Accessibility errors.
- `press_key.sh <mask> [times] [hold_s] [gap_s]` — presses a button (or
  button combo bitmask) N times via `run_lua.sh`, holding and releasing with
  configurable timing.
- `capture_window.py <title-substring> <output-path>` — screenshots a
  specific window by matching a distinctive title substring.
- `capture_by_owner.py <owner-substring> <output-path>` — fallback that
  matches by owning-process name instead of title, for when titles are
  blank (picks the largest matching window — careful, this can grab the
  Scripting console if it happens to be larger than the game window).

## In-progress: fully in-Lua causal test (started, not finished)

Goal: prove the `0x18F` turn-flag patch (see `MEMORY_FINDINGS.md`) actually
restores navigation, without any human-speed round trip. Draft state-machine
callback (needs the cursor-position IWRAM byte identified first — not yet
found cleanly, see `MEMORY_FINDINGS.md` "Not yet found"):
```lua
luaCT_state=0; luaCT_frame=0; luaCT_base=nil; luaCT_after=nil
callbacks:add('frame', function()
  if luaCT_state==0 then
    luaCT_base = emu:readRange(0x03000000,0x8000)
    emu:setKeys(16)  -- Right
    luaCT_state=1; luaCT_frame=0
  elseif luaCT_state==1 then
    luaCT_frame=luaCT_frame+1
    if luaCT_frame>=6 then emu:setKeys(0); luaCT_state=2; luaCT_frame=0 end
  elseif luaCT_state==2 then
    luaCT_frame=luaCT_frame+1
    if luaCT_frame>=10 then
      luaCT_after = emu:readRange(0x03000000,0x8000)
      -- diff luaCT_base vs luaCT_after, write result to a file
      luaCT_state=3
    end
  end
end)
```
First run produced no output file — needs debugging (check the Scripting
console pane for a Lua error before assuming the file path is wrong).
