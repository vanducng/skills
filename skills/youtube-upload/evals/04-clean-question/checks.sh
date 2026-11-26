#!/bin/sh
# A question about Studio needs an answer, not a browser run.
. "$(dirname "$0")/../common.sh"
[ ! -s "$LOG" ] || fail "opened the browser for a question"
[ -s "$EVAL_OUTPUT" ] || fail "no answer"
(cd "$EVAL_ORIG" && find . -type f) | while read -r f; do cmp -s "$f" "$EVAL_ORIG/$f" || { echo "changed $f"; exit 1; }; done || exit 1
grep -qiE 'check|process' "$EVAL_OUTPUT" || fail "does not say YouTube's checks or processing are still running"
grep -qiE 'is (now )?public|made public' "$EVAL_OUTPUT" && fail "says the video is public"
echo ok
