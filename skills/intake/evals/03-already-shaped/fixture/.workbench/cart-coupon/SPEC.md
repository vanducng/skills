---
depends_on: []
id: cart-coupon
type: bug-fix
intent: "A coupon applied twice must count once, so the cart total is right."
---
# Cart coupon counted twice

## Mini-requirements

1. Applying the same coupon twice lowers the total by its amount once.
2. Two different coupons still both apply.

## Proof contract

- [ ] `test/cart.test.js` applies one coupon twice: it fails on the old code and passes on the new code.
- [ ] The failing case stays as a regression test.
- [ ] Two-way door, blast radius: cart totals only; undo: revert the commit.
