#!/usr/bin/env bash
# The thin record gets numbered, observable mini-requirements and a concrete contract; nothing else is written.
set -u
s=.workbench/cart-coupon/SPEC.md
! grep -qi TODO "$s" || { echo "TODO left in $s"; exit 1; }
[ "$(grep -Ec '^[0-9]+\. .+' "$s")" -ge 2 ] || { echo "fewer than 2 numbered mini-requirements"; exit 1; }
grep -Eiq '^[0-9]+\. .*(twice|same code|once)' "$s" || { echo "no requirement for the repeated coupon"; exit 1; }
grep -Eiq '^[0-9]+\. .*(zero|negative|below)' "$s" || { echo "no requirement for the floor at zero"; exit 1; }
grep -Eq '^- \[ \] .*`[^`]+`' "$s" || { echo "no concrete contract line naming a test or command"; exit 1; }
extra=$(diff -rq . "$EVAL_ORIG" | grep -v "cart-coupon")
[ -z "$extra" ] || { echo "files written outside the record: $extra"; exit 1; }
echo ok
