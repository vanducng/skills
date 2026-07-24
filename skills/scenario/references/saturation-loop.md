# Saturation Loop

`--saturation` keeps generating until the dimensions stop yielding new cases - for when coverage must be exhaustive, not just a first pass.

## Round protocol

```
seen = {}            # set of scenario keys (dimension + normalized condition)
dry  = 0             # consecutive zero-new rounds
round = 0
while dry < 2 and round < Iterations:    # Iterations default 5
    round += 1
    fresh = generate_scenarios()         # full 12-dimension pass
    new   = [s for s in fresh if key(s) not in seen]
    if not new:
        dry += 1
        continue
    dry = 0
    seen |= {key(s) for s in new}
    log(f"round {round}: +{len(new)} new (total {len(seen)})")
```

- **Dedupe key** = dimension + normalized condition (lowercase, whitespace-collapsed) so paraphrases of the same case don't re-count.
- **Completeness critic** - each round after the first, before generating, ask: *"Which dimension is thinnest? Which cross-dimension combo is unexplored?"* Steer the next round there instead of re-walking evenly.

## Termination (always bounded)

| Condition | Result |
|---|---|
| 2 consecutive rounds add 0 new scenarios | converged → stop |
| `round == Iterations` | cap reached → stop, **log that more may exist** |

Never run unbounded. If the cap is hit with the last round still adding cases, say so explicitly in the report's coverage line so the user knows enumeration was truncated, not complete.

## Reporting

Final coverage line includes round count and whether it converged or hit the cap:

```
Dimensions covered: 12/12 · scenarios: 37 · rounds: 4 (converged)
```
