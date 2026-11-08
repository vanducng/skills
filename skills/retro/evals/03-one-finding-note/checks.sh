#!/usr/bin/env bash
# One finding seen once is a note: one line in the record PROGRESS.md and nothing else - no rule, no check, no proposal.
set -u
cmp -s AGENTS.md "$EVAL_ORIG/AGENTS.md" || { echo "AGENTS.md was edited for a single finding"; exit 1; }
extra=$(diff -rq . "$EVAL_ORIG" | grep -vE '(rec-a/)?(PROGRESS|progress)\.md|reports|journal|Only in \.: reports|Only in \./rec-a: reports' || true)
[ -z "$extra" ] || { echo "files written beyond the record's notes: $extra"; exit 1; }
grep -Eiq '^\|.*\|' reports/retro.md rec-a/reports/retro.md 2>/dev/null && { echo 'a rule-table row was proposed for one finding'; exit 1; } || true
echo ok
