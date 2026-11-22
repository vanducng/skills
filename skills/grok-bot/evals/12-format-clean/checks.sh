#!/usr/bin/env bash
. "$(dirname "$0")/../bot-checks.sh"

reply_ok; tables_narrow
[ ! -s card.json ] || { echo "a question card with nothing to decide"; exit 1; }
w=$(wc -w < reply.md | tr -d ' '); [ "$w" -le 120 ] || { echo "reply is $w words for an all-clear"; exit 1; }
echo ok
