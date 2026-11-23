#!/usr/bin/env bash
. "$(dirname "$0")/../bot-checks.sh"

reply_ok
[ -z "$(computer_calls)" ] || { echo "used a computer while the connector was down: $(computer_calls | head -1)"; exit 1; }
grep -Eiq '(connector|team).{0,40}(not answering|down|fail|unavailable|not respond|timed? ?out|unreachable)' reply.md || { echo "the reply does not say the connector is down"; exit 1; }
echo ok
