---
name: plan
description: "Turn a chosen approach into a phased implementation plan with concrete steps, file changes, and success criteria. Use after `vd:brainstorm` (or any decided design) when you need to sequence the work before building. Default produces plan.md + phase files; pass `--quick` for a single-file plan, `--deep` for research dispatch + red-team review."
license: MIT
argument-hint: "[task or path to brainstorm brief] [--quick | --deep] [--tdd]"
metadata:
  author: vanducng
  version: "1.0.0"
---

# Plan

## What this skill is — and isn't

| Skill | Question it answers | Output |
|---|---|---|
| `vd:brainstorm` | "How should I approach this — what are the options?" | Decision brief with 3+ approaches |
| `vd:research` | "Which of these known options should I pick?" | Comparison report with citations |
| **`vd:plan`** | **"Given the chosen approach, what are the steps to ship it?"** | **Phased plan: `plan.md` + `phase-XX-*.md`** |
| `vd:cook` (or manual impl) | "Execute the plan." | Code changes |

Plan converts a *decided* approach into a *sequenced* implementation. If the approach isn't decided, stop and run `vd:brainstorm` first. A plan that opens with "we should consider whether to use X or Y" is a brainstorm in disguise — kick it back.

## Hard rules

1. **No code, no scaffolding, no source edits.** Only plan files. If the user pushes for implementation, hand off to `vd:cook` or implement separately.
2. **One decided approach in, one plan out.** If the input is ambiguous about *what* is being built, ask — don't guess and write a plan for the wrong shape.
3. **Phases are independently reviewable units.** Each phase should be reviewable/mergeable on its own — not "step 4 of 12 with no working state in between." A phase that can't ship standalone is two phases.
4. **Concrete, not aspirational.** Every phase names the files it touches, the steps in order, and the criteria that prove it's done. "Implement auth" is not a phase. "Add `auth/middleware.ts` validating JWT signature against JWKS endpoint, reject expired tokens" is.
5. **YAGNI/KISS/DRY.** Don't plan for hypothetical future features. Don't add phases for cleanups the task doesn't need. Three similar phases is better than a generic abstraction.
6. **Brutal honesty on scope.** If the task is too big for one plan, say so in Phase 1 and propose decomposition.

## Modes

| Mode | When | Output |
|---|---|---|
| `--quick` | Single-file change, bug fix, tight scope (<3 phases) | One file: `plans/{date}-{slug}/plan.md` with inline steps |
| **default** | Standard feature, 3-7 phases | `plan.md` overview + `phase-XX-{name}.md` per phase |
| `--deep` | High-risk, multi-system, irreversible | Default output + research dispatch (Phase 2) + red-team review (Phase 6) |

Composable flag:

| Flag | Effect |
|---|---|
| `--tdd` | Each phase opens with a "Tests first" step + a failing-test checklist before implementation |

Detect mode from the argument or task shape. Announce mode in your first reply.

## Phase 1 — Frame

Before writing any plan file, in your reply, capture:

- **Goal** — one sentence. What ships at the end.
- **Approach** — one paragraph. The chosen design (from brainstorm brief, or stated by user).
- **Success criteria** — observable signals that the goal is met (not "code works" — "endpoint X returns 200 with shape Y", "page loads in <500ms on 3G").
- **Scope boundary** — what's *out* of scope. Out-of-scope items get listed but not planned.
- **Constraints** — language, runtime, team size, existing systems that can't change.

If any of these are unclear after reading the task / brainstorm brief, **ask before writing files**. A misaimed plan wastes more than the 60 seconds it takes to clarify.

### Scope check (mandatory)

If the goal spans 3+ independent shippable features → **stop**. Reply:

> This plan would have N+ phases across independent features. Suggest splitting into separate plans: [A, B, C]. Build order: [reason]. Pick one to start.

A plan with 12+ phases is almost always two plans pretending to be one.

## Phase 2 — Discover (`--deep` only, optional in default)

Before designing phases, gather what exists:

