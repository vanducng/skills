---
name: plan
description: "Turn a chosen approach into a phased implementation plan with concrete steps, file changes, and success criteria. Use after `vd:interview` and `vd:brainstorm` (or a cleared `vd:interview --wayfinder` chunk, or any decided design) when you need to sequence the work before building. Default produces plan.md + phase files; pass `--quick` for a single-file plan, `--deep` for research dispatch + red-team review, `--audit` to independently check an existing plan. Do not use while the approach is still foggy across multiple fronts - that's vd:interview --wayfinder."
license: MIT
argument-hint: "[task or path to brainstorm brief | plan-dir --audit] [--quick | --deep] [--tdd] [--audit [--fix [--apply-all]]]"
metadata:
  author: vanducng
  version: "1.3.0"
---

# Plan

Plan converts a *decided* approach into a *sequenced* implementation. If the approach isn't decided, stop and run `vd:brainstorm`. If the *deciding* itself will not fit one session, stop and run `vd:interview --wayfinder`. A plan that opens with "we should consider whether to use X or Y" is a brainstorm in disguise - kick it back.

## Hard rules

1. **No code, no scaffolding, no source edits.** Only plan files. If the user pushes for implementation, hand off to `vd:cook` or implement separately.
2. **One decided approach in, one plan out.** If the input is ambiguous about *what* is being built, ask - don't guess and write a plan for the wrong shape.
3. **Phases are independently reviewable units.** Each phase should be reviewable/mergeable on its own - not "step 4 of 12 with no working state in between." A phase that can't ship standalone is two phases.
4. **Concrete, not aspirational.** Every phase names the files it touches, the steps in order, and the criteria that prove it's done. "Implement auth" is not a phase. "Add `auth/middleware.ts` validating JWT signature against JWKS endpoint, reject expired tokens" is.
5. **YAGNI/KISS/DRY.** Don't plan for hypothetical future features. Don't add phases for cleanups the task doesn't need. Three similar phases is better than a generic abstraction.
6. **Brutal honesty on scope.** If the task is too big for one plan, say so in Phase 1 and propose decomposition.

## Modes

| Mode | When | Output |
|---|---|---|
| `--quick` | Single-file change, bug fix, tight scope (<3 phases) | One file: `{plans-path}/{date}-{slug}/plan.md` with inline steps |
| **default** | Standard feature, 3-7 phases | `plan.md` overview + `phase-XX-{name}.md` per phase |
| `--deep` | High-risk, multi-system, irreversible | Default output + research dispatch (Phase 2) + red-team review (Phase 6) + independent audit (Phase 7) |
| `--audit` | Existing plan needs a clean-context second look | Severity-tagged report; optional `--fix` / `--fix --apply-all`. See [`references/audit.md`](references/audit.md) |

Composable flag: `--tdd` opens each phase with a "Tests first" step + a failing-test checklist before implementation.

Detect mode from the argument or task shape. A path to an existing plan dir plus `--audit` (or "audit this plan") is audit-only: skip Phases 1-6 and follow [`references/audit.md`](references/audit.md). Announce mode (and `--tdd`) in your first reply.

## Phase 1 - Frame

Before writing any plan file, in your reply, capture:

- **Goal** - one sentence. What ships at the end.
- **Approach** - one paragraph. The chosen design (from brainstorm brief, or stated by user).
- **Success criteria** - observable signals that the goal is met (not "code works" - "endpoint X returns 200 with shape Y", "page loads in <500ms on 3G").
- **Definition of Done** - the goal's *machine-checkable* form: 1-5 typed verifiers (`test_suite_passes`, `cmd_exits_zero`, `shell`, `http_status`, `manual_confirm`), one per line as `- <type>: <arg>`. Plain commands + expected results only, **no tool-specific constructs**, so the goal runs identically under Claude Code and Codex. `vd:cook` runs them as a final goal gate via the shared runner `cook/scripts/eval-dod.sh` (resolved across the `$HOME/.claude/skills`, `$HOME/.agents/skills`, `$HOME/skills/skills` install roots - see `vd:cook` Phase 3); validate the block as you write it with `eval-dod.sh --lint <plan.md>`.
- **Scope boundary** - what's *out* of scope. Out-of-scope items get listed but not planned.
- **Constraints** - language, runtime, team size, existing systems that can't change.

