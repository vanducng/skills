#!/usr/bin/env bash
# Nothing to simplify and the one comment is an outside constraint: the file stays as it was.
diff -r "$EVAL_ORIG" . -x .git >/dev/null || { echo "the clean file was changed:"; diff -r "$EVAL_ORIG" . -x .git | head -5; exit 1; }
echo ok
