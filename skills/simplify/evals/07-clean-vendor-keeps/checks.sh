#!/usr/bin/env bash
# License header, a one-line public API doc and a vendor constraint with its link all stay: nothing changes.
diff -r "$EVAL_ORIG" . -x .git >/dev/null || { echo "the clean file was changed:"; diff -r "$EVAL_ORIG" . -x .git | head -5; exit 1; }
echo ok
