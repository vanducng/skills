---
name: ultracook
description: "Dynamic workflow conductor. Classifies a coding task, picks the smallest viable workflow — direct, pipeline (brainstorm → plan → cook → ship), or parallel fan-out — stays interactive until a gate clears, then runs autonomously to verified done. Dual-runtime (Claude Code + Codex) with on-disk resumable state and hard guardrails. Use when the user types ultracook / $ultracook, asks to orchestrate, run the whole pipeline, drive a feature/fix/migration end-to-end, or split work across agents."
license: MIT
argument-hint: "[<short goal> | resume | status | kill --reason <text> | resolve <goal-dir>] [--reuse] [--manual | --semi | --auto]"
metadata:
  author: vanducng
  version: "0.4.0"
---

# Ultracook — dynamic workflow conductor

`vd:ultracook` is the conductor over the `vd:` skill stack. Given a task it does two
things, in order: **classify** it and pick the smallest viable workflow (the
*conductor*), then run it through the right runtime primitives (the *router*). It
composes existing skills — it never reimplements `vd:plan`, `vd:cook`, `vd:ship`, etc.

The spine is **brainstorm → plan → cook → ship**, but ultracook runs only the slice a
task earns: a typo goes `direct` (no machinery); a feature goes `pipeline`
(intake → executor, gating at high-blast transitions, then autonomous); a repo-wide
migration goes `fan-out` (parallel packets). It stays human-in-the-loop until a gate
clears, then drives autonomously to a terminal state, with state on disk so it
resumes across context compaction.

This file is the entry point. It runs triage, detects the runtime (Claude Code or
Codex), and dispatches to the adapter under `runtimes/`.

## Quick reference

| Form | Action |
|---|---|
| `vd:ultracook "<goal>"` | New goal — intake → goal.yaml + state.json → executor loop |
| `vd:ultracook` (no args) | Resume — auto-detect most recent in-progress goal-dir, skip intake, jump to executor |
| `vd:ultracook status [--all]` | One-screen status; `--all`/`--list` enumerates every goal-dir (scripts/status.sh) |
| `vd:ultracook kill --reason "<text>"` | Write terminal=abandoned + cancel.sentinel (scripts/kill.sh — runtime-agnostic) |
| `vd:ultracook resolve <goal-dir>` | Dry-run the resolved workflow (scripts/resolve-workflow.sh — runtime-agnostic) |
| `vd:ultracook install-hooks [--apply\|--uninstall]` | Register Codex hooks in `~/.codex/config.toml` (scripts/install-hooks.sh) |

Flags: `--reuse` (no worktree), `--manual` / `--semi` (default) / `--auto` (autonomy). CI/exec: `--target-kind` `--action-shape` `--autonomy` (+`--branch` `--reuse-worktree`) with `ULTRACOOK_EXEC=1` skip intake.

## Conductor — classify first

Before any dispatch, classify the task and pick a **mode** (how much workflow) and an
**autonomy** (how often to gate). Full heuristics + gate map in
[`references/conductor.md`](references/conductor.md); the short form:

| Mode | Pick when | What runs |
|---|---|---|
| `direct` | trivial, clear, single-surface, reversible | do it inline — **no goal-dir** — narrowest check, report |
| `pipeline` | real feature/fix, phases, uncertainty, blast radius | intake → executor (brainstorm/plan/cook/ship slice) → `vd:auto-loop` → verify |
| `fan-out` | repo-wide / migration / N-finder audit, independent packets | parallel packets via the runtime's native primitive; parent owns integration |

Sub-verbs (`status`, `kill`, `resolve`, `install-hooks`) and bare resume skip triage —
they go straight to their scripts. `direct` mode finishes here without touching the
executor. `pipeline` and `fan-out` continue to runtime dispatch below.

**Progressive autonomy:** `semi` (default) gates the first `plan`, `ship`, and final
`verify_*`, then runs autonomously; re-gate only on exceptions (unrelated test
failure, merge conflict, non-auto-fixable error). Hard gates (delete, deploy,
migration, secrets, broad codemod, expensive fan-out) always ask, even in `auto`.

