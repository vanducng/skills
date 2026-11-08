#!/usr/bin/env bash
# Today's behavior, charted from the code through a TLC run, in the reader's words; the code is left alone.
. "$(dirname "$0")/../common-checks.sh"
diff -q src/upload.js "$EVAL_ORIG/src/upload.js" >/dev/null || { echo "the code was changed"; exit 1; }
n=$(grep -cE '^ *s[0-9]+: ' "$chart")
[ "$n" -ge 4 ] || { echo "the chart has $n states; the code has at least 4"; exit 1; }
if grep -E '^ *s[0-9]+: ' "$chart" | grep -Eq '[a-z][A-Z]|_|status|attempts'; then
  echo "a state label uses a code name:"; grep -E '^ *s[0-9]+: ' "$chart"; exit 1
fi
echo ok
