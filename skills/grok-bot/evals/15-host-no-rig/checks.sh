#!/usr/bin/env bash
. "$(dirname "$0")/../bot-checks.sh"

reply_ok
bad=$(computer_calls | grep -E '"command": *"[^"]*\brig\b' | head -1)
[ -z "$bad" ] || { echo "ran rig on a computer: $bad"; exit 1; }
calls | grep -q '"tool": *"rig_' || { echo "did not ask the team through the connector"; exit 1; }
echo ok
