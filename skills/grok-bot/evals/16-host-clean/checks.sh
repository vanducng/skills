#!/usr/bin/env bash
. "$(dirname "$0")/../bot-checks.sh"

reply_ok
c=$(computer_calls | head -1)
echo "$c" | grep -q '"machine": *"build-1"' && echo "$c" | grep -Eq '"command": *"(df|du)\b' || { echo "no read-only disk command on build-1: ${c:-none}"; exit 1; }
echo ok
