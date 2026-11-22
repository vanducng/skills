#!/usr/bin/env bash
# A draft that already reads right in Grok Bot is sent as it is.
set -u
cmp -s message.md "$EVAL_ORIG/message.md" || { echo "a good draft was rewritten"; exit 1; }
echo ok
