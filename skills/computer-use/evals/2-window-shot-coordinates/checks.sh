#!/usr/bin/env bash
set -u
o=$(cat "$EVAL_OUTPUT")
grep -qE 'mouse-click' <<<"$o" || { echo "no mouse-click"; exit 1; }
grep -qE -- '--headed' <<<"$o" || { echo "no --headed"; exit 1; }
grep -qE -- 'screenshot[^`]*--screen' <<<"$o" || { echo "clicks from the window shot (shadow margin) instead of a display shot"; exit 1; }
! grep -qE -- '--xy[ =]882,570' <<<"$o" || { echo "naive window-origin point"; exit 1; }
