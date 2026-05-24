---
name: cook
description: "Execute a plan (or a small task) phase-by-phase: implement → verify → test → review → update status. Use after `/vd:plan` to ship the plan, or directly for tight tasks (`--quick`). Default stops at review gates between phases; pass `--auto` to run straight through, `--quick` for sub-plan tasks, `--tdd` for tests-first."
license: MIT
argument-hint: "[plan-dir | plan.md | task] [--auto | --quick] [--tdd] [--no-test]"
metadata:
  author: vanducng
  version: "1.1.0"
---

# Cook

## What this skill is — and isn't

| Skill | Question it answers | Output |
|---|---|---|
| `/vd:brainstorm` | "How should I approach this?" | Decision brief |
| `/vd:plan` | "Given the approach, what are the steps?" | Phased plan |
| **`/vd:cook`** | **"Execute the plan — turn the spec into code."** | **Code changes, tests passing, plan status updated** |

Cook **implements**. It does not design. If during cooking you find the plan is wrong, **stop** and kick back to `/vd:plan` (or `/vd:brainstorm` if the approach itself is wrong) — don't silently redesign while typing.

## Hard rules

1. **One phase at a time.** Don't start phase N+1 until phase N's success criteria pass.
2. **No new design decisions in code.** If a step requires a choice the plan didn't make → stop and ask. Don't pick silently.
3. **Compile/type-check after every file**, not at end of phase. Fail fast.
4. **Tests pass before review.** Don't ask for review with red tests.
5. **Plan status reflects reality** — update phase frontmatter and `plan.md` after each phase, never at the end.
6. **Outside review per phase.** Spawn a subagent reviewer at least once before declaring a phase done; self-review is not enough.

## Modes

| Mode | When | Behavior |
|---|---|---|
| `--quick` | Tight scope, no plan exists, single-file change | Skip plan-loading; treat task as a single phase. Still verify + test before done. |
| **default** | Standard execution of an existing plan | Phase loop with **review gate** between phases — user confirms before next phase starts |
| `--auto` | Plan is solid, user trusts the loop, end-to-end run | No review gates; run all phases continuously. Stops only on test failure or compile error. |

Composable flags:

| Flag | Effect |
|---|---|
| `--tdd` | Step B of every phase opens with writing the phase's `Tests` as failing tests. Implementation comes after. |
| `--no-test` | Skip the test step. Docs/config-only changes. Warn the user loudly. |
| `--skip-preflight` | Skip Step 0. Use when audit already ran or you trust the plan against current codebase. |

Detect mode from the argument shape (path → plan loop, free text → quick) and explicit flags. Announce mode + flags in your first reply.

## Pragmatism rules (apply during every Step B)

YAGNI > KISS > DRY when they conflict. Ship-first wins. These rules turn "good engineering" into "good engineering for *this* PR."

1. **Rule of Three before abstracting.** Tolerate duplication through the 2nd occurrence. Refactor on the 3rd, or earlier only if both call-sites are converging in this same PR. Sandi Metz: *"Duplication is far cheaper than the wrong abstraction."*
2. **No speculative generality.** If the plan says "single user," don't add multi-tenant hooks because "we might want it later." YAGNI applies to features, not to readability — invest in clear names and test coverage, never in imagined extensibility.
3. **Inline > one-liner helpers.** Don't extract a private function that's called once and adds no clarity. AI agents tend to over-modularize; resist it.
4. **No throwaway comments.** Delete commented-out code on sight. Do **not** write:
   - `// TODO: refactor later`, `// FIXME`, `// HACK` without an owner + ticket
   - `// added for issue #123`, `// new in v2`, `// removed X`
   - Trivial restatements of the code (`// increment counter`)

   Comments earn their keep by explaining **why**: a non-obvious constraint, a workaround for a known bug, a domain rule the code can't express. If a future reader could deduce it from the code, delete the comment.
5. **MVP / POC / spike bias.** If the plan declares itself MVP / POC / spike, prefer shipping working code over elegant code. Skip optimizations, skip micro-abstractions, accept short variable names in narrow scopes. Refactoring debt goes in the post-launch backlog, **not** in a `// TODO` in the source.

