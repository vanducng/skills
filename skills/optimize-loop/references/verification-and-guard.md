# Verification & Guard

Two concerns, kept separate:
- **Verify** = "did the target metric improve?" (the number)
- **Guard** = "did anything else break?" (the regression check)

## Guard pattern

1. Baseline: guard must exit 0 *before* the loop starts - establishes a clean floor.
2. Each iteration, after Verify and **before** the Keep/Discard decision (loop-protocol Phase 5.5): run the guard - its result is an input to the decision.
3. Guard fails → recovery flow:

```
guard fails → revert → rework attempt 1 (different approach)
            → guard fails → rework attempt 2 (minimal change)
            → guard fails → discard (status: guard-failed)
```

**Rules:**
- If guard can't pass at baseline, fix it before the loop - never relax the guard.
- Guard-referenced files are **READ-ONLY** (tests, specs, guard scripts).
- A guard failure means the optimization is wrong, not the guard.

### Common guard commands

| Stack | Guard |
|---|---|
| Node | `npm test` |
| Python | `pytest` |
| Go | `go test ./...` |
| Rust | `cargo test` |
| TypeScript | `tsc --noEmit && npm test` |

Heuristic: optimizing runtime code → guard = full suite; optimizing build/bundle → `tsc --noEmit` + smoke; unsure → the project's default test command.

## Noise-aware verification

Noisy metrics produce false positives - "improvements" that are really measurement variance.

| Noise | Examples | Strategy |
|---|---|---|
| **low** | LOC, type errors, lint count | 1 run, trust it |
| **medium** | build time, unit-test timing (±5%) | 2 runs, take the **worse** result |
| **high** | API latency, benchmarks, ML accuracy | 3–5 runs, take the **median** (not mean) |

Use median for high noise - it resists single outlier spikes.

## Min-Delta threshold

Only KEEP when improvement exceeds the threshold:

```
improvement = (Direction=higher) ? new - prev : prev - new
if improvement < Min-Delta:  status = no-op   # not a failure, just insufficient
```

Defaults by noise: low = 0 · medium = 1–2% of baseline · high = 3–5% of baseline.

## Confirmation run

For high-stakes points (final 3 iterations, or improvement > 20%): re-verify once. Within 2% of the first measurement → confirm KEEP; outside 2% → treat as high noise and average the two.

## Environment pinning (user responsibility)

The loop can't control the environment. The user must ensure: fixed random seeds for ML; consistent cache warmth; no competing background processes; identical input data across runs.
