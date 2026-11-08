#!/usr/bin/env bash
# In a rig the notes go into the slice folder's reports/, nothing is split off to .workbench, evidence is not hand-written.
set -u
s=orgs/acme/projects/shop/missions/m/slices/02-b
[ -f "$s/reports/review.md" ] || { echo "review.md is not in $s/reports/"; exit 1; }
grep -q "no blocking issues" "$s/reports/review.md" || { echo "review.md lost its text"; exit 1; }
[ ! -e .workbench ] && [ -z "$(find . -name .workbench -not -path './.git/*' 2>/dev/null)" ] || { echo "a .workbench folder was created in a rig"; exit 1; }
[ ! -e "$s/proof" ] && [ ! -e "$s/PROOF.md" ] || { echo "proof written by hand in a slice folder"; exit 1; }
[ ! -e orgs/acme/projects/shop/missions/m/slices/01-a/reports ] || { echo "wrote into the wrong slice"; exit 1; }
grep -q "rig proof" "$EVAL_OUTPUT" && grep -q " add " "$EVAL_OUTPUT" && grep -q "02-b" "$EVAL_OUTPUT" || { echo "reply lacks the rig proof add command for 02-b"; exit 1; }
t=$(grep -o -- '--artifact-type [^ ]*' "$EVAL_OUTPUT" | head -1 | cut -d' ' -f2)
[ -z "$t" ] || echo "$t" | grep -qxE 'guard|qa|rev1-r1|rev1-r2|adjudication' || { echo "invalid --artifact-type $t"; exit 1; }
echo ok
