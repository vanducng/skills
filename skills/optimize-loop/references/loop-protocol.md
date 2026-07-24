# Loop Protocol

Phases 0–8 per iteration (plus a 5.5 guard step). Run in order - no skipping.

## Phase 0 - Precondition checks (first iteration only)

Abort with a clear error if any fails:

1. Current dir is a git repo (`git rev-parse --git-dir`).
2. Working tree is clean (`git status --porcelain` → empty).
3. HEAD is on a named branch (not detached).
4. No stale `loop-results.tsv.lock`.
5. `Scope` glob matches ≥1 file.
6. Dry-run `Verify` → exits 0 and prints a number. (Apply the safety screen in SKILL.md *before* this dry-run.)
7. Dry-run `Guard` (if set) → exits 0.
8. Record the **baseline metric** as iteration 0 in `loop-results.tsv`.

## Phase 1 - Review

Read context every iteration (never skip):

```bash
git log --oneline -20      # recent history
git diff HEAD~1            # last change
cat loop-results.tsv       # metric trend + keep/discard record
```

Extract: which file types/techniques improved the metric, which were discarded, is the trend rising / flat / oscillating?

## Phase 2 - Ideate

Pick **ONE** focused change.

- **Atomicity test:** describe it in one sentence; if it contains "and", split into two iterations.
- Exploit patterns from kept iterations; avoid the exact file+technique pairs that were discarded.
- Prefer high-leverage targets (lowest-coverage file, biggest bundle contributor, most lint errors).
- After 3+ discards in one area → pivot to a different file or technique.

## Phase 3 - Modify

- Edit within `Scope` only.
- **Never** modify files referenced by `Guard`.
- Keep syntax valid after the edit (run the language's type-check / linter).
- One logical unit - no drive-by changes.

## Phase 4 - Commit (before verify)

```bash
git add <changed files>
git commit -m "loop(iter-N): <one-line description>"
```

Git is the undo mechanism, not a post-hoc save. The `loop(iter-N):` prefix enables later log filtering.

## Phase 5 - Verify

```bash
RESULT=$(eval "$VERIFY_CMD"); DELTA=$(echo "$RESULT - $PREV_METRIC" | bc)
```

| Outcome | Meaning | Action |
|---|---|---|
| Exit 0, number printed | success | proceed to 5.5 / 6 |
| Exit 0, no number | bad command | log `crash` (no-number), revert, fix the verify cmd |
| Exit non-zero | verify crash | log `crash`, revert, treat as discard |
| Timeout (>30s) | too slow | log `crash` (timeout), abort loop, surface to user |

For noisy metrics, run multiple times and aggregate per `references/verification-and-guard.md` before computing delta.

## Phase 5.5 - Guard (skip if no Guard)

```bash
eval "$GUARD_CMD"; GUARD_EXIT=$?
```

| Guard exit | Action |
|---|---|
| 0 | proceed to Phase 6 |
| non-zero | revert; rework (max 2 attempts); if still failing, discard with status `guard-failed` |

## Phase 6 - Decide

Guard runs in Phase 5.5 (before this decision); its pass/fail is an input here.

| Direction | Delta vs Min-Delta | Guard | Decision | status |
|---|---|---|---|---|
| higher | `delta ≥ Min-Delta` | pass | **KEEP** | `keep` |
| higher | `0 < delta < Min-Delta` | pass | revert | `no-op` |
| higher | `delta ≤ 0` | pass | revert | `discard` |
| lower | `delta ≤ -Min-Delta` | pass | **KEEP** | `keep` |
| lower | `-Min-Delta < delta < 0` | pass | revert | `no-op` |
| lower | `delta ≥ 0` | pass | revert | `discard` |
| any | any | fail | revert | `guard-failed` |
| any | verify crash | n/a | revert | `crash` |

- **KEEP:** update `PREV_METRIC`; reset consecutive-discard counter to 0.
- **Revert (discard / no-op / guard-failed / crash):** `git revert HEAD --no-edit` (fallback `git reset --hard HEAD~1` only if revert conflicts); **increment the consecutive-discard counter** (a `no-op` counts toward stuck detection - sub-threshold change is the stuck signal).

## Phase 7 - Log

Append one row to `loop-results.tsv` (schema in `references/git-memory.md`):

```
{iteration}\t{ISO8601}\t{commit}\t{metric}\t{delta:+}\t{status}\t{description}
```

`commit` = the short SHA created in Phase 4 (kept on KEEP; the reverted SHA on discard/no-op/guard-failed; `-` only if the crash happened before the commit).

## Phase 8 - Repeat or stop

Continue while **all** hold: `iter < Iterations`, consecutive discards `< 10`, no `loop-stop` file / interrupt.

| Consecutive discards | Action |
|---|---|
| 5 | analyze the log → shift strategy |
| 10 | STOP - surface findings |

### Final report

```
Loop complete: N iterations, K kept, best metric X (baseline Y, Δ +Z)
Kept: [commit hashes + descriptions]
Discarded: [count]
Recommendation: continue / diminishing returns / target met
```

## Anti-patterns

| Anti-pattern | Why it fails | Correct |
|---|---|---|
| Multiple changes per iteration | metric delta unattributable | one atomic change |
| Verify before commit | no rollback if verify crashes | commit first |
| Editing guard-scope files | guard becomes meaningless | guard files read-only |
| `git reset` instead of `revert` | destroys history / pattern analysis | `git revert` |
| Skipping Phase 1 review | repeats failed patterns | always read log + diff |
| Ignoring `Min-Delta` | keeps noise as "progress" | set a meaningful threshold |
