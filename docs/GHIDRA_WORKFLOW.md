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

## Lighter alternative: capstone (`tools/disasm_thumb.py`)

Session 4 found `ReadKeys` and retracted the `0x0300018F` turn-flag theory
without Ghidra, in minutes: find aligned literal-pool words equal to a RAM
address (`lit`), then disassemble around the loads that use them (`dis`).
This ROM's code loads RAM addresses as literal-pool constants (or a struct
base + small offset), so it works well. Its limit: no code/data separation
or function boundaries, so literal pools disassemble as garbage, and there
are false-positive literal hits inside data (anything past ~`0x08300000` is
likely data). Use Ghidra when you need real xrefs / call graphs / the
decompiler.

Note: older docs said a raw grep for `0x0300018F` found 2 unaligned hits.
That grep searched the wrong bytes (`b2 01 00 03` = `0x030001B2`); the
correct little-endian bytes `8f 01 00 03` appear **nowhere** in the ROM.
And `0x0300018F` turned out not to be a turn flag anyway (see
`MEMORY_FINDINGS.md`).

## Next task for Ghidra

Find WC06's CPU-turn dispatcher (EDS: `AiRunTurn`) and the human
field-cursor handler. Import with the ROM base set so xrefs resolve:
`-loader BinaryLoader -loader-baseAddr 0x08000000`, and add uninitialized
memory blocks for EWRAM (`0x02000000`, `0x40000`), IWRAM (`0x03000000`,
`0x8000`) and I/O (`0x04000000`, `0x400`) before analysis — without them,
references into RAM have nowhere to point. (The Session 1 import did
neither, as far as these docs record.)
