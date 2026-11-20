#!/usr/bin/env bash
set -u
o=$(cat "$EVAL_OUTPUT")
grep -q 'agent-desktop' <<<"$o" || { echo "no agent-desktop"; exit 1; }
grep -qE 'agent-desktop (snapshot|find)' <<<"$o" || { echo "no observe step"; exit 1; }
grep -qE 'agent-desktop click .?(@|<|\$)' <<<"$o" || { echo "no ref click"; exit 1; }
! grep -qE 'cliclick|mouse-click|keystroke|key code' <<<"$o" || { echo "used pixel or key injection"; exit 1; }
