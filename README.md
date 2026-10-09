# Yu-Gi-Oh! Ultimate Masters (GBA) - Romhack Project

This project is a romhack for the GBA game *Yu-Gi-Oh! World Championship Tournament 2006* (specifically the "Ultimate Masters" patch/version).

## Project Goals

1. **Gameplay Logic Modification (Opponent Turn Navigation):** ✅ **done — shipped as [`patch/oppnav.ips`](patch/oppnav.ips)**
   - Navigate the field and view cards while the opponent is taking their turn. Reverse-engineered and patched the duel loop; press **Select** on the CPU's turn to browse. See the [patch section below](#the-patch).
2. ~~**Graphic Modification (SD/HD Cards):**~~ ❌ **(dropped — see below)**
   - ~~Replace the original card graphics in the ROM with higher-quality versions downscaled from an external source. (Target format: 72x80, 6bpp indexed, 64 colors).~~
   - **Why dropped:** we focused on goal 1 (which is now shipped), and this one is a bigger, separate pipeline with blockers still open. The approach is clear and feasible in principle — pull each card's illustration at higher quality, crop it to the in-game art rectangle, re-encode to the GBA's format, and write it back over the originals. But it is *not* a quick win:
     - **The art block was never located.** Its real ROM offset is still unknown; naive scans failed, and the format (72×80, 6bpp, 64-colour palette) is only a hypothesis carried over from a sibling engine, not confirmed against this ROM. It needs a Ghidra xref-trace from the card-ID table. See [`docs/MEMORY_FINDINGS.md`](docs/MEMORY_FINDINGS.md).
     - **Memory/space is the real risk.** This ROM is the full 32 MB with no free padding (the same wall we hit placing the opponent-turn patch). Higher-quality art only fits if each card re-encodes to the *same or smaller* byte size; anything bigger needs relocation and pointer fix-ups, which is a lot more work.
     - **The crop differs per card era.** WC06 shows illustration-only art; our source scans are full cards, and the illustration rectangle varies by frame generation, so a plain downscale won't line up.
   - So: doable, worth doing later, but a real project of its own — not abandoned for being impossible.

See the [`ROADMAP.md`](ROADMAP.md) for the current status of both project goals and the concrete next step for each.

## Tools Used

- **[mGBA](https://mgba.io/)**: Main emulator used for live debugging via its integrated GDB server.
- **[Ghidra](https://ghidra-sre.org/)**: Used for static analysis and ROM disassembly (ARM/Thumb architecture).
- **[Python](https://www.python.org/)**: Scripts for image processing, ROM manipulation, and debugging automation.

## The patch

Objective 2 (navigate during the opponent's turn) is **done and shipped** as a
ROM patch: [`patch/oppnav.ips`](patch/oppnav.ips). Apply it to a clean
`trm-yum6.gba`, then press **Select** on the CPU's turn to browse the field.
See **[`docs/PATCH_GUIDE.md`](docs/PATCH_GUIDE.md)** (apply / play / rebuild /
test / internals) and the patch [quickstart](patch/README.md). For putting the
patched ROM on an Android/iOS phone, see the
[phone install guide](.workspace/output/README.md). Build:
`python3 tools/build_patch.py`. Tests: `python3 tests/test_patch.py`.

## Documentation

Write-ups, findings, and working techniques are stored in the `docs/` directory. **Read these before re-deriving something that may already be solved**:

- [`PATCH_GUIDE.md`](docs/PATCH_GUIDE.md) — how to apply, use, rebuild and test the opponent-turn patch; and how it works.
- [`MEMORY_FINDINGS.md`](docs/MEMORY_FINDINGS.md) — confirmed ROM/RAM facts: offsets, addresses, the turn-flag candidate, what's still unconfirmed.
- [`OPPONENT_TURN_NAVIGATION.md`](docs/OPPONENT_TURN_NAVIGATION.md) — how the duel loop gates the field cursor, the full address map, the shipped patch, and the live validation.
- [`LUA_AUTOMATION.md`](docs/LUA_AUTOMATION.md) — how the live mGBA automation harness works (Lua console scripting, macOS Accessibility, screenshotting) and its gotchas.
- [`GHIDRA_WORKFLOW.md`](docs/GHIDRA_WORKFLOW.md) — static analysis: Ghidra setup/gotchas, and the lighter capstone path (`tools/disasm_thumb.py`) that is usually enough.

## Directory Structure

- `.workspace/`: Temporary files, working ROMs, and reference repositories (e.g., decompilations). *Not versioned*.
- `tools/`: Utility scripts created during the reverse engineering process (incl. `build_patch.py`).
- `tests/`: Automated tests for the patch builder.
- `patch/`: The shipped IPS patch and its quickstart.
- `docs/`: Technical documentation and write-ups.

---

*To see the chronological progress and the journey we have followed, please refer to [`JOURNEY.md`](JOURNEY.md), our short append-only log detailing findings session by session.*
