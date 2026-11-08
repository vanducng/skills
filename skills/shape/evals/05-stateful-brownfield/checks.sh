#!/usr/bin/env bash
# A record with the statechart lens on existing code gets a today chart (from the code) and an intended chart, both
# from TLC runs; the stated rule becomes an invariant requirement with a contract test that fails on today's code.
set -u
r=.workbench/upload-cancel; s=$r/SPEC.md
trap 'rc=$?; [ $rc -ne 0 ] && [ -f "$s" ] && { echo "--- $s:"; cat "$s"; }; exit $rc' EXIT
for which in today intended; do
  rep=$(grep -rlE '^TLC reached [0-9]+ states' --include=report.md "$r/reports/statechart/$which" 2>/dev/null | head -1)
  [ -n "$rep" ] && [ -f "$(dirname "$rep")/chart.mmd" ] || { echo "no $which chart from a TLC run under $r/reports/statechart/$which"; exit 1; }
done
! grep -qi TODO "$s" || { echo "TODO left in $s"; exit 1; }
sed -n '/^## States/,/^## /p' "$s" | grep -q 'reports/statechart/today' && sed -n '/^## States/,/^## /p' "$s" | grep -q 'reports/statechart/intended' \
  || { echo "no ## States section naming both charts"; exit 1; }
grep -Eiq '^[0-9]+\. .*cancel.*\(invariant\)' "$s" || { echo "the cancel rule is not a numbered (invariant) requirement"; exit 1; }
grep -Eiq '^- \[ \] .*cancel.*fail.*(today|old|current).*pass' "$s" || { echo "no contract test for the cancel rule that fails on today's code"; exit 1; }
diff -q src/upload.js "$EVAL_ORIG/src/upload.js" >/dev/null || { echo "the code was changed"; exit 1; }
extra=$(diff -rq . "$EVAL_ORIG" | grep -v "upload-cancel")
[ -z "$extra" ] || { echo "files written outside the record: $extra"; exit 1; }
echo ok
