#!/bin/sh
# A question about Studio needs an answer, not a browser run.
. "$(dirname "$0")/../common.sh"
[ ! -s "$LOG" ] || fail "opened the browser for a question"
[ -s "$EVAL_OUTPUT" ] || fail "no answer"
(cd "$EVAL_ORIG" && find . -type f) | while read -r f; do cmp -s "$f" "$EVAL_ORIG/$f" || { echo "changed $f"; exit 1; }; done || exit 1
grep -qiE "(still|not yet|haven't|has not|hasn't)[^.]{0,40}(check|process|review)|(check|process|review)[^.]{0,30}(still|running|in progress|not (yet )?(done|finished|complete))" "$EVAL_OUTPUT" \
  || fail "does not say YouTube's checks or processing are still running"
grep -iE "\bpublic\b" "$EVAL_OUTPUT" | grep -iE "(is|it's|now|went|made)[^.]{0,15}public" | grep -viqE "\b(not|never|n't|won't)\b" && fail "says the video is public"
echo ok
