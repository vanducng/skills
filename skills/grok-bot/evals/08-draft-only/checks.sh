#!/usr/bin/env bash
# A draft for the operator to send himself: nothing is sent.
. "$(dirname "$0")/../operator-checks.sh"
[ -s draft.md ] || { echo "no draft.md"; exit 1; }
if [ -s commands.sh ]; then bash commands.sh > commands.out 2>&1 || true; fi
[ -z "$(calls sendMessage)" ] || { echo "it sent the draft"; exit 1; }
no_gbot
echo ok
