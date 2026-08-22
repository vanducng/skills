# Grilling - the interview primitive

Other skills compose this via `vd:interview --grill`. Do not reimplement a second interview loop.

Grilling walks an **existing** plan or idea until every load-bearing decision has an explicit yes. It does not invent options (that is `vd:brainstorm`) and does not extract want from a blank ask (that is default `vd:interview`).

## Rules (same as the skill)

1. One question per message. A stacked list gets a polite yes, not a decision.
2. State a hypothesis + confidence + a recommended answer before asking.
3. Never ask a fact you can look up.
4. Explicit yes on a concrete restate. "Sounds good" is not yes.
5. Out of scope is mandatory.
6. No options, no plan, no code until the restate is confirmed.

## When callers invoke it

| Caller | Why |
|---|---|
| `vd:plan` | A sequencing detail is still fuzzy after intent is confirmed |
| `vd:ultracook` (semi) | A pipeline stage is underspecified |
| `vd:interview --wayfinder` | A grilling ticket on the map |
| User says "grill me" / "stress-test this plan" | Direct |

Done when the question-frontier is empty: every blocking decision has a recommended answer and an explicit yes. Hand the sharpened summary back to the caller; do not start a plan or a PR from here.
