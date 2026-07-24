# The 12 Risk Dimensions

Walk each one against the target. The prompt for each: *"What input or condition in this category makes the target misbehave?"*

| # | Dimension | Probe for |
|---|---|---|
| 1 | **Happy path** | The intended flow with valid, typical inputs - the baseline that must work. |
| 2 | **Boundary values** | Min/max, off-by-one, empty vs one vs many, first/last, overflow/underflow, zero, negative. |
| 3 | **Null / empty / missing** | null, undefined, empty string/array/object, absent optional field, missing config. |
| 4 | **Type / format errors** | Wrong type, malformed JSON/date/number, unexpected encoding, injection payloads in string fields. |
| 5 | **Concurrency / races** | Two writers, read-during-write, double-submit, lost update, deadlock, non-atomic check-then-act. |
| 6 | **Ordering / idempotency** | Out-of-order events, replayed/duplicate requests, retry without idempotency key, reordered async. |
| 7 | **Scale / volume** | Large payloads, long lists, pagination edges, N+1, memory/timeout under load, rate limits. |
| 8 | **Authz / permissions** | Unauthenticated, wrong role, expired token, privilege escalation, cross-tenant access, IDOR. |
| 9 | **Network / IO failure** | Timeout, partial response, 5xx from dependency, connection drop mid-stream, disk full, DNS failure. |
| 10 | **State / lifecycle** | Uninitialized, already-closed, double-init, transition from an illegal state, stale cache, resource leak. |
| 11 | **Time / timezone** | DST transition, leap year/second, clock skew, expiry exactly now, TZ-naive vs aware, epoch edges. |
| 12 | **Localization / encoding** | Unicode, RTL, emoji, very long names, locale-specific number/date formats, normalization (NFC/NFD). |

**Tips:** not every dimension yields cases for every target - note "N/A: <reason>" rather than padding. Cross-dimension combos (e.g. concurrency × authz) are often the highest-severity finds - flag them explicitly.