- **Codebase scan** — read entry points, existing patterns, conventions in `docs/`. Delegate to a subagent (`Explore` or `general-purpose` via the `Agent` tool) if the codebase is large; do not bloat the planning session with file dumps.
- **Research** — for unfamiliar libraries/APIs, use `WebSearch` or `vd:research`. In `--deep` mode, dispatch 1–2 researcher subagents for parallel topics (e.g. "X library auth flow", "Y rate-limit patterns").
- **Risks** — note version mismatches, deprecated APIs, breaking changes, hidden state (caches, feature flags, migrations) that affect sequencing.

Skip this phase if the user provided scout/research reports already. Don't repeat work.

## Phase 3 — Design phases

Decompose the approach into 3–7 phases. Rules:

- **Order by dependency, not by domain.** "Backend then frontend" is a domain split. The right split is "what unblocks the next thing." If frontend can be stubbed and backend phases can ship independently, do that.
- **First phase ships something small and real.** Setup-only phases ("configure tooling") are fine but should be ≤1 phase. Don't spend 3 phases on scaffolding.
- **Last phase = integration + validation.** The plan ends with the system working end-to-end against success criteria.
- **Each phase has a single owner concern.** "Add migration + endpoint + UI" is three phases. "Add migration" is one.
- **Name phases with the verb.** `phase-03-add-rate-limit-middleware.md`, not `phase-03-rate-limit.md`.

Sketch the dependency graph in your reply (text or mermaid) before writing files. Catch ordering bugs cheap.

## Phase 4 — Write plan files

### Directory layout

```
plans/{YYYYMMDD-HHMM}-{slug}/
  plan.md
  phase-01-{verb-noun}.md
  phase-02-{verb-noun}.md
  ...
```

Use the date/slug pattern injected by session hooks (`## Naming` block). If unavailable, fall back to `plans/{YYYYMMDD-HHMM}-{slug}/`.

### `plan.md` template (≤80 lines)

```markdown
---
title: "{Plan title}"
status: pending          # pending | in-progress | completed
goal: "{one-sentence goal}"
created: {YYYY-MM-DD}
mode: default            # quick | default | deep
---

# {Plan title}

## Goal
{One sentence — what ships.}

## Approach
{One paragraph — the chosen design. Link to brainstorm brief if applicable.}

## Success Criteria
- [ ] {observable signal}
- [ ] {observable signal}

## Out of Scope
- {explicit non-goal} — {why deferred}

## Phases

| # | Phase | Status | Depends on | Effort |
|---|---|---|---|---|
| 1 | [{verb-noun}](phase-01-{verb-noun}.md) | pending | — | {est} |
| 2 | [{verb-noun}](phase-02-{verb-noun}.md) | pending | 1 | {est} |
| ... | | | | |

## Constraints
- {fixed thing}
- {fixed thing}

## Risks
- {risk} → {mitigation}

## References
- Brainstorm brief: {path if applicable}
- Research: {paths}
```

### `phase-XX-{verb-noun}.md` template

```markdown
---
phase: {N}
title: "{verb-noun}"
status: pending          # pending | in-progress | completed
priority: P2             # P1 (blocker) | P2 (default) | P3 (nice-to-have)
effort: "{e.g. 2h, 1d}"
depends_on: [{phase ids}]
---

# Phase {N}: {Title}

## Overview
{1–2 sentences: what this phase delivers, why it's a phase.}

## Files
- **Create:** `path/...`
- **Modify:** `path/...`
- **Delete:** `path/...`

## Steps
1. {concrete step — file, function, change}
2. {concrete step}
3. ...

## Tests   <!-- omit if --tdd is off and phase has no test surface -->
- [ ] {test case the phase must pass}
- [ ] {edge case}

## Success Criteria
- [ ] {observable — runs, returns X, no regression in Y}

## Risks
- {risk} → {mitigation}
```

`--tdd` mode: the **Tests** section moves to the top (above Steps), and Step 1 of every phase is "Write the failing tests listed below."

`--quick` mode: single `plan.md` file. Phases become bullet sections inside the same file. No separate phase files.

## Phase 5 — Hand off

After writing files, in your reply:

