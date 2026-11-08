---
depends_on: []
id: price-cache
type: feature
intent: "Product pages stop timing out when the pricing API is slow."
---
# Price lookups

Product pages call the external pricing API on every view. It is slow (p95 2.4 s) and rate-limited to 50 requests a second; prices change at most once an hour and a stale price for up to an hour is acceptable to the business. We run one Node service behind a load balancer with three instances and a managed Redis already used for sessions.

## Mini-requirements

1. TODO

## Proof contract

- [ ] TODO
