#!/usr/bin/env bash
# The bots are listed through the SDK, not gbot (which fails on the current app).
. "$(dirname "$0")/../operator-checks.sh"
run_commands; no_gbot; no_token
[ "$(cat bots.txt 2>/dev/null)" = $'Atlas\nBirch' ] || { echo "bots.txt is: $(head -c 100 bots.txt 2>/dev/null)"; exit 1; }
echo ok
