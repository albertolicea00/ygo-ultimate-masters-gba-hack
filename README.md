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
- `docs/`: Write-ups and running logs. See [`docs/REVERSE_ENGINEERING_LOG.md`](docs/REVERSE_ENGINEERING_LOG.md)
  for concrete findings, confirmed offsets, and working techniques (toolchain setup gotchas,
  the live mGBA automation harness, in-game navigation steps, etc.) — read this before
  re-deriving something that may already be solved.
