#!/usr/bin/env bash
# The thin record gets numbered, observable mini-requirements, a concrete contract with its door type and undo step,
# and an out-of-scope line; nothing else is written.
set -u
s=.workbench/cart-coupon/SPEC.md
trap 'rc=$?; [ $rc -ne 0 ] && [ -f "$s" ] && { echo "--- $s:"; cat "$s"; }; exit $rc' EXIT
! grep -qi TODO "$s" || { echo "TODO left in $s"; exit 1; }
[ "$(grep -Ec '^[0-9]+\. .+' "$s")" -ge 2 ] || { echo "fewer than 2 numbered mini-requirements"; exit 1; }
grep -Eiq '^[0-9]+\. .*(twice|same code|once)' "$s" || { echo "no requirement for the repeated coupon"; exit 1; }
grep -Eiq '^[0-9]+\. .*(zero|negative|below)' "$s" || { echo "no requirement for the floor at zero"; exit 1; }
grep -Eq '^- \[ \] .*`[^`]+`' "$s" || { echo "no concrete contract line naming a test or command"; exit 1; }
grep -Eiq "(one|two)[- ]way|reversible" "$s" || { echo "no door type (one-way or two-way) in the contract"; exit 1; }
grep -Eiq "undo|revert|roll ?back" "$s" || { echo "no undo step"; exit 1; }
grep -Eiq "out of scope" "$s" || { echo "no out-of-scope line"; exit 1; }
extra=$(diff -rq . "$EVAL_ORIG" | grep -v "cart-coupon")
[ -z "$extra" ] || { echo "files written outside the record: $extra"; exit 1; }
echo ok
