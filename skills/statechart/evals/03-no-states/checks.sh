#!/usr/bin/env bash
# A pure function has no states: decline the chart, say why, model nothing, and leave the code alone.
set -u
diff -q src/price.js "$EVAL_ORIG/src/price.js" >/dev/null || { echo "the code was changed"; exit 1; }
[ -z "$(find . -name '*.tla' -o -name 'chart.mmd' | head -1)" ] || { echo "a model or chart was written"; exit 1; }
! grep -q 'stateDiagram' "$EVAL_OUTPUT" || { echo "the reply draws a state diagram"; exit 1; }
grep -Eiq "no state|stateless|not a state machine|pure function|does not (keep|hold|store|have) (any )?state|has no (memory|states)" "$EVAL_OUTPUT" \
  || { echo "the reply does not say the code has no states"; exit 1; }
echo ok
