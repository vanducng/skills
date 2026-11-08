#!/usr/bin/env bash
# Slice close leaves one retro line in the form the close check reads, naming what cost a round; verdicts untouched.
set -u
p=record/PROGRESS.md
line=$(grep -E '^\s*[-*]\s+[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}Z\b.*\bretro:\s*\S' "$p" | tail -1)
[ -n "$line" ] || { echo "no '- <YYYY-MM-DDTHH:MMZ>: retro: <text>' line in $p"; exit 1; }
echo "$line" | grep -Eiq 'empty|round|F1|test' || { echo "the retro line does not name what cost the round: $line"; exit 1; }
diff -r record/proof "$EVAL_ORIG/record/proof" >/dev/null || { echo "a verdict file was edited"; exit 1; }
cmp -s record/SPEC.md "$EVAL_ORIG/record/SPEC.md" || { echo "SPEC.md was edited"; exit 1; }
echo ok
