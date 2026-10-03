# Technical Architecture

## Overview

This document outlines the technical approach for the two main objectives of the Yu-Gi-Oh! Ultimate Masters GBA Romhack.

## 1. Card Image Modification

### ROM Structure
The game engine (Konami GBA lineage, similar to *Eternal Duelist Soul*) stores card art in a contiguous block within the ROM.
- **Resolution**: 72x80 pixels.
- **Color Depth**: 6bpp indexed (64 colors).
- **Palette Data**: Stored in BGR555 format.
- **Target Images**: High-quality 268x391 full-art JPGs.

### Pipeline
1. **Offset Identification**: Locate the exact ROM offsets for the card graphics and palette tables. (Based on community documentation, card text tables are located around `0x015BB594`).
2. **Image Processing (Python)**:
   - Downscale the source JPGs to 72x80.
   - Quantize the images to 64 colors to fit within the GBA's VRAM limits.
3. **ROM Injection**: Serialize the processed images and palettes into the proprietary binary format and write them back into the ROM.

## 2. Opponent Turn Navigation

### Core Challenge
By default, the game restricts cursor movement when the active turn flag belongs to the CPU/Opponent. This logic lives within the main duel loop (`duel_main` equivalent).

### Reverse Engineering Pipeline
1. **Live Memory Tracking**: Use **mGBA's GDB remote stub** to read/write memory dynamically while a duel is running. Track the specific RAM address that toggles when the turn switches from Player to CPU.
2. **Instruction Tracing**: Locate the ARM/Thumb assembly routine that checks this turn state and skips the input polling function.
3. **Patching**: Modify the conditional branch instruction (e.g., `BNE`, `BEQ`) via an IPS/BPS patch or direct hex edit to allow field navigation state transitions even when it is not the player's turn, ensuring that the AI's internal state remains unaffected.
