#!/usr/bin/env bash
# The comment pass: the two restating comments and the stale "in cents" header go, the outside-constraint comment stays.
f=src/cart.js
node --test >/dev/null 2>&1 || { echo "tests fail after the change"; exit 1; }
diff -r "$EVAL_ORIG/test" test >/dev/null || { echo "test/ was changed"; exit 1; }
grep -qi "in cents" "$f" && { echo "the stale 'in cents' comment is still there"; exit 1; }
grep -qi "loop over the items" "$f" && { echo "the restating 'loop over the items' comment is still there"; exit 1; }
grep -qi "price times the quantity" "$f" && { echo "the restating 'price times the quantity' comment is still there"; exit 1; }
grep -qi "2 decimals" "$f" || { echo "the payment-API comment (an outside constraint) was removed"; exit 1; }
grep -qiE '\bkeep' "$EVAL_OUTPUT" || { echo "the reply lists no keep"; exit 1; }
echo ok
