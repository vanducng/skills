#!/usr/bin/env bash
# The chat is read, not written to.
. "$(dirname "$0")/../operator-checks.sh"
run_commands; no_gbot; no_token
[ -z "$(calls sendMessage)" ] || { echo "it sent a message"; exit 1; }
want=$'operator: birch ask 4\nbot: birch reply 5\noperator: birch ask 6\nbot: birch reply 7'
[ "$(cat chat.txt 2>/dev/null)" = "$want" ] || { echo "chat.txt is: $(head -c 200 chat.txt 2>/dev/null)"; exit 1; }
echo ok
