#!/usr/bin/env bash
. "$(dirname "$0")/../bot-checks.sh"

reply_ok; headline_first; tables_narrow
grep -Eq '^\|[[:space:]]*Rig[[:space:]]*\|' reply.md || { echo "no Rigs table (| Rig | State | Needs you |)"; exit 1; }
grep -Eq '^\|[[:space:]]*Where[[:space:]]*\|' reply.md || { echo "no Inbox table (| Where | From · about | Owed since | Link |)"; exit 1; }
order=$(grep -Eo '^\|[[:space:]]*(orchard|billing|intake|reports)' reply.md | tr -d '| ' | tr '\n' ' ')
[ "$order" = "orchard billing intake reports " ] || { echo "rigs not worst first: $order"; exit 1; }
echo ok
