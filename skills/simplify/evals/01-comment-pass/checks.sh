#!/usr/bin/env bash
# The comment pass: the two restating comments and the stale "in cents" header go, the outside-constraint comment stays.
f=src/cart.js
node --test >/dev/null 2>&1 || { echo "tests fail after the change"; exit 1; }
diff -r "$EVAL_ORIG/test" test >/dev/null || { echo "test/ was changed"; exit 1; }
grep -qi "in cents" "$f" && { echo "the stale 'in cents' comment is still there"; exit 1; }
grep -qi "loop over the items" "$f" && { echo "the restating 'loop over the items' comment is still there"; exit 1; }
grep -qi "price times the quantity" "$f" && { echo "the restating 'price times the quantity' comment is still there"; exit 1; }
grep -qi "2 decimals" "$f" || { echo "the payment-API comment (an outside constraint) was removed"; exit 1; }
# The reply lists each comment on its own line with what was done to it and why.
listed() { # TERM ACTION: a reply line names the comment, the action and a reason
  grep -iF -- "$1" "$EVAL_OUTPUT" | grep -iE "$2" \
    | grep -qiE 'because|since|restat|stale|wrong|drift|outdated|constraint|outside|can.t show|cannot show|obvious|duplicat'
}
listed "in cents" 'rewr|fix|correct|updat|replac|remov|delet|kill|drop' || { echo "the reply does not list the 'in cents' comment with its action and reason"; exit 1; }
listed "loop over the items" 'remov|delet|kill|drop' || { echo "the reply does not list 'loop over the items' as removed, with a reason"; exit 1; }
listed "price times the quantity" 'remov|delet|kill|drop' || { echo "the reply does not list 'price times the quantity' as removed, with a reason"; exit 1; }
listed "payment API" '\bkeep|\bkept' || { echo "the reply does not list the payment-API comment as kept, with a reason"; exit 1; }
echo ok
