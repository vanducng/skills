---
name: auto-loop
description: "Drive a Claude Code session toward a verifiable goal until done or a hard cap fires — autonomous loop, no user intervention. Use for refactor batches, test-coverage runs, migration loops where success is a check command (tests, lint, custom predicate) plus a fresh-context audit. Hosts the loop intra-session via Stop hook with two-vote completion gate; supports optional Codex /goal delegation."
license: MIT
argument-hint: "<goal> --verify <cmd> [--max-iterations N] [--max-tokens T] [--max-wallclock D] [--codex] | --status | --cancel"
metadata:
  author: vanducng
  version: "1.0.0"
---

# auto-loop

## What this skill is — and isn't

| Skill | Question it answers | Output |
|---|---|---|
| `/loop` | "Re-run this prompt every N minutes." | Cron-style recurrence |
| `/ralph-loop` | "Bash-while loop external to Claude." | Subprocess churn |
| `vd:cook` | "Execute the plan, phase-by-phase, with review gates." | Phased delivery |
| **`vd:auto-loop`** | **"Drive toward this goal until verified done or a cap fires — no babysitting."** | **Verified completion or graceful drain** |

Auto-loop **pursues**. It does not design (use `vd:brainstorm`/`vd:plan` first) and it does not poll on a clock (use `/loop`). The exit condition is a **two-vote completion gate**: a user-supplied verifier command **and** a fresh-context audit subagent both vote `achieved`.

## Modes

| Flag | Behaviour |
|---|---|
| _(default)_ | Run intra-session loop hosted by Stop hook until two-vote gate or hard cap. |
| `--codex` | Delegate to native Codex `/goal` (requires codex ≥ 0.128.0 + ChatGPT auth). |
| `--status` | Read-only snapshot of current loop state. Exits with status-coded code. |
| `--cancel` | Tear down Stop hook, mark state `cancelled`, leave working tree intact. |

## Hard rules

1. **Two-vote completion gate.** `status: achieved` is *not* terminal until verifier passes 2× and audit subagent votes `achieved`. False positives loop back as `unmet`.
2. **Hard caps non-negotiable.** Iterations / tokens / wallclock — at least one always set. Wallclock cap defaults to `4h` and is the floor cap (always present even if user sets only iter or token caps).
3. **State file is source of truth.** `.auto-loop/goal-state.json` round-trips across compaction and restart. Schema-validated atomic writes only.
4. **No `--dangerously-skip-permissions`.** Default sandbox = workspace-write semantics. Loops needing broader access must allow-list explicit globs in `goal.md` scope.
5. **No audit recursion.** `VD_AUTOLOOP_DEPTH` env-flag gate; audit subagents may not invoke `vd:auto-loop`, `ralph-loop`, or `codex /goal`.
6. **No `ScheduleWakeup` for loop primitive.** Stop-hook re-feed is the loop; ScheduleWakeup is reserved for `/loop` and has known re-fire bugs (anthropics/claude-code#51304, #54086).

## Arguments

| Flag | Default | Notes |
|---|---|---|
| `<goal>` (positional) | — | Required for default mode. Use `goal.md` shape if multi-line. |
| `--verify <cmd>` | — | Required for default mode. Shell command; exit 0 = pass. Run twice per gate check. |
| `--goal-file <path>` | `goal.md` | Markdown spec (overrides positional `<goal>`). See `references/goal-spec-format.md`. |
| `--max-iterations <N>` | `40` | Hard ceiling; `budget-limited` reason `iterations`. |
| `--max-tokens <T>` | `2000000` | Advisory unless `ccusage` present; falls back silently if probe noisy. |
| `--max-wallclock <D>` | `4h` | **Floor cap** — always enforced. Accepts `30m`, `2h`, `4h30m`. |
| `--restart-pct <N>` | `70` | Context % triggering phase-restart compaction. |
| `--codex` | off | Delegate to Codex `/goal`. |
| `--status` | — | Read-only inspect. |
| `--cancel` | — | Stop active loop. |

`--status` / `--cancel` / `--codex` are mutually exclusive with each other and with default-mode args.

## Workflow position

`vd:plan` (decide what) → **`vd:auto-loop`** (drive to done) → `vd:journal` (record what happened).

Use auto-loop when (a) the goal has a single-shot verifier and (b) you'd otherwise babysit `vd:cook` for hours. Use `vd:cook` instead when phases want human review between them.

## Anti-patterns

- "Tests pass = done." No — tests passing is one vote. The audit subagent independently re-reads goal vs diff.
- "Disable wallclock cap to let it run all night." No — wallclock is the floor. Raise it (`--max-wallclock 12h`) instead.
- "Run two auto-loops in the same workspace." Refused — heartbeat lock prevents it.
- "Use ScheduleWakeup with `/vd:auto-loop` as the prompt." Re-fire bug. Use the in-process Stop-hook host.
- "Audit subagent calls another `/vd:auto-loop` for sub-goals." Recursion guard refuses; promote to peer skill instead.

## Argument parser

`scripts/dispatch.sh` parses the flags listed above, validates mutual exclusion,
seeds `.auto-loop/heartbeat.json` + `goal-state.json`, and installs the Stop
hook. Invoke with no arguments to print `references/usage.md`.

## See also

- `references/usage.md` — bare-invocation help text.
- `references/goal-spec-format.md` — `goal.md` schema (phase 2).
- `references/architecture.md` — state machine + contract diagram (phase 8).
- `references/smoke-test.md` — reproducible end-to-end recipe (phase 8).
- `references/codex-delegation.md` — when and how `--codex` works (phase 7).
- `references/troubleshooting.md` — common failure modes (phase 8).
