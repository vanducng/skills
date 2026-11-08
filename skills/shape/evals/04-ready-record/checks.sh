#!/usr/bin/env bash
# A record that is already shaped is left alone.
set -u
diff -r . "$EVAL_ORIG" >/dev/null || { echo "a ready record was changed: $(diff -rq . "$EVAL_ORIG" | head -2)"; exit 1; }
echo ok