If who / why / success / constraint / out of scope are not confirmed (no interview intent file, no brainstorm brief, no explicit user restate), **stop and run `vd:interview`** before writing files. A misaimed plan wastes more than the interview. If only a sequencing detail is fuzzy after a confirmed intent, **ask before writing files**.

### Capture decisions (mandatory if any non-goals stated)

Note any explicit non-goals or trade-offs the user states ("skip auth", "no migration needed", "use library X over Y", "defer i18n"). These belong in `{plan-dir}/decisions.md`, written alongside `plan.md` in Phase 4. Ask "any explicit non-goals to record?" if none have surfaced and the task feels likely to omit common scaffolding.

**Tip:** if a brainstorm brief exists, copy its "Avoid" / "Out of scope" / "Open questions" sections into `decisions.md` as starting non-goals. The `--audit` subagent reads `decisions.md` and respects listed exclusions, so capturing them here prevents false-positive findings later.

### Scope check (mandatory)

If the goal spans 3+ independent shippable features → **stop**. Reply:

> This plan would have N+ phases across independent features. Suggest splitting into separate plans: [A, B, C]. Build order: [reason]. Pick one to start.

A plan with 12+ phases is almost always two plans pretending to be one. And if the *decisions* themselves span more sessions than the phases do - the approach is still foggy across multiple fronts - escalate to `vd:interview --wayfinder` instead: chart the open decisions as a map, then come back here per cleared chunk.

## Phase 2 - Discover (`--deep` only, optional in default)

- **Codebase scan** - read entry points, existing patterns, conventions in `docs/`. Delegate to a subagent (`Explore` or `general-purpose` via the `Agent` tool) if the codebase is large; do not bloat the planning session with file dumps.
- **Research** - for unfamiliar libraries/APIs, use `WebSearch` or `vd:research`. In `--deep` mode, dispatch 1-2 researcher subagents for parallel topics (e.g. "X library auth flow", "Y rate-limit patterns").
- **Risks** - note version mismatches, deprecated APIs, breaking changes, hidden state (caches, feature flags, migrations) that affect sequencing.

Skip this phase if the user provided scout/research reports already. Don't repeat work.

## Phase 3 - Design phases

Decompose the approach into 3-7 phases. Rules:

- **Order by dependency, not by domain.** "Backend then frontend" is a domain split. The right split is "what unblocks the next thing." If frontend can be stubbed and backend phases can ship independently, do that.
- **First phase ships something small and real.** Setup-only phases ("configure tooling") are fine but should be ≤1 phase. Don't spend 3 phases on scaffolding.
- **Last phase = integration + validation.** The plan ends with the system working end-to-end against success criteria.
- **Each phase has a single owner concern.** "Add migration + endpoint + UI" is three phases. "Add migration" is one.
- **Name phases with the verb.** `phase-03-add-rate-limit-middleware.md`, not `phase-03-rate-limit.md`.
- **Phase-sizing ceiling (tracer bullet).** A phase touches ≤5 files and ships in one focused session. Prefer a thin slice that proves the riskiest unknown over a wide scaffold. Tripwires that mean *split it*: an `and` in the title, spanning two independent subsystems, or a Success-Criteria list past ~4 items.

**Slicing strategy** - pick one per plan (they compose with dependency ordering):

