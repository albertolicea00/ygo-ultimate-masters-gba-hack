# Ghidra workflow

Static-analysis side of the project. Separate from the live/dynamic
mGBA+Lua harness (`LUA_AUTOMATION.md`) — this is for once we have a RAM
address (from the dynamic side) and need to find the actual code that reads
it.

## Install (macOS, Homebrew)

```
brew install ghidra
brew install openjdk@21
```
Gotchas:
- Both of these intermittently fail downloading from `ghcr.io` ("HTTP/2
  stream was not closed cleanly" / "PROTOCOL_ERROR"). This is a registry/
  network issue, not a problem with the formula — just retry (`brew install
  <name>` again); it isn't a permanent block, it eventually succeeds.
- Ghidra via Homebrew does **not** pin a working JDK — it picks up whatever
  `JAVA_HOME` resolves to (e.g. via `jenv`), which may be too old. Ghidra
  12.x needs **JDK 21+**; this machine's default/jenv-managed JDK was 17,
  which Ghidra rejects with `WARNING: JAVA_HOME environment specifies
  unsupported java version`. Exporting `JAVA_HOME` in the shell did **not**
  fix it (something re-resolves it back to the jenv version first). What
  actually works: edit the properties file directly —
  ```
  /opt/homebrew/Cellar/ghidra/<version>/libexec/support/launch.properties
  ```
  and set:
  ```
  JAVA_HOME_OVERRIDE=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
  ```
- `analyzeHeadless` lives at
  `/opt/homebrew/Cellar/ghidra/<version>/libexec/support/analyzeHeadless`
  (not on `PATH` by default under that name — `ghidraRun` is linked into
  `/opt/homebrew/bin`, but `analyzeHeadless` isn't).

## Importing + analyzing the ROM

```bash
mkdir -p /tmp/ghidra_project   # NOT a dot-prefixed path, see below
/opt/homebrew/Cellar/ghidra/<version>/libexec/support/analyzeHeadless \
  /tmp/ghidra_project wct06 \
  -import "<path-to-rom>/trm-yum6.gba" \
  -processor "ARM:LE:32:v4t"
```
Gotchas:
- `analyzeHeadless` **rejects project paths with a leading-dot path
  segment** (e.g. `.workspace/ghidra_project`) with "Path element starting
  with '.' is not permitted". Use a plain path like `/tmp/ghidra_project`.
- Importing + full auto-analysis of this 32MB ROM as raw `ARM:LE:32:v4t`
  took **~46 minutes** headless on this machine. It's not interactive —
  kick it off in the background and do something else while it runs.
- **`/tmp` does not survive a reboot** (confirmed: the project built in an
  earlier session was gone the next day). If you need the analyzed project
  to persist across sessions, either put it somewhere durable (e.g. inside
  `.workspace/`, which is gitignored but on disk persistently) or just
  budget the 46 minutes again each fresh session.

## What we haven't done yet with it

We have **not yet** used Ghidra's actual decompiler/xref tools on this ROM
— the single import+analyze run so far was to have the project ready, but
the project itself was lost to a `/tmp` cleanup before we got to use it for
anything. Everything in `MEMORY_FINDINGS.md` about the `0x0300018F` flag was
found via the *dynamic* (mGBA+Lua) side only.

## The actual next task for Ghidra

Once the project is (re-)built: find what code reads IWRAM address
`0x0300018F` (the turn-flag candidate, see `MEMORY_FINDINGS.md`) and
confirm it also gates the d-pad/cursor-movement handler specifically (not
some unrelated consumer of the same byte).

A raw byte-grep of the ROM for `0x0300018F` as a little-endian 32-bit
literal-pool constant (`b2 01 00 03`... wait, actually `8f 01 00 03`) found
**2 hits, both at non-4-byte-aligned file offsets** — a real Thumb/ARM
literal pool word can never be at an unaligned offset, so both hits are
almost certainly coincidental byte patterns in unrelated code/data, not real
references. This means the address is probably **constructed arithmetically**
in the actual code (e.g. a base pointer like `0x03000180` or a register
computed via `mov`/`lsl`/`add`, then a byte offset of `0xF` or `0x3`/`0xB`
applied via the addressing mode) rather than loaded as one raw literal — so
finding the real reference needs Ghidra's proper code/data-aware
disassembly and xref engine, not a naive byte search (a naive linear
disassembly pass also doesn't work well — tried once, it produces garbage
because Thumb code is interspersed with literal-pool data that isn't
instructions, and without knowing the real function boundaries you can't
tell which bytes are which; this is exactly the problem Ghidra's analysis
pass solves).

Suggested approach once the project exists:
1. Import + analyze (46 min, see above).
2. Use Ghidra's "Search → For Scalars" or a small Ghidra script
   (Python/Java) to find every instruction whose computed effective address
   equals `0x0300018F` (not just literal-pool hits) — this requires actual
   constant-propagation/decompilation, which Ghidra does provide via its
   decompiler, unlike a raw disassembly pass.
3. For each hit, check (a) is it inside a function that also reads
   `KEYINPUT`/handles the d-pad, and (b) does it feed a conditional branch
   that would skip input handling when the byte is non-`0xFC`.
4. Once confirmed, that conditional branch (likely a `BEQ`/`BNE` after a
   `CMP`) is the actual patch target for a permanent IPS/BPS fix — instead
   of forcing the RAM value every frame (the current live-patch approach),
   you'd flip or NOP that one branch so the check never fails.
