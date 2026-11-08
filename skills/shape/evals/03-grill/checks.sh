#!/usr/bin/env bash
# --grill asks one question (with a recommended answer) and writes nothing yet.
set -u
diff -r . "$EVAL_ORIG" >/dev/null || { echo "files changed during grilling"; exit 1; }
# A bold or heading line that restates the question ("**Q1 - ...?**") is a title, not a second question.
q=$(grep '?[*_]*[[:space:]]*$' "$EVAL_OUTPUT" | grep -Evc '^(#|\*\*[^*]+\?\*\*[[:space:]]*$)')
[ "$q" -eq 1 ] || { echo "want exactly one question, found $q question lines"; exit 1; }
grep -Eiq 'recommend|my guess|i.d suggest|hypothes' "$EVAL_OUTPUT" || { echo "no stated recommendation or hypothesis"; exit 1; }
echo ok