When unsure between two paths, pick the one a reviewer can delete or rewrite in 10 minutes.

## Phase 1 — Load

### If input is a path to a plan

- Read `plan.md` and all `phase-XX-*.md` files
- Read referenced docs (`docs/code-standards.md`, etc.)
- Identify the next pending phase
- Echo the phases table so the user sees the shape before edits begin

### If input is a free-text task (`--quick`)

- Restate the task in one sentence
- Sketch the change in 3–5 lines (files touched, behavior change)
- **Ask for confirmation** before editing if the change touches >1 file or >50 LOC

### Sanity check (mandatory before any code edit)

Stop and ask if:

- Plan references files that don't exist
- A phase requires a service / API key not configured
- Success criteria reference a tool or script that doesn't exist
- Phase order violates a visible dependency (phase 3 imports what phase 5 creates)

## Phase 2 — Cook the loop

For each phase, in order. Don't parallelize phases; parallel work **within** a phase is fine when steps are genuinely independent.

### Step 0 — Pre-flight (mechanical)

Validate the phase's mechanical assumptions against the live codebase. Fast local check, no subagents.

- **`**Modify:**` paths** — verify each file exists. Missing → halt.
- **`**Delete:**` paths** — verify each file exists. Already gone → no-op, continue.
- **`**Create:**` paths** — verify each file does NOT exist. Already there → halt (potential overwrite).
- **Install steps** — if the phase says `npm install X` etc. and a manifest exists, best-effort check the package isn't already installed at a conflicting version. Don't block on uncertainty.

**On halt:** print `Pre-flight failed for phase {N}: {reason}. Plan written {age} ago; codebase may have drifted.` Offer:
1. Skip preflight and proceed (user accepts risk)
2. Revise the phase manually then resume
3. Abort cook

Don't auto-fix the plan — user owns the decision. Pre-flight is mechanical, not logical: ordering / dependency / success-criteria realism is `/vd:plan-audit`'s job. `--skip-preflight` bypasses Step 0 entirely.

### Step A — Conform

Before writing code, scan the target files and confirm:

- Naming + import + error-handling style matches what's there
- Existing helpers — extend, don't fork (`utils/foo-v2.ts` is a smell)
- New code extends existing interfaces, not parallel ones
- Read the relevant parts of `docs/code-standards.md` if present

If the plan and the codebase disagree (e.g. plan says "add to file X" but X has been moved), stop and reconcile before editing.

### Step B — Implement

- Edit one file at a time. Apply the **Pragmatism rules** above.
- After each file: compile / type-check / lint the relevant target.
- After each file: re-read the diff. Compilers don't catch logic.
- If a step grows beyond the phase's scope (files not listed in the phase get touched) → stop and decide explicitly. Don't scope-drift.

`--tdd`: Step B opens with writing the phase's `Tests` section as failing tests, then implementing.

### Step C — Verify

After all files for the phase are written:

- Run the full type-check / lint (not just per-file)
- Run any smoke command the phase implies (start dev server, hit endpoint, run script)
- Walk each item in the phase's `Success Criteria` and confirm with evidence, not vibes (`curl /api/foo → 200, body matches`)

If a success criterion fails: fix inside this phase. Don't tick it and move on.

### Step D — Test

- Spawn a subagent for testing: `Agent(subagent_type="general-purpose", description="Run test suite", prompt="Run [test command], report pass/fail counts and failure details. Do not modify code.")`. Use a project-specific tester agent if one exists.
- 100% pass required (unless `--no-test`).
- On failure: read carefully → fix → re-run. Don't edit the test to make it pass unless it was provably wrong (document the why).

### Step E — Review

