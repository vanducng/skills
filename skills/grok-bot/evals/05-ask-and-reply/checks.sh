#!/usr/bin/env bash
# The send carries a messageId (a send without one never reaches the chat), and the reply is read back.
. "$(dirname "$0")/../operator-checks.sh"
run_commands; no_gbot; no_token
sends=$(calls sendMessage)
[ -n "$sends" ] || { echo "nothing was sent"; exit 1; }
! echo "$sends" | grep -q '"messageId":null' || { echo "a send without a messageId"; exit 1; }
grep -qx 'FAKE_REPLY to: What is waiting on me?' reply.txt 2>/dev/null || { echo "reply.txt is not the reply: $(head -c 120 reply.txt 2>/dev/null)"; exit 1; }
echo ok
