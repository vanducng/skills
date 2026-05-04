---
name: cook
description: "Execute a plan (or a small task) phase-by-phase: implement → verify → test → review → update status. Use after `vd:plan` to ship the plan, or directly for tight tasks (`--quick`). Default stops at review gates between phases; pass `--auto` to run straight through, `--quick` for sub-plan tasks, `--tdd` for tests-first."
license: MIT
argument-hint: "[plan-dir | plan.md | task] [--auto | --quick] [--tdd] [--no-test]"
metadata:
  author: vanducng
  version: "1.0.0"
---

# Cook

## What this skill is — and isn't

| Skill | Question it answers | Output |
|---|---|---|
| `vd:brainstorm` | "How should I approach this?" | Decision brief |
| `vd:plan` | "Given the approach, what are the steps?" | Phased plan |
| **`vd:cook`** | **"Execute the plan — turn the spec into code."** | **Code changes, tests passing, plan status updated** |

Cook **implements**. It does not design. If during cooking you find the plan is wrong, **stop** and kick back to `vd:plan` (or `vd:brainstorm` if the approach itself is wrong) — don't silently redesign while typing.

## Hard rules

1. **One phase at a time.** Don't start phase N+1 until phase N's success criteria pass. Skipping phases is how plans rot into unreviewable PRs.
2. **No new design decisions in code.** If a step says "add JWT validation" and you find that requires a library choice the plan didn't make → stop, ask, or kick back to plan. Don't pick the library silently.
3. **Compile/type-check after every file.** Not at the end of the phase. Catching the error one file later is 10× cheaper than 5 files later.
4. **Tests pass before review.** Failing tests at review time are a process failure — fix tests first, then ask for review.
5. **Plan status reflects reality.** After each phase, update `plan.md` and the phase frontmatter to match what actually happened. Stale status across a long cook session is the most common silent failure.
6. **Subagent for review.** Self-reviewing your own implementation catches ~30% of what an outside reviewer catches. Delegate review through the `Agent` tool (subagent) at minimum once per phase before marking it done.

## Modes

| Mode | When | Behavior |
|---|---|---|
| `--quick` | Tight scope, no plan exists, single-file change | Skip plan-loading; treat task as a single phase. Still verify + test before done. |
| **default** | Standard execution of an existing plan | Phase loop with **review gate** between phases — user confirms before next phase starts |
| `--auto` | Plan is solid, user trusts the loop, end-to-end run | No review gates; run all phases continuously. Stops only on test failure or compile error. |

Composable flags:

| Flag | Effect |
|---|---|
| `--tdd` | Step 1 of every phase is "write the tests from the phase's Tests section as failing tests." Implementation comes after. |
| `--no-test` | Skip the test step. Use only for docs/config-only changes. Loud warning to user. |

Detect mode from the argument shape (path → plan loop, free text → quick) and explicit flags. Announce mode in your first reply.

## Phase 1 — Load

### If input is a path to a plan

- Read `plan.md` and **all** `phase-XX-*.md` files
- Read referenced docs (`docs/code-standards.md`, etc. if present)
- Identify the **next pending phase** — first phase with `status: pending` (or in-progress, to resume)
- Echo the phases table from `plan.md` to the user so they see the shape before you start

### If input is a free-text task (`--quick`)

- Restate the task in one sentence
- Sketch the change in 3–5 lines (files touched, behavior change)
- **Ask for confirmation** before editing if the change touches >1 file or >50 LOC. The cheapest correction happens before any edit.

### Sanity check (mandatory before any code edit)

If any of these are true → stop and ask:

- The plan references files that don't exist
- A phase requires an external service / API key not configured
- The plan's success criteria reference a tool/script that doesn't exist
- Phase order violates a dependency you can see (phase 3 imports something phase 5 creates)

These failures are cheaper to surface now than to discover halfway through.

## Phase 2 — Cook the loop

For each phase, in order, run this loop. Do not parallelize phases (parallelizing **within** a phase is fine if the steps are genuinely independent).

### Step A — Conform

Before writing code, scan the files the phase will touch and confirm:

- **Naming + import + error-handling style** matches what's already there
- **Existing helpers** — don't recreate. If `utils/foo.ts` already does 80% of what you need, extend it; don't write `utils/foo-v2.ts`
- **Interface contracts** — new code extends existing surfaces, not parallel ones
- **Docs** — if the repo has `docs/code-standards.md` or similar, read the parts relevant to this phase

If the phase plan and the actual codebase disagree (e.g. plan says "add to file X" but X has been moved), **stop and reconcile** before editing. Don't paper over with assumptions.

### Step B — Implement

- Edit one file at a time
- After each file: **compile / type-check / lint** the relevant target. Fail fast.
- After each file: re-read the diff. Catch obvious bugs while the context is hot.
- If a step grows beyond the phase's scope (you find yourself touching files not listed in the phase) → **stop**. Either the phase is wrong, or you're scope-creeping. Decide explicitly, don't drift.

`--tdd` mode: Step B opens with writing the tests from the phase's `Tests` section as **failing tests** before any implementation. The failing tests prove the implementation actually does something.

### Step C — Verify

After all files in the phase are written:

- Run the project's full type-check / lint (not just per-file)
- Run any smoke command the phase implies (start dev server, run script, hit endpoint)
- Walk through each item in the phase's `Success Criteria` and confirm — with evidence, not vibes ("ran `curl /api/foo` → got 200, body matches")

If a success criterion fails: fix it inside this phase. Do not move on with a checkbox unticked.

### Step D — Test

