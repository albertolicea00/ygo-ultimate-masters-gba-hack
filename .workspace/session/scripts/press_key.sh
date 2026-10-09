#!/bin/bash
# usage: press.sh <mask> [times] [hold_s] [gap_s]
MASK=$1
TIMES=${2:-1}
HOLD=${3:-0.12}
GAP=${4:-0.12}
for i in $(seq 1 $TIMES); do
  "$(dirname "$0")/run_lua.sh" "emu:setKeys($MASK)" > /dev/null
  sleep $HOLD
  "$(dirname "$0")/run_lua.sh" "emu:setKeys(0)" > /dev/null
  sleep $GAP
done
