#!/bin/sh
# A dashboard ask starts with the question sheet and the questions only the asker can answer, never with a chart.
. "$(dirname "$0")/../common.sh"
built=$(new_files | grep -Eiv '\.(md|csv|txt|sql)$')
[ -z "$built" ] || { echo "built something before the question sheet was answered: $built"; exit 1; }
row_with audience decision metric grain refresh || { echo "no question sheet (a table with audience, decision, metric, grain and refresh columns)"; exit 1; }
grep -q '?' "$EVAL_OUTPUT" && grep -Eiq 'audience|who (will |is going to )?(use|read|look|see)' "$EVAL_OUTPUT" && grep -Eiq 'decision|decide|do differently|act on' "$EVAL_OUTPUT" \
  || { echo "the reply does not ask for the audience and the decisions"; exit 1; }
echo ok
