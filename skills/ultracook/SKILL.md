---
name: ultracook
description: "Workflow conductor over the vd: skill stack. Classifies a coding task, picks the smallest viable workflow - direct, pipeline (brainstorm → plan → cook → review → ship), or parallel fan-out - stays interactive until a gate clears, then runs autonomously to verified done, with resumable on-disk state. Use when the user types ultracook / $ultracook, asks to orchestrate, run the whole pipeline, drive a feature/fix/migration end-to-end, or split work across agents."
license: MIT
argument-hint: "[<short goal> | resume | status | kill --reason <text>] [--reuse] [--manual | --semi | --auto]"
metadata:
  author: vanducng
  version: "1.0.0"
---

# Ultracook - workflow conductor

Ultracook is a **map, not a cage**. Given a task it classifies the work, picks the smallest slice of the **brainstorm → plan → cook → review → ship** spine that the task earns, and then runs that flow by invoking the named skills - each stage's discipline lives in the invoked skill, never here. A typo goes `direct` (no machinery); a feature goes `pipeline`; a repo-wide migration goes `fan-out`. Every skill it composes stays independently invokable.

## Quick reference

| Form | Action |
|---|---|
| `vd:ultracook "<goal>"` | New goal - classify → confirm flow → state.json → run stages |
| `vd:ultracook` (no args) | Resume - read the most recent in-progress goal's `state.json`, continue from the first non-done stage |
| `vd:ultracook status [--all]` | One-screen status (`scripts/status.sh <state-base>[/<slug>]`) |
| `vd:ultracook kill --reason "<text>"` | Mark abandoned + drop cancel sentinel (`scripts/kill.sh`) |

Flags: `--reuse` (work in the current checkout instead of a `vd:worktree`), `--manual` / `--semi` (default) / `--auto` (autonomy - see `references/autonomy-modes.md`).

## Step 1 - Classify

Read the goal and pick a **mode** (how much workflow) and an **autonomy** (how often to gate). Full heuristics, gate map, and fan-out packet shapes in [`references/conductor.md`](references/conductor.md); the short form:

| Mode | Pick when | What runs |
|---|---|---|
| `direct` | trivial, clear, single-surface, reversible | do it inline - **no state file** - narrowest useful check, report |
| `pipeline` | real feature/fix, phases, uncertainty, blast radius | compose a stage flow (below), run to terminal |
| `fan-out` | repo-wide / migration / N-finder audit, independent packets | parallel subagents with disjoint write scope; parent owns integration |

`direct` finishes right here - do the task, run the narrowest check, done. If mid-task it turns out bigger than classified, stop and re-enter as `pipeline` (say so).

## Step 2 - Compose the flow (pipeline mode)

Pick the slice of the spine the task needs, as a list of **stages**. Each stage is a skill name plus a checkable **done-when** gate:

| Stage | Skill | Done when |
|---|---|---|
| brainstorm | `vd:brainstorm` (or `--grill` to sharpen an existing idea) | decision brief approved / grilling frontier empty |
| plan | `vd:plan` | plan files written and approved - Plannotator's plan-review hook intercepts the handoff where installed; add `vd:plan --audit` before cook when stakes are high |
| cook | `vd:cook --auto` | all phases completed and the plan's Definition of Done passes (`eval-dod.sh` exit 0) |
| review | `vd:code-review` | review pass with no blocking findings |
| ship | `vd:ship` | PR open and CI green (never auto-merge on this repo) |

Common slices: ambiguous spec → all five; clear fix → `cook → review → ship`; "just plan it" → `plan` only; cross-cutting refactor → `plan → cook → review`. Stages the task doesn't need are skipped, not ceremonially run. Other skills slot in the same way when the goal calls for them (`vd:scout` before plan, `vd:fix` instead of cook for a diagnosed bug, `vd:simplify` after review) - a stage is just a skill name + done-when, there is no fixed vocabulary.

In `semi`/`manual`, show the proposed flow (one line per stage with its done-when) and let the user edit before starting. In `auto`, the proposal stands.

Then initialize state (see [`references/state.md`](references/state.md)):

