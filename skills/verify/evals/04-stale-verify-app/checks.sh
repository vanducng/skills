#!/usr/bin/env bash
# The upkeep gate ran and its verdict is in the reply: stale.cjs named with its exit 1, and all three causes reported
# (the e2e script is gone, the seed target was renamed to seed-db, the stamp is old). Reading the files finds the
# causes; only running the gate gives its exit. Nothing is rewritten.
set -u
grep -Eiq 'stale\.cjs' "$EVAL_OUTPUT" || { echo "the reply does not show the upkeep gate (stale.cjs) ran"; exit 1; }
grep -Eiq '(exit(s|ed)?( code| status)?:? *1\b|exit 1|returns? 1|code 1)' "$EVAL_OUTPUT" || { echo "the reply does not report the gate's exit 1"; exit 1; }
grep -Eiq 'e2e' "$EVAL_OUTPUT" || { echo "the reply does not name the missing e2e script"; exit 1; }
grep -Eiq 'seed' "$EVAL_OUTPUT" || { echo "the reply does not name the renamed seed target"; exit 1; }
grep -Eiq '2026-09-01|[0-9]+ days|over 14|old|stale stamp' "$EVAL_OUTPUT" || { echo "the reply does not flag the old verified stamp"; exit 1; }
diff -r . "$EVAL_ORIG" >/dev/null || { echo "files changed: $(diff -rq . "$EVAL_ORIG" | head -2)"; exit 1; }
echo ok
