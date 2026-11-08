#!/usr/bin/env bash
# The record exists in the bench shape, is authored, and holds one well-formed QA artifact.
set -u
d=.workbench/uploader-retry
for f in SPEC.md PROGRESS.md PROOF.md; do [ -f "$d/$f" ] || { echo "missing $d/$f"; exit 1; }; done
[ -d "$d/reports" ] || { echo "missing $d/reports"; exit 1; }
[ ! -e .workbench/features ] || { echo "old features/ layout created"; exit 1; }
grep -qi "TODO" "$d/SPEC.md" && { echo "SPEC.md still has TODO lines"; exit 1; }
grep -q "^intent: ..*" "$d/SPEC.md" || { echo "no intent"; exit 1; }
grep -q '^1\. .\+' "$d/SPEC.md" || { echo "no numbered mini-requirement"; exit 1; }
grep -q '^- \[ \] .\+' "$d/SPEC.md" || { echo "no checkbox proof contract line"; exit 1; }
f=$(ls "$d"/proof/*.md 2>/dev/null | head -1)
[ -n "$f" ] || { echo "no proof artifact"; exit 1; }
grep -q '^candidate_sha: abc1234$' "$f" && grep -q '^artifact_type: qa$' "$f" && grep -q '^verdict: PASS$' "$f" && grep -q '^slice: ' "$f" && grep -q '^money_evidence: .*uploader test exits 0' "$f" || { echo "bad C1 header in $f"; exit 1; }
grep -q "$(basename "$f")" "$d/PROOF.md" || { echo "PROOF.md does not list $f"; exit 1; }
grep -q "uploader-retry" "$EVAL_OUTPUT" || { echo "reply does not name the folder"; exit 1; }
echo ok