## Runtime dispatch

1. Run `bash scripts/detect-runtime.sh`. Output is `claude-code`, `codex`, or `codex-exec`.
2. If exit 3 (unknown — no env signals + no CLI on PATH): print "Cannot detect runtime. Set `ULTRACOOK_RUNTIME` env var explicitly."
3. Else follow the runtime body:
   - `claude-code` → see `runtimes/claude-code.md`
   - `codex` → see `runtimes/codex.md` (interactive TUI — intake via `ask_user_question`)
   - `codex-exec` → `runtimes/codex.md` in **CI / non-interactive mode**: skip interactive intake. Read default-answer flags (`--target-kind`, `--action-shape`, `--autonomy`; optional `--branch`, `--reuse-worktree`) into `ULTRACOOK_*` env, then `bash scripts/intake-complete.sh`. If it prints `ready` → call `init-goal.sh` directly. If `missing:`/`invalid:` → refuse with that exact line; never silently fall back to interactive intake.

`codex-exec` is an explicit exec contract: set `ULTRACOOK_EXEC=1` (or `ULTRACOOK_RUNTIME=codex-exec`). detect-runtime.sh never infers exec from TTY/process state — no env var distinguishes `codex exec` from `codex` TUI in codex-cli. When both Claude and Codex env signals are present, detection assumes `claude-code` (CODEX_SESSION_ID leaks via `inherit=all`); override with `ULTRACOOK_RUNTIME=codex`.

The sub-verbs (`status`, `kill`, `resolve`, `install-hooks`) short-circuit the runtime dispatch — they invoke `scripts/<sub-verb>.sh` directly because those scripts are runtime-agnostic.

## Hard rules (apply across both runtimes)

1. **State on disk is source of truth.** `<state-base>/{slug}/goal.yaml` + `state.json` survive context compaction. State base resolves to `$VD_STATE_PATH` → `<git-root>/.workbench/state` when `.workbench/` exists → `$XDG_STATE_HOME/vd/ultracook/<repo-id>/goals` (`~/.local/state/...` by default). Legacy `plans/goals` is read for old runs only; do not write new ultracook state into the project tree.
2. **Loop primitive = `vd:auto-loop` (Stop hook on Claude / `--codex` → native `/goal` on Codex).** Not `ScheduleWakeup`. Monitor is only for event-driven async waits.
3. **No auto-merge on the skills repo.** `vd:ship official` (no `--auto`).
4. **Closed-set verifier vocabulary + `shell` escape.** Six built-ins + `shell`.
5. **Two verifier layers.** Per-action verifiers (cook iteration) vs workflow-level `target.verifiers` (verify_* phases). Never mix.
6. **Hard guardrails.** Global iter cap (30), per-phase retry caps (3 rebases, 2 CI reruns), same-signature failure recognizer, token-cap prompt-back at 80%.
7. **Composes existing `vd:*` skills** — never reimplements.

## Architecture

```
SKILL.md (this file)        — conductor (classify) + router (detect + dispatch)
references/
  conductor.md              — triage: mode/autonomy selection, gate map, fan-out packets
  autonomy-modes.md         — manual/semi/auto gate semantics
  architecture.md           — two-layer SKILL.md ↔ bash-script invariant
  action-vocab.{md,yaml}    — 21 actions · verifier-vocab.{md,yaml} — 7 verifier types
  codex-runtime.md          — Codex specifics · codex-gap-workarounds.md — Monitor/Skill bridges
runtimes/
  claude-code.md            — Claude Code adapter (tools: Skill, Task, Workflow, Monitor, hooks)
  codex.md                  — Codex adapter (codex exec, subagents, --ask-for-approval/--sandbox)
  detect.md                 — runtime detection spec
scripts/                    — runtime-agnostic bash (filesystem/git/parse); never call runtime tools
projects/                   — 4 TOML profiles, picked by git remote
```

## See also

- `references/conductor.md` — how a task is classified and routed
- `runtimes/detect.md` — detection precedence + ambiguity rules
- `README.md` — install + quick-start for both runtimes
