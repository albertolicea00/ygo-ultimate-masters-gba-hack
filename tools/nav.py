#!/usr/bin/env python3
"""Reusable menu-navigation driver for trm-yum6.gba via the live mGBA harness.

Shells out to the gitignored helper scripts in
`.workspace/claude_session/scripts/` (`run_lua.sh`, `press_key.sh`,
`capture_window.py`) to drive the running emulator with no manual input.
See `docs/GAME_NAVIGATION.md` for the flows these helpers encode and
`docs/LUA_AUTOMATION.md` for how the harness itself works.

CRITICAL gotcha baked in here: a d-pad press held for the harness default
(0.12s) triggers the game's key auto-repeat and moves the cursor TWO slots.
`press()` defaults to a short 0.08s hold so each press moves exactly one
slot. Keep it short for any direction key.

usage:
  python3 tools/nav.py full-duel    # boot(Continue) -> Free Duel -> Main Phase 1

Requires mGBA already running the ROM with a Scripting console open and a
Free Duel's last-used profile/deck/opponent already chosen (Free Duel jumps
straight to the coin toss). Must run on the Mac that owns the mGBA window,
with Accessibility permission granted to the terminal (see LUA_AUTOMATION.md).
"""
import os
import subprocess
import sys
import time

# Button masks for emu:setKeys / press_key.sh.
A, B, SELECT, START = 1, 2, 4, 8
RIGHT, LEFT, UP, DOWN = 16, 32, 64, 128
R, L = 256, 512

# Resolve the harness scripts by absolute path, relative to the project root
# (this file lives at <root>/tools/nav.py).
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, ".workspace", "claude_session", "scripts")
RUN_LUA = os.path.join(SCRIPTS, "run_lua.sh")
PRESS_KEY = os.path.join(SCRIPTS, "press_key.sh")
CAPTURE = os.path.join(SCRIPTS, "capture_window.py")

# Short d-pad hold: moves one cursor slot. The 0.12s default auto-repeats.
DPAD_HOLD = 0.08


def press(mask, times=1, hold=DPAD_HOLD):
    """Press a GBA button `times`, each held `hold` seconds. Default hold is
    the short one-slot d-pad value; A/B/Start confirms are unaffected by it."""
    subprocess.run([PRESS_KEY, str(mask), str(times), str(hold)], check=True)


def lua(code):
    """Send one line of Lua to the Scripting console and click Run."""
    subprocess.run([RUN_LUA, code], check=True)


def wait(s):
    """Sleep for animations / screen transitions the game needs to settle."""
    time.sleep(s)


def shot(name):
    """Screenshot the game window ('mGBA -' matches the game view, not the
    Scripting console) to <name>. Returns the path written."""
    subprocess.run([sys.executable, CAPTURE, "mGBA -", name], check=True)
    return name


# --- high-level flows (see docs/GAME_NAVIGATION.md) ------------------------

def continue_game():
    """Title screen -> Main menu via the default 'Continue' option. [VERIFIED]"""
    press(A)
    wait(1.0)


def goto_free_duel():
    """Main menu (cursor on row 0) -> select Free Duel (row 1). [VERIFIED]

    Free Duel reuses the last-used profile/deck/opponent and jumps straight
    to the coin toss."""
    press(DOWN)          # row 0 Deck Edit -> row 1 Free Duel (one slot)
    press(A)
    wait(1.0)


def enter_duel_from_free_duel():
    """Coin Toss (cursor on Heads) -> coin animation -> START DUEL banner ->
    Main Phase 1. [VERIFIED]"""
    press(A)             # accept Heads
    wait(3.0)            # coin animation (~2-3s)
    press(A)             # dismiss START DUEL banner
    wait(1.5)            # field loads


def end_turn():
    """Open the 'Select phase to enter.' menu (B on a field zone) and pick
    the rightmost option (End Phase in the observed menus), then confirm.

    [INFERRED] navigation: EP is rightmost in the menus seen so far, so press
    Right to reach it, then A. Option sets differ by phase and the discard
    prompt (7+ cards) can intercept this — screenshot to confirm EP is
    highlighted the first time. See docs/GAME_NAVIGATION.md."""
    press(B)             # open phase menu (cursor must be on a zone, not a card)
    wait(0.5)
    press(RIGHT, times=2)  # walk to the rightmost option (EP)
    press(A)             # confirm
    wait(1.0)


def full_duel():
    """Boot(Continue) -> Free Duel -> your Main Phase 1. [VERIFIED path]"""
    continue_game()
    goto_free_duel()
    enter_duel_from_free_duel()
    print("Reached Main Phase 1 (expected).")


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "full-duel":
        full_duel()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
