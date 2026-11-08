#!/usr/bin/env bash
# A bug fix is proved by a check that fails on the old code and passes on the new; the code is left alone.
. "$(dirname "$0")/../common-checks.sh"
type_is 'bug[- ]?fix'
grep -Eiq '^- \[ \] .*fail.*old.*pass.*new' "$spec" || { echo "no fails-on-old, passes-on-new contract line"; exit 1; }
diff -q src/cart.js "$EVAL_ORIG/src/cart.js" >/dev/null || { echo "the code was changed"; exit 1; }
echo ok
