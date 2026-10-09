#!/bin/bash
# Sends Lua code to mGBA's Scripting console REPL via Accessibility (System
# Events) and clicks Run. Retries a few times since the window list query is
# occasionally flaky (transient, especially if something else on the Mac
# steals focus/Spaces at the same instant).
CODE="$1"
osascript -e 'tell application "mGBA" to activate' > /dev/null 2>&1
for attempt in 1 2 3 4 5; do
  OUT=$(osascript << EOF 2>&1
tell application "System Events"
    tell process "mGBA"
        set value of text field 1 of splitter group 1 of window "Scripting" to "$CODE"
        click button "Run" of splitter group 1 of window "Scripting"
    end tell
end tell
EOF
)
  if [[ "$OUT" != *"error"* ]]; then
    exit 0
  fi
  sleep 0.2
done
echo "run_lua.sh FAILED after retries: $OUT" >&2
exit 1