- **Vertical** (default) - each phase is one complete path through the stack, shippable on its own.
- **Contract-first** - when work fans out across a shared interface, make Slice 0 *freeze the contract* (the API/type/schema), then later phases build against it in parallel. Stops integration churn.
- **Risk-first** - sequence the riskiest unknown first (the spike that could invalidate the design), so a dead end is found cheaply before dependent work is built on it.

Sketch the dependency graph in your reply (text or mermaid) before writing files. Catch ordering bugs cheap.

## Phase 4 - Write plan files

**Feature-first repos - claim a feature first.** If the hook context shows `Feature: none` (paths resolve under `_global/scratch/`), run `workbench new <slug>` (kebab summary of the task) before writing, then use the paths it prints - the plan lands in `features/<slug>/plans/` instead of the shared scratch bin. Idempotent: skip when a feature is already active (a `feat/*` branch, an active plan, or a prior `workbench new`).

Write to the injected `Plans:` path, using the date/slug pattern injected by session hooks (`## Naming` block).

```
{plans-path}/{YYYYMMDD-HHMM}-{slug}/
  plan.md
  decisions.md          # OPTIONAL - non-goals, trade-offs, accepted constraints. Write only if user stated any.
  phase-01-{verb-noun}.md
  phase-02-{verb-noun}.md
  ...
```

### `decisions.md` template (write only if non-goals/trade-offs were stated)

```markdown
# Decisions for {plan-title}
_Captured during vd:plan on {YYYY-MM-DD}_

## Non-goals (intentionally excluded)
- **{thing}** - reason: {user-stated rationale}

## Trade-offs
- **{decision}** - chose {A} over {B} because {rationale}

## Constraints accepted
- **{constraint}** - {context}

## Agent boundaries
_Optional. Write only if the build has dangerous edges. cook and `vd:plan --audit` honor these as guardrails._
- **Always:** {things the implementer may do without asking - e.g. add tests, refactor within a touched file}
- **Ask first:** {things needing a checkpoint - e.g. schema migrations, new dependencies, touching auth}
- **Never:** {hard lines - e.g. delete prod data, edit generated files, commit secrets, change the public API}
```

Keep it flat: bullets, not prose. The audit subagent treats listed non-goals as out-of-scope and won't report them as gaps; it treats `Ask first`/`Never` items as guardrails the plan must respect.

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
{One sentence - what ships.}

## Approach
{One paragraph - the chosen design. Link to brainstorm brief if applicable.}

## Success Criteria
- [ ] {observable signal}
- [ ] {observable signal}

## Definition of Done
<!-- One verifier per line: `- <type>: <arg>`. vd:cook runs these via cook/scripts/eval-dod.sh (the goal gate). Plain shell → identical in Claude Code & Codex. -->
- test_suite_passes: {test command, e.g. npm test}
- cmd_exits_zero: {build or lint command}
# more types: `- shell: <cmd>` · `- http_status: <url> <code>` · `- manual_confirm: <prompt>`

## Test Seams
<!-- One line per seam: the command cook will run, what a failure looks like before the phase lands, and any fixture / env var / service the command needs. -->
- `{npm test -- settings-csv}` - fails with {symptom} until Phase {N} lands - needs {fixture/env/service}

## Out of Scope
- {explicit non-goal} - {why deferred}

## Phases

| # | Phase | Status | Depends on | Effort |
|---|---|---|---|---|
| 1 | [{verb-noun}](phase-01-{verb-noun}.md) | pending | - | {est} |
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

