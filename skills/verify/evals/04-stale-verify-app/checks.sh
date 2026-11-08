#!/usr/bin/env bash
# Both staleness reasons are reported (the e2e script is gone; the stamp is two months old), and nothing is rewritten.
set -u
grep -qi 'e2e' "$EVAL_OUTPUT" || { echo "the reply does not name the missing e2e script"; exit 1; }
grep -Eiq '2026-09-01|[0-9]+ days|two months|stale|old' "$EVAL_OUTPUT" || { echo "the reply does not flag the old verified stamp"; exit 1; }
diff -r . "$EVAL_ORIG" >/dev/null || { echo "files changed: $(diff -rq . "$EVAL_ORIG" | head -2)"; exit 1; }
echo ok