```bash
bash scripts/update-state.sh init "<state-base>/<slug>" <<'JSON'
{ "goal": "...", "mode": "pipeline", "autonomy": "semi", "stages": [ ... ] }
JSON
```

## Step 3 - Run the flow

For each stage, in order:

1. Mark it `running` (`update-state.sh patch`), then **invoke the stage's skill** and let it drive - ultracook never reimplements a stage inline.
2. **Gate per autonomy mode** (`references/autonomy-modes.md`): `semi` gates the first plan approval, ship, and final verify; `manual` gates every stage; `auto` gates nothing. **Hard gates always ask, even in `auto`** - the list lives in conductor.md (delete/deploy/migrations/secrets/broad codemods/expensive fan-outs).
3. **Check the done-when with evidence**, not vibes. Prefer the skill's own gate (cook's DoD runner, ship's CI watch). Record one line of evidence in the stage entry; mark `done`.
4. **On failure**: update `last_failure_signature` (`stage|command|exit-code`) and retry through the stage skill. Long red→green grinding (cook iterations, CI retries) is delegated to `vd:auto-loop` - it owns the stop-hook loop and its own two-vote done gate; ultracook just reads the outcome. If an underspecified decision surfaces mid-stage, invoke `vd:brainstorm --grill` rather than guessing.
5. When all stages are `done`, set `terminal: done` with a one-line reason. Summarize: stages run, evidence per stage, PR link if shipped.

## Hard rules

1. **State on disk is source of truth.** `<state-base>/<slug>/state.json` (resolution order in `references/state.md`) survives context compaction; resume = read it and continue from the first non-done stage.
2. **Composes existing `vd:*` skills - never reimplements them.** If a stage needs behavior its skill lacks, improve that skill, not this file.
3. **Guardrails on every autonomous run:** iteration cap 30 → `blocked`; 3 identical failure signatures in a row → `blocked` with the signature surfaced; at ~80% context, checkpoint state and prompt back rather than degrading silently.
4. **Once a gate clears, don't re-gate.** Escalate only on exceptions: unrelated test failure, merge conflict, non-auto-fixable structural error, a service down after retries, a never-seen error. This is what prevents approval fatigue.
5. **No auto-merge on the skills repo.** `vd:ship official` (no `--auto`).
6. **Feature-first repos - claim a feature at intake.** If the hook context shows `Feature: none`, run `workbench new <slug>` once so the whole run's artifacts land in `features/<slug>/`. Idempotent; skip when a feature is already active.
7. **Observability stays in scope.** Behavior-changing code keeps log/debug visibility in the acceptance bar: stable structured fields, reason codes, short human reasons; no secrets or unbounded payloads.

## Runtime notes

Ultracook is runtime-agnostic prose: it names skills and shell scripts, nothing host-specific. Use the host's native primitives where a stage needs them - subagents/`Workflow` for fan-out packets on Claude Code, Codex subagents on Codex; `vd:auto-loop` handles the loop primitive per host (Stop hook on Claude Code, `--codex` native `/goal` on Codex). If a primitive is missing, run the stage inline sequentially and say so - degraded, not dead.

## Files

```
references/
  conductor.md       - classification heuristics, gate map, hard-gate list, fan-out packets
  autonomy-modes.md  - manual/semi/auto gate semantics
  state.md           - state.json schema v2 + state-base resolution
scripts/
  update-state.sh    - init/patch state.json (atomic)
  status.sh          - one-line status per goal, stage detail per goal
  kill.sh            - mark abandoned + cancel sentinel
```

## Workflow position

**Composes:** `vd:brainstorm`, `vd:plan` (+ `--audit`), `vd:cook`, `vd:code-review`, `vd:ship`, `vd:scout`, `vd:fix`, `vd:debug`, `vd:simplify`, `vd:docs`, `vd:journal`, `vd:worktree`, `vd:auto-loop`, `vd:optimize-loop`
**Compares to:** invoking the skills by hand (same flow, you gate every step yourself); `vd:auto-loop` (single-goal grinder - ultracook's iteration engine, not a competitor); `vd:codex-workflow` (deterministic scripted steps on Codex when you already know the exact sequence)
