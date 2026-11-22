#!/usr/bin/env bash
. "$(dirname "$0")/../bot-checks.sh"

reply_ok; headline_first; tables_narrow
lines=$(grep -cv '^[[:space:]]*$' reply.md); [ "$lines" -le 25 ] || { echo "reply is $lines lines: a long document pasted into the chat"; exit 1; }
copied=$(grep -c 'check the totals against the nightly report' reply.md); [ "$copied" -le 1 ] || { echo "the plan's steps are pasted into the chat ($copied steps)"; exit 1; }
echo ok
