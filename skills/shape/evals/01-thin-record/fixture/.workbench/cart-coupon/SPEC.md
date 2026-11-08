---
depends_on: []
id: cart-coupon
type: bug-fix
intent: "A coupon applied twice must count once, so the cart total is right."
---
# Cart coupon counted twice

A customer applied SAVE10 twice and got $20 off a $50 cart. Coupons have a `code` and an `amount`; the same code may only count once, different codes still stack, and the total never goes below zero.

## Mini-requirements

1. TODO

## Proof contract

- [ ] TODO
