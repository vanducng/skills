#!/usr/bin/env bash
# No trigger (not closing, nothing escaped, nothing repeated): retro writes nothing.
set -u
diff -r . "$EVAL_ORIG" >/dev/null || { echo "files changed with no retro trigger: $(diff -rq . "$EVAL_ORIG" | head -2)"; exit 1; }
echo ok
