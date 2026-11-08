#!/usr/bin/env bash
# --grill asks one question (with a recommended answer) and writes nothing yet.
set -u
diff -r . "$EVAL_ORIG" >/dev/null || { echo "files changed during grilling"; exit 1; }
# The one question is the **Ask:** line; no other line asks anything (headings that restate it are titles).
a=$(grep -c '^\*\*Ask:\*\*' "$EVAL_OUTPUT")
[ "$a" -eq 1 ] || { echo "want one **Ask:** line, found $a"; exit 1; }
[ "$(grep '^\*\*Ask:\*\*' "$EVAL_OUTPUT" | tr -cd '?' | wc -c | tr -d ' ')" -eq 1 ] || { echo "the Ask line holds more than one question"; exit 1; }
q=$(grep -v '^\*\*Ask:\*\*' "$EVAL_OUTPUT" | grep -Ev '^(#|\*\*[^*]+\*\*[[:space:]]*$)' | grep -c '?')
[ "$q" -eq 0 ] || { echo "$q other line(s) ask a question"; exit 1; }
grep -Eiq 'recommend|my guess|i.d suggest|hypothes' "$EVAL_OUTPUT" || { echo "no stated recommendation or hypothesis"; exit 1; }
echo ok
