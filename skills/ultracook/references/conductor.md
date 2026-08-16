# Conductor - dynamic workflow selection

The conductor is the brain that runs **before** any state exists. It reads the task, classifies
it, and picks the smallest workflow that can prove the result. No ceremony for small
tasks; full machinery only when the task earns it.

Two orthogonal axes:

- **Mode** (how much workflow): `direct` · `pipeline` · `fan-out`
- **Autonomy** (how often to gate): `manual` · `semi` · `auto` - see `autonomy-modes.md`

Mode decides the *shape*; autonomy decides the *gating*. A `pipeline` can run `semi`;
a `fan-out` can run `auto`. Pick both.

## Step 1 - Classify

Read the goal text + repo signals. Score these axes (cheap heuristics, not a model call):

| Axis | Signal | Pull toward |
|---|---|---|
| **Clarity** | "maybe", "could", "or", contradictory or open-ended spec | brainstorm-first |
| **Reversibility** | delete / drop / force-push / deploy / migrate / revoke | approval gate |
| **Scope / blast** | "all", "every", "bulk", repo-wide, many files, external system | plan + fan-out |
| **Complexity** | multi-file, new subsystem, cross-cutting, >~50 LOC | pipeline |
| **Verification** | none / command / tests / build / browser / manual checklist | sets gate depth |

A task can score on several axes - take the strongest pull.

## Step 2 - Pick a mode

```
ambiguous spec                          → pipeline, shape = brainstorm-first
irreversible AND high blast radius       → pipeline + hard gate (always ask)
repo-wide / migration / N-finder audit   → fan-out
multi-file / real feature / has verifier → pipeline
small, clear, single-surface, reversible → direct
```

### `direct` - just do it
Trivial, clear, low-blast: a typo, one function, a narrow question, one command, a
config tweak. **Do not** create a goal-dir or `state.json`. Do the task, run the
narrowest useful check, report. Mention the full pipeline wasn't needed only if useful.

### `pipeline` - the goal loop (brainstorm → plan → cook → review → ship)
A real feature/fix with phases, uncertainty, or blast radius. This is the pipeline
core: compose a stage flow → run each stage's skill → `vd:auto-loop` for long
iteration → terminal. The conductor proposes the **flow slice** (see Step 3); the
user confirms it (`semi`/`manual`) or the proposal stands (`auto`).

### `fan-out` - parallel packets
Many *independent* work items: repo-wide audit, migration over many call sites,
N-finder review, broad refactor with disjoint file ownership. Use the host's native
parallelism (Claude Code `Workflow` tool / `Task` subagents; Codex subagents). See
[Fan-out packets](#fan-out-packets). The parent session always owns integration.

## Step 3 - Choose the flow slice

The spine is **brainstorm → plan → cook → review → ship**. Run the smallest slice;
skip stages the task doesn't need. Common slices (a stage is a skill name + a
checkable done-when - see SKILL.md Step 2; there is no closed vocabulary):

| Slice | Stages | Pick when |
|---|---|---|
| brainstorm-first | brainstorm → plan → cook → review → ship | spec is ambiguous / design not decided |
| plan-only | plan (stop) | user wants a plan, not execution |
| fix-and-ship | (scout) → cook → review → ship | clear fix, design already obvious |
| refactor | plan → cook → review | cross-cutting change, no new behavior |

In `semi`/`manual` the conductor *proposes*; the user can edit the stage list before
the run starts. In `auto` the conductor's proposal stands.

## Step 4 - Progressive autonomy (interactive → autonomous)

Stay human-in-the-loop until a gate clears, then run autonomously to a terminal
condition. Default `semi` already encodes this; the gate map:

| Gate | When it fires | After it clears |
|---|---|---|
| **Plan approval** | first `plan` action (semi) | run autonomously through cook |
| **Risk gate** | irreversible OR high-blast action | proceed once approved/compensated |
| **Ship** | `ship` action (semi) | land, then watch CI |
| **Final verify** | last stage's done-when check (semi) | mark terminal |

Once a gate clears, **do not re-gate** - escalate back to the user only on an
*exception*: a test failure in an unrelated area, a merge conflict, a structural
type/lint error (not auto-fixable), a tool/service down after retries, or a
never-seen error. This is what prevents approval fatigue. Gate semantics live in
`autonomy-modes.md`; nothing else makes gate decisions.

## Always ask (hard gates - every mode, including `auto`)

Stop and ask one clear yes/no before:

- Delete / overwrite / mass-rename; force-push, history rewrite, remote changes.
- Publish, deploy, email, post, or any external side effect.
- Migrations or broad codemods.
- Credentials, secrets, production data, billing, or user accounts.
- Expensive/long-running fan-outs (large `Workflow`, many subagents).
- Global installs or machine-level config; real customer data in prompts.

If approval is missing, continue only with safe read-only / local-draft work. For
ambiguous risk: state the action, state the side effect, offer a safe fallback (e.g.
a dry-run + diff), ask one question. Report any skipped risky action in the final answer.

## Fan-out packets

When mode = `fan-out`, decompose into narrow, bounded, evidence-based packets with
**disjoint write scope**. Good: "find entry points for X", "migrate adapter Y",
"add tests for module Z". Bad: "fix the whole thing", "edit any files you need".

Agent prompt shapes:

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

Use the host's native parallelism (Claude Code `Workflow` / `Task` subagents; Codex
subagents). Integration is never delegated - the parent reads each result, checks
claimed edits against source/tests, rejects unevidenced output, then verifies.

## Anti-patterns

- **Ceremony > signal.** If the task fits in ~30 lines of doing, it's `direct`. Don't
  spin up a goal-dir, packets, or a supervisor for a rename.
- **Unbounded autonomy.** Every `auto`/fan-out run keeps the hard guardrails: iter
  cap, retry caps, same-signature recognizer, token-cap prompt-back.
- **Gating trivia.** Don't gate variable renames. Gate irreversible OR high-blast only.
- **Vague gates.** Gate conditions must be checkable ("all tests pass", "plan lists
  rollback"), never "proceed if confident".

## Worked examples

| Prompt | Classify | Mode / shape / autonomy |
|---|---|---|
| "fix this typo in the README" | clear, tiny, reversible | `direct` |
| "should we use SSE or WebSockets for notifications?" | ambiguous design | `pipeline` / brainstorm-first / semi |
| "implement settings export, ship to staging, verify" | real feature, clear-ish | `pipeline` / fix-and-ship / semi |
| "migrate all API clients to the new SDK" | repo-wide, many sites | `fan-out` + hard gate (broad codemod) |
| "get lint errors to zero" | mechanical, measurable | `pipeline` / fix-and-ship / auto (delegates to `vd:optimize-loop`) |
| "audit the repo for slow startup paths" | broad, read-heavy | `fan-out`, read-only packets |