1. **List the files written** (relative paths).
2. **Show the phases table** verbatim from `plan.md` so the user sees the shape without opening it.
3. **Recommend the next action:**
   - For implementation: `vd:cook {plan-dir}` or "I can implement Phase 1 — say go."
   - For more rigor: "Run `--deep` mode with red-team review?"
4. **Ask if anything's missing.** Don't claim done until the user confirms the shape is right.

## Phase 6 — Red-team review (`--deep` only)

After writing the plan, before declaring done, run an adversarial pass. In your reply, ask the plan three hostile questions and answer them honestly:

| Persona | Question |
|---|---|
| **Skeptical reviewer** | "What does this plan assume that isn't true?" |
| **On-call engineer** | "What page do I get at 3am when this ships?" |
| **Future maintainer** | "What will I curse you for in 6 months?" |

If any answer reveals a real problem → revise the plan and note the change in `plan.md` under a `## Revisions` section. Don't hide the iteration.

## Anti-rationalization

| Excuse | Reality |
|---|---|
| "This is too small to need phases" | Then `--quick` mode with inline steps. Still write the file — it's the diff of intent. |
| "User wants implementation, not planning" | A 5-minute plan saves a 5-hour wrong implementation. Push back briefly, then plan. |
| "I'll figure out the steps as I go" | The point of a plan is to discover the wrong steps cheaply. Write them. |
| "The phases overlap a bit" | Then they're one phase. Merge them. |
| "I'll skip the success criteria — they're obvious" | They're never obvious. Future-you, on review, will not remember. Write them. |
| "This phase has 15 steps but it's one concern" | 15 steps = unreviewable PR = not one phase. Split. |

## Quality bar

- **Concrete files.** Every phase names the files it creates/modifies/deletes. No "implement the thing."
- **Independent phases.** Each phase ships something reviewable. No "phase 4 of 12 with broken state at the end."
- **Observable success criteria.** Every phase ends with checks a human or test can run. Not "code works."
- **Honest scope.** Out-of-scope is listed explicitly. Risks are named, not hand-waved.
- **Self-contained.** A new contributor can pick up Phase N and ship it from the file alone.
- **Decided.** No "we should evaluate X vs Y" in the plan body — that's brainstorm. Plan is post-decision.

## Specials

- **Migrations / schema changes** — phase 1 is always the migration with rollback path; later phases assume the migration applied. Do not interleave migration steps with feature steps.
- **API breaking changes** — sequence as: add new (phase A) → migrate callers (phase B) → remove old (phase C). Never do all three in one phase.
- **Performance work** — phase 1 captures baseline numbers (against success criteria). Without baseline, "faster" is unfalsifiable.
- **Refactors** — `--tdd` is mandatory. No tests = no safety net = no refactor plan, just hope.
- **Bug fixes** — `--quick` mode is usually right. If the fix needs 3+ phases, the bug is a redesign in disguise — escalate to `vd:brainstorm`.
- **Library upgrades** — every phase ends with "tests pass + manual smoke test of {feature touched}." Don't lump the smoke tests into a final QA phase.

## Output rules

1. Announce mode (`--quick` / default / `--deep`) and `--tdd` if set in your first reply.
2. Phase 1 (frame + scope check) happens *before* writing any files — visible to the user.
3. If decomposition triggers, stop and ask — do not write a 12-phase mega-plan.
4. Default and `--deep` write `plan.md` + phase files. `--quick` writes only `plan.md` with inline phases.
5. After writing, list files + show phases table in your reply (don't make the user open files to see the shape).
6. End with the handoff recommendation (implement, deepen, revise) — don't leave the user wondering what's next.
7. `--deep` mode is not done until the red-team round runs.

## Workflow position

**Typically follows:** `vd:brainstorm` (after deciding the approach), `vd:research` (after picking a known option), `/ck:scout` or `/ck:debug` (after discovery)
**Typically precedes:** `vd:cook` (execute the plan), or manual implementation phase-by-phase
**Compares to:** `vd:brainstorm` (pre-decision exploration) — if you find yourself debating approaches inside a plan, kick back to brainstorm
