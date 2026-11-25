#!/bin/sh
# A question about Studio needs an answer, not a browser run.
. "$(dirname "$0")/../common.sh"
[ ! -s "$LOG" ] || fail "opened the browser for a question"
[ -s "$EVAL_OUTPUT" ] || fail "no answer"
echo ok
