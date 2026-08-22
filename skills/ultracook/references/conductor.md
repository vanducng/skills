# Conductor - classify, then compose

Read the task, pick the smallest workflow that can prove the result. No ceremony for small tasks; a goal-dir only when the task earns it.

Two orthogonal axes:

- **Mode** (how much workflow): `direct` · `pipeline` · `fan-out`
- **Autonomy** (how often to gate): `manual` · `semi` · `auto` - see `autonomy-modes.md`

## Step 1 - Classify

| Axis | Signal | Pull toward |
|---|---|---|
| **Want-clarity** | missing who / why / success / constraint / out of scope | interview-first (interactive only) |
| **How-clarity** | "maybe", "could", "or", open-ended approach after want is known | brainstorm-first |
| **Session-span** | "this is huge", "we'll be at this for a while", 3+ interdependent decisions still in fog | `vd:interview --wayfinder` (do not open a pipeline) |
| **Reversibility** | delete / drop / force-push / deploy / migrate / revoke | approval gate |
| **Scope / blast** | "all", "every", "bulk", repo-wide | plan + fan-out |
| **Complexity** | multi-file, new subsystem, cross-cutting, >~50 LOC | pipeline |
| **Verification** | none / command / tests / browser / checklist | sets `done_when` depth |

Take the strongest pull.

## Step 2 - Pick a mode

```
want unclear                         → pipeline, interview-first (semi/manual only)
how unclear, want known              → pipeline, brainstorm-first
deciding will not fit one session    → vd:interview --wayfinder; no pipeline
irreversible AND high blast          → pipeline + hard gate
repo-wide / migration / N-finder     → fan-out
multi-file / real feature            → pipeline
small, clear, single-surface         → direct
want unclear AND autonomy=auto       → block; do not invent intent
```

### `direct`

Typo, one function, a narrow question, one command. Do **not** create `state.json`. Do the task with `vd:cook --quick` or `vd:fix`, run the narrowest useful check, report.

### `pipeline`

A real feature/fix. Write `state.json` with the stages the task earns (skill name + `done_when`). Invoke each skill; the skill owns its discipline. Use `vd:auto-loop` when a stage must iterate (usually cook/verify).

### `fan-out`

Many independent items. Use the host's native parallelism. Two packet shapes: **split** (divide the work) and **arena** (N candidates compete, then graft). The parent always owns integration.

## Step 3 - Choose the slice

The spine is **interview → brainstorm → plan → cook → ship**. Skip stages the task does not need.

| Shape | Stages | Pick when |
|---|---|---|
| `interview-first` | interview → (brainstorm or plan) → cook → ship | want unconfirmed |
| `brainstorm-first` | brainstorm → plan → cook → ship | want known, approach not decided |
| `plan-only` | plan | user wants a plan, not execution |
| `fix-and-ship` | cook or fix → ship | clear fix, design obvious |
| `refactor` | plan → cook → code-review --refactor | cross-cutting change, no new behavior |

In `semi`/`manual` the conductor proposes; the user can override. In `auto` the proposal stands.

A mid-pipeline hole is `vd:interview --grill` on that decision, not a new conductor verb.

## Always ask (every mode, including `auto`)

Stop for a clear yes/no before:

- Delete / overwrite / mass-rename; force-push, history rewrite, remote changes
- Publish, deploy, email, post, or any external side effect
- Migrations or broad codemods
- Credentials, secrets, production data, billing, or user accounts
- Expensive/long-running fan-outs
- Global installs or machine-level config; real customer data in prompts

If approval is missing, continue only with safe read-only or local-draft work. For ambiguous risk: state the action, state the side effect, offer a dry-run, ask one question.

Deploy and rollout checks (image tag, `kubectl rollout status`) live in `vd:devops` references, not in this conductor.

## Fan-out packets

Narrow, bounded, evidence-based, **disjoint write scope**.

```text
Read-only packet:
  Task: <specific read-only objective>
  Do: inspect only listed sources; cite file:line; return findings + evidence.
  Do not: edit files; duplicate other packets' work.
  Output: summary, evidence, risks, recommended parent action.

Write-capable packet:
  You are not alone in the codebase. Other agents edit other files.
  Do not revert others' edits. Adapt to nearby changes.
  Ownership: <files or module - disjoint from all other packets>
  Task: <specific implementation task>
  Do: edit only owned files; add focused tests if the area has them; list changes.
  Do not: change behavior outside this packet; broad-format; commit/push/deploy.
  Output: files changed, summary, verification run, risks/blockers.
```

Integration is never delegated. The parent reads each result, checks claimed edits against source/tests, rejects unevidenced output, then verifies.

### Arena packets (compete, then graft)

Use when one attempt at a single non-trivial artifact would lock in the wrong shape.

1. **Frame before spawning.** Write the spec and a 3-6 criterion rubric first. Candidates see the task, never the rubric.
2. **Fan out 2-4 candidates** to their own output dirs. Each returns the artifact plus a short rationale naming rejected alternatives.
3. **Judge against the rubric**, criterion by criterion, after reading every candidate.
4. **Pick a base, graft the rest.** Port one or two strongest ideas from each loser by hand. Record picks in `decisions.tsv` when a goal-dir exists.
5. **Convergence is signal.** Same shape from N candidates → ship the consensus. Wild divergence → reframe, do not average.
6. **Verify like any other output.** The arena does not earn a verification pass.

## Anti-patterns

- **Ceremony > signal.** A rename is `direct`. No goal-dir.
- **Closed vocab.** Do not invent conductor actions or verifier types. Name the skill and the `done_when`.
- **Vague gates.** "Proceed if confident" is not a gate.
- **Unbounded autonomy.** Keep the iter / rebase / CI / same-signature caps from SKILL.md.

## Worked examples

| Prompt | Mode / shape |
|---|---|
| "fix this typo in the README" | `direct` |
| "build me a dashboard" | `pipeline` / interview-first / semi |
| "should we use SSE or WebSockets?" | `pipeline` / brainstorm-first / semi |
| "rebuild billing, auth, and admin - weeks of work" | `vd:interview --wayfinder` (no pipeline) |
| "implement settings export and ship" | `pipeline` / fix-and-ship / semi |
| "migrate all API clients to the new SDK" | `fan-out` + hard gate |
| "get lint errors to zero" | `pipeline` / fix-and-ship / auto (may compose `vd:optimize-loop`) |
| "audit the repo for slow startup paths" | `fan-out`, read-only packets |