Every default/`--deep` plan carries that `## Test Seams` section plus a `## Tests` / `## Verify` pair on each phase. A plan with no seams is a plan cook cannot gate.

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
{1-2 sentences: what this phase delivers, why it's a phase.}

## Files
- **Create:** `path/...`
- **Modify:** `path/...`
- **Delete:** `path/...`

## Steps
1. {concrete step - file, function, change}
2. {concrete step}
3. ...

## Tests   <!-- omit if --tdd is off and phase has no test surface -->
- [ ] {test case the phase must pass}
- [ ] {edge case}

## Success Criteria
- [ ] {observable - runs, returns X, no regression in Y}

## Verify
`{one command that proves this phase works - e.g. `npm test -- rate-limit`, `curl -s localhost:3000/health | jq .ok`}`
<!-- The deterministic check cook runs at Step C. A command, not a checkbox. -->

## Risks
- {risk} → {mitigation}
```

`--tdd` mode: the **Tests** section moves to the top (above Steps), and Step 1 of every phase is "Write the failing tests listed below."

`--quick` mode: single `plan.md` file. Phases become bullet sections inside the same file. No separate phase files.

## Phase 5 - Hand off

After writing files, in your reply:

1. **List the files written** as clickable absolute links (`[plan.md](/absolute/path/to/plan.md)`, plus a `file://` URI when helpful). Never list only basenames.
2. **Show the phases table** verbatim from `plan.md` so the user sees the shape without opening it.
3. **Recommend the next action:**
   - For implementation: `vd:cook {plan-dir}` or "I can implement Phase 1 - say go."
   - For more rigor: "Run `--deep` mode with red-team review + independent audit?"
   - For default mode: "Run `vd:plan --audit` for independent verification before execution (recommended)."
4. **For `--deep` runs:** mention the audit step - "Audit ran automatically. Findings: {summary}. See report: {path}. Address CRITICAL findings before `vd:cook`."
5. **Ask if anything's missing.** Don't claim done until the user confirms the shape is right.

## Phase 6 - Red-team review (`--deep` only)

After writing the plan, before declaring done, ask the plan three hostile questions in your reply and answer them honestly:

| Persona | Question |
|---|---|
| **Skeptical reviewer** | "What does this plan assume that isn't true?" |
| **On-call engineer** | "What page do I get at 3am when this ships?" |
| **Future maintainer** | "What will I curse you for in 6 months?" |

If any answer reveals a real problem → revise the plan and note the change in `plan.md` under a `## Revisions` section. Don't hide the iteration.

## Phase 7 - Independent audit (`--deep` only)

After the red-team round, run `--audit` on this plan dir (see [`references/audit.md`](references/audit.md)). Same-context red-team is not a substitute. `--deep` is not done until both Phase 6 and Phase 7 have run.

- Trigger: only when `--deep` is set. Default and `--quick` skip this. Standalone `--audit` is the same pass without writing a new plan.
- Surface result inline: top-3 findings + path to the audit report.
- Audit findings are **advisory** - never block plan completion. The author owns the call.
- If the audit returns CRITICAL findings, recommend revising the plan before handoff to `vd:cook`.

## Anti-staleness

Plans outlive the session that wrote them. Do not cache a file inventory that will rot.

- Point at the live environment: "the handlers next to `src/http/`", not a pasted 20-file list copied from today's tree.
- Name **Create** / **Modify** / **Delete** paths that this phase will actually touch. Those are commitments, not a repo dump.
- If a path may move, write the discovery command (`rg -l 'type Handler'`) instead of a guess.
- `--audit` is how a later session checks the plan against the tree as it is now.

## Specials

- **Migrations / schema changes** - phase 1 is always the migration with rollback path; later phases assume the migration applied. Do not interleave migration steps with feature steps.
- **API breaking changes** - sequence as: add new (phase A) → migrate callers (phase B) → remove old (phase C). Never do all three in one phase.
- **Performance work** - phase 1 captures baseline numbers (against success criteria). Without baseline, "faster" is unfalsifiable.
- **Refactors** - `--tdd` is mandatory. No tests = no safety net = no refactor plan, just hope.
- **Bug fixes** - `--quick` mode is usually right. If the fix needs 3+ phases, the bug is a redesign in disguise - escalate to `vd:brainstorm`.
- **Library upgrades** - every phase ends with "tests pass + manual smoke test of {feature touched}." Don't lump the smoke tests into a final QA phase.
