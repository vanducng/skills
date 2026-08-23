---
name: ultracook
description: "Open workflow conductor. Classifies a coding task and runs the smallest viable path - direct, a pipeline of named skills with checkable done-when gates, or parallel fan-out - then resumes from on-disk state. Use when the user types ultracook, asks to orchestrate, run the whole pipeline, drive a feature or fix end-to-end, or split work across agents. Composes vd: skills by name; does not reimplement them."
license: MIT
argument-hint: "[<short goal> | resume | status | kill --reason <text>] [--manual | --semi | --auto]"
metadata:
  author: vanducng
  version: "1.0.0"
---

# Ultracook - open conductor

`vd:ultracook` classifies a task and runs the smallest workflow that can prove the result. It composes existing skills **by name**. Planning rigor lives in `vd:plan`, execution in `vd:cook`, landing in `vd:ship`. This skill is a map, not a cage.

The one-session spine is **interview → brainstorm → plan → cook → ship**. Run only the slice the task earns. If the deciding will not fit one session, stop and run `vd:interview --wayfinder` before opening a pipeline.

## What this skill is - and isn't

| Skill | Question it answers | Horizon |
|---|---|---|
| `vd:interview` | "What do you actually want?" | One session |
| `vd:brainstorm` | "How should I approach this?" | One session |
| `vd:plan` | "What are the build steps?" | One plan, phases sized to one session |
| `vd:cook` | "Execute the plan." | One plan |
| **`vd:ultracook`** | **"Drive a decided goal through the smallest skill path that proves it."** | **One goal, one pipeline** |
| `vd:auto-loop` | "Keep iterating this one command until the gate." | One loop |

## Quick reference

| Form | Action |
|---|---|
| `vd:ultracook "<goal>"` | Classify, write `state.json`, run stages |
| `vd:ultracook` (no args) | Resume: list-and-pick if several in-progress; else first unfinished stage |
| `vd:ultracook status [--all]` | `scripts/status.sh` |
| `vd:ultracook kill --reason "<text>"` | `scripts/kill.sh` - refuses to overwrite a terminal state |

Flags: `--manual` / `--semi` (default) / `--auto`. `--reuse` skips a fresh worktree.

## Hard rules

1. **Compose by name.** Each stage is a skill id plus a checkable `done_when`. Never reimplement `vd:plan`, `vd:cook`, `vd:ship`, `vd:interview`, or `vd:brainstorm` here.
2. **State on disk is source of truth.** One `state.json` (schema v2 - [`references/state.md`](references/state.md)) per goal. Resume is the first stage that is neither `done` nor `skipped`.
3. **List-and-pick.** Several in-progress goals: print them and ask. Do not silently take the newest.
4. **Loop primitive = `vd:auto-loop`.** Use it for cook/verify iteration. Not a home-grown retry loop.
5. **No auto-merge on this skills repo.** `vd:ship official` without `--auto`.
6. **Hard caps.** Global 30 iterations; 3 rebases; 2 CI reruns; same-signature failure 3 times → `blocked`. Prompt back at ~80% context.
7. **Hard gates always ask** (even in `auto`): delete, deploy, migration, secrets, broad codemod, expensive fan-out. See [`references/conductor.md`](references/conductor.md).
8. **Feature-first repos - claim a feature at intake.** If the hook context shows `Feature: none`, run `workbench new <slug>` once so artifacts land in `features/<slug>/`.
9. **Observability stays in scope.** Behavior-changing code should expose stable structured fields, reason codes, and short human reasons. No secrets or large prompt/diff payloads in logs.
10. **Decision log on autonomous stretches.** Append one row per decision to `{goal-dir}/decisions.tsv`: `ts	phase	decision	why	evidence	result`. Evidence is a pointer (commit SHA, `file:line`), never prose.

## Classify, then run

Full heuristics: [`references/conductor.md`](references/conductor.md). Short form:

| Mode | Pick when | What runs |
|---|---|---|
| `direct` | trivial, clear, single-surface, reversible | Do it inline. **No goal-dir.** Narrowest check, report. Prefer `vd:cook --quick` or `vd:fix`. |
| `pipeline` | real feature/fix, phases, uncertainty, blast radius | `state.json` stages → invoke each skill → `vd:auto-loop` when a stage must iterate → verify `done_when` |
| `fan-out` | repo-wide / migration / N-finder, independent packets | Parallel packets via the host's native primitive; parent owns integration |

Want unclear + `--auto` / non-interactive: **block**. Do not invent intent.

Autonomy (`manual` / `semi` / `auto`): [`references/autonomy-modes.md`](references/autonomy-modes.md). `semi` gates the first `vd:plan`, `vd:ship`, and the final `done_when`. After a gate clears, do not re-gate except on exceptions (unrelated test failure, merge conflict, non-auto-fixable error).

## Pipeline stages

A pipeline is an open list. Write the stages the task earns - skip the rest.

```json
{
  "id": "plan",
  "skill": "vd:plan",
  "done_when": "plan.md exists with phases and a Definition of Done block",
  "status": "pending"
}
```

Typical slices (propose in `semi`, stand in `auto`):

| Shape | Stages |
|---|---|
| interview-first | `vd:interview` → (`vd:brainstorm` or `vd:plan`) → `vd:cook` → `vd:ship` |
| brainstorm-first | `vd:brainstorm` → `vd:plan` → `vd:cook` → `vd:ship` |
| plan-only | `vd:plan` |
| fix-and-ship | `vd:cook` (or `vd:fix`) → `vd:ship` |
| refactor | `vd:plan` → `vd:cook` → `vd:code-review --refactor` |

`done_when` must be checkable ("tests pass via `npm test`", "PR url recorded"). Never "proceed if confident".

When a stage is underspecified, invoke `vd:interview --grill` on that decision, record the answer, continue. Do not grow a closed action vocabulary to cover the case.

Cook already owns verify and test. There is no `vd:test` skill.

## Resume and kill

1. Load `state.json`.
2. If `terminal` is set, print status and stop.
3. Resume the first stage whose status is not `done` or `skipped`.
4. After a stage's `done_when` holds, patch that stage to `done` with evidence via `scripts/update-state.sh`.
5. When every stage is `done` or `skipped`, set `terminal=done`.

`kill --reason` calls `scripts/kill.sh`. It refuses to clobber `done` / `blocked` / `abandoned`. It does not write a cancel sentinel; if the goal was handed to `vd:auto-loop`, cancel that loop with `vd:auto-loop --cancel`.

## Fan-out

Decompose into narrow packets with **disjoint write scope**. Parent reads each result, checks claimed edits against source and tests, then verifies. Packet shapes and the compete-then-graft arena live in [`references/conductor.md`](references/conductor.md).

## State location

`$VD_STATE_PATH` (exclusive when set) → `<git-root>/.workbench/state` when `.workbench/` exists → `$XDG_STATE_HOME/vd/ultracook/<repo-id>/goals`. Legacy `plans/goals` is read-only for old runs. Do not write new state into the project tree unless the repo opted into `.workbench`.

## Workflow position

**Typically follows:** a goal the user wants driven, not one skill at a time
**Composes:** `vd:interview` (want / `--grill` / `--wayfinder`), `vd:brainstorm`, `vd:plan`, `vd:cook`, `vd:fix`, `vd:code-review`, `vd:ship`, `vd:auto-loop`, `vd:worktree`, `vd:workbench`
**Typically precedes:** nothing - it is the wrapper. After a cleared wayfinder chunk, it may drive that chunk's plan → cook → ship.
