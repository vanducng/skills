#!/usr/bin/env bash
# Clean case: there is nothing to migrate, so nothing changes and the reply says so.
set -u
diff -r "$EVAL_ORIG" . >/dev/null 2>&1 || { echo "the repo changed"; exit 1; }
[ ! -e .workbench ] || { echo "a .workbench folder was created"; exit 1; }
grep -qiE "nothing to migrate|no old|no .*features|nothing to move|no .workbench" "$EVAL_OUTPUT" || { echo "reply does not say there was nothing to migrate"; exit 1; }
echo ok
