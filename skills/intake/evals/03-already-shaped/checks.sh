#!/usr/bin/env bash
# The ask already has a shaped record: no second record, and the SPEC is untouched.
set -u
n=$(find .workbench -name SPEC.md | wc -l | tr -d ' ')
[ "$n" = 1 ] || { echo "a second record was created ($n SPEC.md files)"; exit 1; }
cmp -s .workbench/cart-coupon/SPEC.md "$EVAL_ORIG/.workbench/cart-coupon/SPEC.md" || { echo "the shaped SPEC.md was rewritten"; exit 1; }
diff -q src/cart.js "$EVAL_ORIG/src/cart.js" >/dev/null || { echo "the code was changed"; exit 1; }
echo ok
