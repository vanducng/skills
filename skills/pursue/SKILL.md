---
name: pursue
description: "Goal-driven workflow orchestrator. Intake → worktree → plan → cook → ship → verify. Delegates iteration to `vd:auto-loop`. Use to drive a feature/fix from short-goal prompt to verified deployment with hard guardrails and resume-across-compaction."
license: MIT
argument-hint: "<short goal> [--reuse] [--manual | --semi | --auto] | status | kill --reason <text> | resolve <goal-dir>"
metadata:
  author: vanducng
  version: "0.1.0"
---

# Pursue

## What this skill is — and isn't

| Skill | Question it answers | Output |
|---|---|---|
| `/vd:plan` | "What are the steps?" | Phased plan |
| `/vd:cook` | "Execute the plan." | Code changes |
| `/vd:ship` | "Land the branch." | Merged target |
| `/vd:auto-loop` | "Drive to a verifier until passing." | Verified completion |
| **`/vd:pursue`** | **"Drive a goal end-to-end: intake → plan → cook → ship → verify, until done."** | **Verified deployment or graceful block** |

Pursue **orchestrates the whole workflow**. It does not design (use `/vd:brainstorm`/`/vd:plan` first) and it does not run the inner iteration itself — when an action has a verifier defined, pursue delegates to `/vd:auto-loop` and resumes when auto-loop terminates.

## Hard rules

1. **State on disk is source of truth.** `plans/goals/{slug}/goal.yaml` + `state.json` + `iterations/NNN-*.md` survive context compaction. Re-invoking `/vd:pursue` reads them and resumes; never trust in-memory cache across sessions.
2. **Loop primitive = `vd:auto-loop` (Stop hook).** Do NOT use `ScheduleWakeup` for iteration. `Monitor` is only for event-driven async waits (CI, image build, rollout).
3. **No auto-merge on the skills repo.** `vd:ship official` (no `--auto`). User merges main manually.
4. **Closed-set verifier vocabulary + `shell` escape.** Six built-ins: `ci_green`, `pod_image_matches`, `http_status`, `cmd_exits_zero`, `test_suite_passes`, `manual_confirm`. Plus `shell` for everything else.
5. **Two verifier layers.** Per-action verifiers (run iteration-time during cook) come from `action-vocab`. Workflow-level verifiers in `goal.yaml.target.verifiers` run only at the dedicated `verify_*` phase. Never mix them.
6. **Hard guardrails.** Global iter cap (default 30); per-phase retry caps (3 rebases, 2 CI reruns); same-signature failure recognizer (same fail 3× → `blocked`); token-cap prompt-back at 80%.
7. **Composes existing `vd:*` skills.** Never reimplements them.

## Modes (autonomy)

| Mode | Behaviour | Default? |
|---|---|---|
| `--manual` | Every action gated via `AskUserQuestion`. Use while debugging the skill. | No |
| `--semi` | Gates only at high-blast-radius transitions (first `plan`, `ship`, final `verify_*`). | **Yes** |
| `--auto` | No gates. Stops only on `done` / `blocked` / `abandoned` terminal state, or budget exhaustion. | No |

Mode is set at intake time (`goal.yaml.autonomy`) and can be edited in-place mid-flight; executor re-reads goal.yaml each iteration.

## Arguments

| Form | Meaning |
|---|---|
| `<short goal>` (positional) | Trigger intake. Creates `plans/goals/{date}-{slug}/`. |
| `--reuse` | Skip worktree creation; write goal artifacts into the current repo. |
| `--manual` / `--semi` / `--auto` | Set autonomy at intake (overrides goal.yaml on first run). |
| `resolve <goal-dir>` | Dry-run: print the resolved workflow (Phase 2). |
| `status` | Read state.json + last journal entry; print human summary (Phase 6). |
| `kill --reason "<text>"` | Write `terminal=abandoned`; if mid-delegation, also cancel auto-loop (Phase 6). |

## Phase 1 — Intake (this file's scope)

`/vd:pursue "<short goal>"` runs:

1. Up to 4 `AskUserQuestion` prompts (see `references/intake-template.md`):
   - target kind (local / pr-only / cluster)
   - action shape (brainstorm-first / plan-only / fix-and-ship / refactor)
   - branch name (suggested from slug; skip when `--reuse`)
   - autonomy (manual / semi / auto; default semi)
2. Computes slug from short goal (kebab-case, max 40 chars).
3. Optionally creates a worktree: `git worktree add ../{repo}-{slug} -b {branch}` (skip if `--reuse`).
4. Writes `plans/goals/{date}-{slug}/goal.yaml` + `state.json` (terminal=null, current_phase=intake-complete).
5. Prints the goal-dir path so the next step (Phase 2 `resolve`) can chain.

**Implementation:** `scripts/init-goal.sh` is called from this SKILL.md after the 4 `AskUserQuestion` prompts populate env vars (`PURSUE_TARGET_KIND`, `PURSUE_ACTION_SHAPE`, `PURSUE_BRANCH`, `PURSUE_AUTONOMY`, `PURSUE_REUSE_WORKTREE`). The script handles slug derivation, worktree creation, and file writes. **`AskUserQuestion` cannot be called from bash** — it must be invoked from this SKILL.md and the answers passed to the script via env vars. See `references/architecture.md` for the two-layer pattern.

## Schemas

- `references/goal-schema.md` — `goal.yaml` shape (v1)
- `references/state-schema.md` — `state.json` shape (v1) + atomic write protocol
- `references/intake-template.md` — the 4 intake questions + answer-to-goal.yaml mapping
- `references/architecture.md` — two-layer SKILL.md ↔ bash-script invariant

## Sub-verbs (Phase 6 ships these)

Phase 1 stubs `status` and `kill` to print "not yet implemented (Phase 6)" — they fail gracefully but don't write state.

## Workflow position

**Typically follows:** a short intent ("ship X to staging and verify").
**Typically composes:** `/vd:scout`, `/vd:brainstorm`, `/vd:plan`, `/vd:plan-audit`, `/vd:cook`, `/vd:ship`, `/vd:debug`, `/vd:fix`, `/vd:research`, `/vd:test`, `/vd:docs`, `/vd:journal`, `/vd:worktree`, `/vd:auto-loop`.
**Compares to:** `/vd:cook` (one phase at a time, no e2e drive) and `/vd:auto-loop` (iterate to a verifier, no workflow shape).
