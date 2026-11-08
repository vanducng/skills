---
depends_on: []
id: cart-coupon
type: bug-fix
intent: "A coupon applied twice must count once, so the cart total is right."
---
# Cart coupon counted twice

## Mini-requirements

1. Applying the same coupon code twice lowers the total by its amount once.
2. Two different coupon codes still both apply.

## Proof contract

- [ ] `test/cart.test.js` applies one coupon twice: it fails on the old code and passes on the new code (requirement 1).
- [ ] `test/cart.test.js` applies two different coupons and both discounts land (requirement 2).
- [ ] The failing case stays as a regression test.
- [ ] Two-way door, blast radius: cart totals only; undo: revert the commit.

## Out of scope

Coupon expiry, stacking limits and any UI change.
