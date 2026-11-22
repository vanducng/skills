#!/usr/bin/env bash
# An own-code surprise is fixed in the code, then its comment goes; narration and task references go too.
f=src/pricing.js
node --test >/dev/null 2>&1 || { echo "tests fail after the change"; exit 1; }
diff -r "$EVAL_ORIG/test" test >/dev/null || { echo "test/ was changed"; exit 1; }
grep -qi "stale" "$f" && { echo "the stale-cache comment is still there"; exit 1; }
grep -qi "set the rate" "$f" && { echo "the narrating comment is still there"; exit 1; }
grep -q "PRICE-412" "$f" && { echo "the task reference is still in the code"; exit 1; }
node -e '
const p = require("./src/pricing");
p.setRate(1); p.clearCache && p.clearCache(); p.price(100);
p.setRate(3);
if (p.price(100) !== 300) { console.log("setRate still leaves stale prices: the comment was deleted but the trap stays"); process.exit(1); }
' || exit 1
echo ok
