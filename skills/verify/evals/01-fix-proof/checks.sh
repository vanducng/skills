#!/usr/bin/env bash
# The new check ran against the old code and failed on the bug itself, then passed on the head.
. "$(dirname "$0")/../common-checks.sh"
[ "$(j outcome)" = fixed ] || { echo "outcome is '$(j outcome)', want fixed"; exit 1; }
grep -q "coupon-twice\|same coupon twice" "record/proof/$(j parent.log)" || { echo "the parent run never ran the new check"; exit 1; }
! grep -qi "cannot find module\|could not find" "record/proof/$(j parent.log)" || { echo "the parent failed because the check was missing, not on the bug"; exit 1; }
echo ok
