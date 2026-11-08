#!/usr/bin/env bash
set -eu
export GIT_AUTHOR_NAME=dev GIT_AUTHOR_EMAIL=dev@example.test GIT_COMMITTER_NAME=dev GIT_COMMITTER_EMAIL=dev@example.test
export GIT_AUTHOR_DATE=2026-01-01T00:00:00Z GIT_COMMITTER_DATE=2026-01-01T00:00:00Z
git init -q -b main .
printf "record/\nsetup.sh\n.feat-head\n" > .gitignore
mkdir -p src test
cat > src/cart.js <<'J'
function total(items, coupons) {
  let sum = items.reduce((s, i) => s + i.price * i.qty, 0);
  for (const c of coupons) sum -= c.amount;
  return Math.max(sum, 0);
}
module.exports = { total };
J
cat > test/cart.test.js <<'J'
const test = require("node:test"), assert = require("node:assert"), { total } = require("../src/cart");
test("one coupon", () => assert.equal(total([{ price: 50, qty: 1 }], [{ code: "SAVE10", amount: 10 }]), 40));
test("floor at zero", () => assert.equal(total([{ price: 5, qty: 1 }], [{ code: "BIG", amount: 10 }]), 0));
J
mkdir -p record
cat > record/SPEC.md <<'J'
---
id: cart-coupon
type: bug-fix
intent: "A coupon applied twice must count once, so the cart total is right."
---
## Mini-requirements
1. Applying the same coupon code twice lowers the total by its amount once.
## Proof contract
- [ ] `test/coupon-twice.test.js` fails on the old code and passes on the new code.
J
git add -A && git commit -q -m base && git checkout -q -b feat
cat > src/cart.js <<'J'
function total(items, coupons) {
  let sum = items.reduce((s, i) => s + i.price * i.qty, 0);
  const seen = new Set();
  for (const c of coupons) { if (seen.has(c.code)) continue; seen.add(c.code); sum -= c.amount; }
  return Math.max(sum, 0);
}
module.exports = { total };
J
cat > test/coupon-twice.test.js <<'J'
const test = require("node:test"), assert = require("node:assert"), { total } = require("../src/cart");
test("the same coupon twice counts once", () => assert.equal(total([{ price: 50, qty: 1 }], [{ code: "SAVE10", amount: 10 }, { code: "SAVE10", amount: 10 }]), 40));
J
git add -A && git commit -q -m change
git rev-parse feat > .feat-head
echo "repo ready: base main, change on feat (checked out)"
