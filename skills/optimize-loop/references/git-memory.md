# Git as Memory + Results Log

Git history + `loop-results.tsv` are the loop's only cross-iteration memory. Read them every iteration.

## Required reads - every iteration

```bash
git log --oneline -20      # what changed, in what order
git diff HEAD~1            # exact last diff
cat loop-results.tsv       # metric trend + keep/discard record
```

They answer: **what worked** (kept rows, positive delta), **what failed** (discarded rows, repeated paths), **where is the trend going** (last 5 deltas - accelerating, flat, reversing).

## Pattern recognition

- **Exploit:** a file category / technique that improved before → try adjacent files / untouched functions.
- **Avoid:** a file+technique pair already discarded → don't retry it; an oscillating file → leave it, move on.
- **Diminishing returns:** if the last 5 kept iterations all have `delta < 2 × Min-Delta`, the low-hanging fruit is gone → broaden scope, switch technique, or report a plateau instead of grinding.

## Revert vs reset

| Command | Preserves history | Use when |
|---|---|---|
| `git revert HEAD --no-edit` | yes | **default** discard path |
| `git reset --hard HEAD~1` | no | only when revert conflicts |

`git log --grep="loop(iter-"` relies on intact history - a reset silently breaks future pattern analysis. Reverted commits stay in history (with the standard `Revert "..."` message); discards are part of the experiment record.

## Commit convention

```
loop(iter-N): <one-line description>
```

Examples: `loop(iter-3): add null guard to parseToken in lexer.ts` · `loop(iter-12): drop unused lodash import, -1.2kB`.

## Results log (`loop-results.tsv`)

Tab-separated, one row per iteration, header required.

```
iteration	timestamp	commit	metric	delta	status	description
```

| Column | Notes |
|---|---|
| iteration | 0-indexed; 0 = baseline |
| timestamp | ISO-8601 of the measurement |
| commit | short SHA from Phase 4 (kept SHA on KEEP; reverted SHA on discard/no-op/guard-failed; `-` only if crash before commit) |
| metric | measured value |
| delta | signed change from previous best; `-` for baseline |
| status | see enum below |
| description | one sentence - what was attempted |

### Status enum

| Status | Meaning | Stuck counter |
|---|---|---|
| `baseline` | initial measurement | - |
| `keep` | improvement ≥ Min-Delta, passed guard, committed | reset to 0 |
| `keep (reworked)` | failed guard once, reworked, then passed | reset to 0 |
| `no-op` | improved but below Min-Delta (not a failure); reverted | +1 |
| `discard` | no improvement / regression; reverted | +1 |
| `guard-failed` | metric improved but guard failed; reverted | +1 |
| `crash` | verify errored or timed out; reverted | +1 |

### Example

```tsv
iteration	timestamp	commit	metric	delta	status	description
0	2026-05-31T12:00:00	a1b2c3d	842	-	baseline	initial bundle size
1	2026-05-31T12:01:10	e4f5a6b	810	-32	keep	tree-shake unused lodash imports
2	2026-05-31T12:02:05	b8c9d0e	798	-12	no-op	remove dead CSS - below min-delta
3	2026-05-31T12:03:40	c7d8e9f	771	-39	keep	replace moment.js with day.js
4	2026-05-31T12:04:12	-	-	-	crash	build errored on dynamic import rewrite
5	2026-05-31T12:05:30	1a2b3c4	751	-20	guard-failed	inline critical CSS - tests failed
6	2026-05-31T12:06:50	5d6e7f8	758	-13	keep (reworked)	inline critical CSS, guard-safe
```

## Progressive summaries

Print after every 5 iterations and at the end:

```
--- Progress @ iter 5 ---
Best: 751 (baseline 842, -10.8%)  |  kept 3 · discarded 1 · crashed 1 · guard-failed 1
Top strategy: dependency replacement (moment→day.js, -39)

--- Final ---
Baseline → final: 842 → 741 (-11.9%, -101)
7 iterations | kept 4 · discarded 1 · crashed 1 · guard-failed 1
Key insight: dependency replacement yielded most gains; CSS inlining needed guard-safe rework
```