- Spawn a reviewer subagent: `Agent(subagent_type="code-reviewer", description="Review phase N changes", prompt="Review the diff for phase N at [plan-path]. Files touched: [list]. Check for: bugs, missed edge cases, security issues, style mismatch, broken contracts, premature abstractions, throwaway comments.")`. Fallback to `general-purpose` if no code-reviewer agent.
- Apply critical fixes inline before declaring the phase done.
- Defer non-critical polish to a follow-up section in the phase's notes — don't let suggestions stall the phase.

### Step F — Update status

- Set phase frontmatter `status: completed`
- Update `plan.md`'s phases table
- Tick all phase-level success criteria checkboxes
- If a criterion is unmet but acceptable (e.g. user explicitly deferred), note it inline; don't tick it

### Step G — Gate (default mode only)

Stop. Show the user:

- ✓ Phase N complete: {one-line summary}
- Files touched: {list}
- Test result: {pass/fail counts}
- Review result: {one-line gist}
- Next: Phase N+1 ({title}) — proceed?

Wait for confirmation. `--auto` skips this gate.

## Phase 3 — Finalize

After the last phase passes:

1. **Reconcile** — sweep all phase files; tick stale unchecked items that did get done; sync `plan.md` (`pending` → `completed`).
2. **Docs** — if changes warrant updates (new public APIs, changed behavior, new env vars, new commands) → update `docs/` directly. Otherwise say so: "Docs impact: none."
3. **Smoke** — one final end-to-end check. Run the most user-facing command this plan changed.
4. **Hand off** — ask the user:
   - Commit? (suggest a conventional-commit message)
   - Open a PR? (if on a feature branch)
   - Anything missing? Don't claim done unilaterally.

## Anti-rationalization

| Excuse | Reality |
|---|---|
| "I'll skip conformance, the codebase is small" | Small codebases drift fastest; a quick scan catches the import-style bug. |
| "Compile passed, no need to re-read the diff" | Compilers don't catch logic. Re-read. |
| "Tests are failing but only the flaky ones" | "Flaky" is the first lie before "I disabled it." Investigate; quarantine if proven, don't ignore. |
| "I'll update plan status at the end" | Long sessions drift. Update after each phase or it never happens. |
| "I'll review my own code, faster" | You don't see what you just wrote. Spawn the agent. |
| "The plan is wrong but I can fix it as I go" | That's redesigning while typing. Stop, kick back to `/vd:plan`. |
| "It's only a POC, I'll add a TODO comment" | TODOs without owner + ticket become permanent. Either fix now or open an issue. |
| "These two functions are similar; I'll extract a helper" | Two is not three. Wait — or invite the wrong abstraction. |
| "It's MVP, I'll skip the test too" | MVP bias means skip *polish*, not skip *proof it works*. Tests stay. |
| "User said --auto, I'll skip the smoke check too" | `--auto` skips review gates, not correctness checks. Smoke + tests still required. |

## Specials

- **Migrations** — phase A (migration) must include a tested rollback path before phase B (consumers) starts. Untested rollback = hope, not migration.
- **API breaking changes** — verify all callers compile/run after each step. If you can't add new without breaking old, the plan is wrong → kick back.
- **Performance work** — Step C must compare against baseline numbers from the plan. "Faster" without numbers is unfalsifiable.
- **Refactors with `--tdd`** — Step B's failing tests document **current** behavior. After implementation, all tests must still pass. A new green that wasn't green before is suspicious — investigate, don't celebrate.
- **UI work** — Step C must include manual browser verification. Type errors and visual bugs are orthogonal.
- **Library upgrades** — every phase ends with a smoke of one feature touched by the upgraded library. Don't lump smokes into a final QA phase.
- **Bug fixes** (`--quick`) — write the test that reproduces the bug *first*, watch it fail, then fix. Without the failing test you have no proof the bug existed.

## Workflow position

**Typically follows:** `/vd:plan` (execute the plan), `/vd:brainstorm` → `/vd:plan` chain
**Typically precedes:** code review, PR open, deploy
**Compares to:** `/vd:fix` (narrow bug fixes — `--quick` covers similar ground)
**Kick-back triggers:** plan is wrong → `/vd:plan`; approach is wrong → `/vd:brainstorm`. Do not redesign in cook.
