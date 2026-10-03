# Workspace Directory

This directory is used for local development, temporary files, and external reference repositories. 

**Note:** With the exception of this `README.md`, the contents of this directory are ignored by Git and will not be pushed to the repository.

## Expected Structure

When fully set up, your local `.workspace` directory should look like this:

```text
.workspace/
├── README.md                 # This file (tracked by version control)
├── trm-yum6.gba              # The target ROM to be hacked (place your clean ROM here)
├── refs/                     # Reference materials and external code
│   └── eds-decomp/           # e.g., Decompilation of Eternal Duelist Soul for engine reference
└── output/                   # Compiled outputs, patched ROMs, and test builds
```

## Setup Instructions

1. Place your base ROM (`trm-yum6.gba`) directly in this folder.
2. Clone any reference repositories (such as similar game decompilations) into the `refs/` directory.
3. Generated IPS/BPS patches or modified ROMs should be exported to the `output/` directory by your tools.