- Spawn a subagent for testing — `Agent(subagent_type="general-purpose", description="Run test suite", prompt="Run [test command], report pass/fail counts and failure details. Do not modify code.")`. Or use a project-specific tester agent if one exists.
- 100% pass required (unless `--no-test`)
- On failure: read the failure carefully → fix → re-run. Don't change the test to make it pass unless the test was provably wrong (and document that in the phase notes).

### Step E — Review

- Spawn a code-review subagent — `Agent(subagent_type="code-reviewer", description="Review phase N changes", prompt="Review the diff for phase N at [plan-path]. Files touched: [list]. Check for: bugs, missed edge cases, security issues, style mismatch, broken contracts.")`. If the project has no code-reviewer agent, use `general-purpose` with the same prompt.
- Apply critical fixes inline before declaring the phase done
- Defer non-critical suggestions to a follow-up section in the phase's notes — don't let polish requests stall the phase

### Step F — Update status

- Set the phase's frontmatter `status: completed`
- Update `plan.md`'s phases table for this phase
- Tick all phase-level success criteria checkboxes
- If any criteria is unmet but acceptable (e.g. user explicitly deferred), note it inline; don't tick it

### Step G — Gate (default mode only)

Stop. Show the user:

- ✓ Phase N complete: {one-line summary}
- Files touched: {list}
- Test result: {pass/fail counts}
- Review result: {one-line gist}
- Next: Phase N+1 ({title}) — proceed?

Wait for confirmation. `--auto` skips this gate and proceeds directly to phase N+1.

## Phase 3 — Finalize

After the last phase passes:

1. **Plan-wide reconcile** — sweep all phase files; tick any stale unchecked items that did get done; sync `plan.md` status (`pending` → `completed`).
2. **Docs** — if changes warrant docs updates (new public APIs, changed behavior, new env vars, new commands) → update `docs/` directly. If not, say so explicitly: "Docs impact: none."
3. **Smoke** — one final end-to-end check. Run the most user-facing command this plan changed (start the app, run the CLI, hit the endpoint).
4. **Hand off** — ask the user:
   - Commit? (suggest a conventional-commit message based on the plan title)
   - Open a PR? (if on a feature branch)
   - Anything missing? (don't claim done unilaterally)

## Anti-rationalization

| Excuse | Reality |
|---|---|
| "I'll skip the conformance check, the codebase is small" | Small codebases drift fastest. 30 seconds of scanning catches the import-style bug. |
| "The compile passed, no need to re-read the diff" | Compilers don't catch logic. Re-read. |
| "Tests are failing but only flaky ones" | "Flaky" is the first lie before "I disabled the test." Investigate; quarantine if proven flaky, don't ignore. |
| "I'll update plan status at the end" | Long sessions drift. Update after each phase or it never happens. |
| "I'll review my own code, faster" | Self-review misses 30%. Spawn the agent. |
| "The plan is wrong but I can fix it as I go" | That's redesigning while typing. Stop, kick back to `vd:plan`. |
| "User said --auto, I'll skip the smoke check too" | `--auto` skips review gates, not correctness checks. Smoke + tests still required. |

## Quality bar

- **One phase at a time, completed before the next.** No half-done phases at the end of a session.
- **Compile/test/review per phase, not per session.** Bugs caught per phase = 10× cheaper than per session.
- **Plan status accurate.** A reader can open `plan.md` mid-cook and see truthful state.
- **No silent design.** Every decision the plan didn't make either gets surfaced or written into the plan.
- **Subagent-reviewed.** Every phase's diff is reviewed by an outside agent before declaring done.
- **Honest finalize.** Docs impact stated explicitly; commit message reflects what shipped.

## Specials

- **Migrations** — phase A (migration) must include a tested rollback path before phase B (consumers) starts. If rollback is untested, you don't have a migration phase, you have a hope phase.
- **API breaking changes** — verify all callers compile/run after each step. If the plan ordered "add new → migrate callers → remove old" correctly, this should be smooth; if you can't add new without breaking old, the plan is wrong → kick back.
- **Performance work** — Step C (Verify) must compare against the baseline numbers from the plan. "Faster" without numbers is unfalsifiable.
- **Refactors with `--tdd`** — Step B's failing tests document **current** behavior. After implementation, all tests must still pass. A green test that wasn't green before is suspicious — investigate, don't celebrate.
- **UI work** — Step C must include manual browser verification, not just type-check. Type errors and visual bugs are orthogonal categories.
- **Library upgrades** — every phase ends with a smoke test of one feature touched by the upgraded library. Don't lump smoke tests into a final QA phase.
- **Bug fixes** (`--quick` mode) — write the test that reproduces the bug *first*, watch it fail, then fix. Without the failing test you have no proof the bug existed.

## Output rules

1. Announce mode (default / `--auto` / `--quick`) and `--tdd` / `--no-test` if set in your first reply.
2. Phase 1 (load + sanity check) happens visibly — list the phases or restate the task before any edit.
3. Per-phase log: `✓ Phase N: {title} — files: {n}, tests: {x/y pass}, review: {gist}`. Concise, scannable.
4. Default mode stops at Step G (gate) between phases. Do not start phase N+1 without confirmation.
5. `--auto` runs straight through unless tests fail, compile fails, or sanity check trips.
6. Plan status is updated **after each phase**, not at the end.
7. Finalize phase explicitly states docs impact (`none | minor | major`) and asks before committing.

## Workflow position

**Typically follows:** `vd:plan` (execute the plan), `vd:brainstorm` → `vd:plan` chain (after design)
**Typically precedes:** code review, PR open, deploy
**Compares to:** `/ck:fix` (alternative for narrow bug fixes — `--quick` mode covers similar ground)
**Kick-back triggers:** if the plan is wrong → `vd:plan`; if the approach is wrong → `vd:brainstorm`. Do not redesign in cook.
