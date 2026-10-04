# Yu-Gi-Oh! Ultimate Masters (GBA) - Romhack Project

This project is a romhack for the GBA game *Yu-Gi-Oh! World Championship Tournament 2006* (specifically the "Ultimate Masters" patch/version).

## Project Goals

1. **Graphic Modification (SD/HD Cards):**
   - Replace the original card graphics in the ROM with higher-quality versions downscaled from an external source. (Target format: 72x80, 6bpp indexed, 64 colors).
2. **Gameplay Logic Modification (Opponent Turn Navigation):**
   - Enable the ability to navigate the field and view cards while the opponent is taking their turn. This requires reverse engineering and patching the main duel loop logic.

## Tools Used

- **mGBA**: Main emulator used for live debugging via its integrated GDB server.
- **Ghidra**: Used for static analysis and ROM disassembly (ARM/Thumb architecture).
- **Python**: Scripts for image processing, ROM manipulation, and debugging automation.

## Directory Structure

- `.workspace/`: Temporary files, working ROMs, and reference repositories (e.g., decompilations). *Not versioned*.
- `tools/`: Utility scripts created during the reverse engineering process.
- `docs/`: Write-ups, findings, and working techniques — **read these before re-deriving
  something that may already be solved**:
  - [`docs/ROADMAP.md`](docs/ROADMAP.md) — current status of both project goals and the
    concrete next step for each.
  - [`docs/MEMORY_FINDINGS.md`](docs/MEMORY_FINDINGS.md) — confirmed ROM/RAM facts: offsets,
    addresses, the turn-flag candidate, what's still unconfirmed.
  - [`docs/LUA_AUTOMATION.md`](docs/LUA_AUTOMATION.md) — how the live mGBA automation harness
    works (Lua console scripting, macOS Accessibility, screenshotting) and its gotchas.
  - [`docs/GHIDRA_WORKFLOW.md`](docs/GHIDRA_WORKFLOW.md) — how to set up and use Ghidra for
    the static-analysis side (install gotchas, importing/analyzing this ROM, next steps).
  - [`docs/REVERSE_ENGINEERING_LOG.md`](docs/REVERSE_ENGINEERING_LOG.md) — short append-only
    chronological log, one entry per session, pointing into the docs above.
