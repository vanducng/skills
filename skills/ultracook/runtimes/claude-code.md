---
name: ultracook
description: "Claude Code adapter for the ultracook conductor. Drives a task through the brainstorm → plan → cook → ship spine using Claude Code primitives (Skill, Task, Workflow, Monitor, Stop-hook loops), gating per autonomy mode, resuming from on-disk state."
license: MIT
argument-hint: "<short goal> [--reuse] [--manual | --semi | --auto] | status | kill --reason <text> | resolve <goal-dir>"
metadata:
  author: vanducng
  version: "0.4.0"
---

# Ultracook

## What this skill is - and isn't

| Skill | Question it answers | Output |
|---|---|---|
| `vd:plan` | "What are the steps?" | Phased plan |
| `vd:cook` | "Execute the plan." | Code changes |
| `vd:ship` | "Land the branch." | Merged target |
| `vd:auto-loop` | "Drive to a verifier until passing." | Verified completion |
| **`vd:ultracook`** | **"Drive a goal end-to-end: intake → plan → cook → ship → verify, until done."** | **Verified deployment or graceful block** |

Ultracook **conducts the whole workflow**. It owns design when the spec is ambiguous  - 
the `brainstorm-first` shape runs `vd:brainstorm` before planning - but it does not run
the inner iteration itself: when an action has a verifier, ultracook delegates to
`vd:auto-loop` and resumes when that terminates.

## Conductor modes + autonomy mapping (Claude Code)

Triage happens in `SKILL.md` (see `references/conductor.md`). How each mode lands on
Claude Code primitives:

| Mode | Claude Code primitive |
|---|---|
| `direct` | Do it in-session with `Read`/`Edit`/`Bash`. No goal-dir, no executor. Narrowest verification. |
| `pipeline` | Intake → executor; dispatch each action via `Skill`; iterate via `vd:auto-loop` (Stop hook); wait on CI/builds via `Monitor`. |
| `fan-out` | `Workflow` tool for deterministic fan-out/pipeline (repo-wide, migration, N-finder - `pipeline()` by default, `parallel()` only for genuine joins); `Task`/`Agent` subagents for a handful of independent packets launched in one message. |

**Autonomy ↔ permission posture.** Ultracook's gates (`should-gate.sh`) are independent
of Claude Code's permission mode, but pair naturally: run interactively (default /
`acceptEdits`) through the plan-approval gate, then - once the plan is approved - let it
run autonomously (`acceptEdits` / `auto`) to a terminal state. The Stop-hook loop inside
`vd:auto-loop` is the autonomous driver; ultracook re-gates only on the exceptions in
`references/conductor.md`. Never use `bypassPermissions` for ultracook runs.

**Runtime detection.** `scripts/detect-runtime.sh` returns `claude-code` when
`CLAUDECODE=1` (or other CLAUDE signals) is present. Subagents inherit it.

## Hard rules

1. **State on disk is source of truth.** `<state-base>/{slug}/goal.yaml` + `state.json` + `iterations/NNN-*.md` survive context compaction. Re-invoking `vd:ultracook` reads them and resumes; never trust in-memory cache across sessions. State base = `$VD_STATE_PATH` → `<git-root>/.workbench/state` (when `.workbench` exists) → `$XDG_STATE_HOME/vd/ultracook/<repo-id>/goals` (`~/.local/state/...` by default). Legacy `plans/goals` is read for old runs only.
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
| `<short goal>` (positional) | Trigger intake. Creates `<state-base>/{date}-{slug}/`. |
| `--reuse` | Skip worktree creation; write goal artifacts into the current repo. |
| `--manual` / `--semi` / `--auto` | Set autonomy at intake (overrides goal.yaml on first run). |
| `resolve <goal-dir>` | Dry-run: print the resolved workflow (Phase 2). |
| `status` | Read state.json + last journal entry; print human summary (Phase 6). |
| `kill --reason "<text>"` | Write `terminal=abandoned`; if mid-delegation, also cancel `vd:auto-loop` (Phase 6). |

## Entry routing - intake OR resume

`vd:ultracook` is overloaded. The executor first decides which path to take based on `$1`:

```
if $1 is empty (bare `vd:ultracook`):
  # Resume mode - find in-progress goal-dirs (terminal == null).
  # State base resolution: $VD_STATE_PATH → <git-root>/.workbench/state (when .workbench exists) → XDG user state.
  # Discovery scans BOTH the resolved state base AND legacy plans/goals (read-either).
  candidates = scan [state_base, "plans/goals"] dedup sort-r \
               | filter: jq -e '.terminal == null' "$d/state.json"
  if exactly 1 candidate:
    print "resuming goal {slug} (current_phase={current_phase})"
    jump to executor loop (skip intake - Phase 3+ protocol)
  elif >1 candidate (#66 multi-goal disambiguation):
    # Don't silently pick the newest - that orphans the others.
    run `bash scripts/status.sh --all` to show slug + state + age + last-action,
    then AskUserQuestion("Which goal to resume?") over the non-terminal candidates;
    jump to executor for the picked goal-dir.
  else (0 candidates):
    print "no in-progress goal. Pass a goal: vd:ultracook \"<short goal>\""
    exit 0

elif $1 == "status" or "kill" or "resolve":
  dispatch to scripts/status.sh / kill.sh / resolve-workflow.sh (sub-verbs)

else:
  # New-goal mode - $1 is the short goal text.
  run Intake flow (next section)
```

The "Resume mode" mirrors `scripts/status.sh`'s auto-detect logic. **Phase 5's keystone test (cross-runtime state.json portability) depends on this entry path.** `runtimes/codex.md` must mirror identical resume-mode behavior.

## Phase 1 - Intake (new-goal mode)

`vd:ultracook "<short goal>"` runs:

1. Up to 4 `AskUserQuestion` prompts (see `references/intake-template.md`):
   - target kind (local / pr-only / cluster)
   - action shape (brainstorm-first / plan-only / fix-and-ship / refactor)
   - branch name (suggested from slug; skip when `--reuse`)
   - autonomy (manual / semi / auto; default semi)
2. Computes slug from short goal (kebab-case, max 40 chars).
3. Optionally creates a worktree: `git worktree add .worktrees/{repo}-{slug} -b {branch}` (standard `.worktrees/` location) (skip if `--reuse`).
4. Writes `<state-base>/{date}-{slug}/goal.yaml` + `state.json` (terminal=null, current_phase=intake-complete). State base = `$VD_STATE_PATH` → `<git-root>/.workbench/state` (when `.workbench` exists) → `$XDG_STATE_HOME/vd/ultracook/<repo-id>/goals` (`~/.local/state/...` by default).
5. Prints the goal-dir path so the next step (Phase 2 `resolve`) can chain.

**Implementation:** `scripts/init-goal.sh` is called from this SKILL.md after the 4 `AskUserQuestion` prompts populate env vars (`ULTRACOOK_TARGET_KIND`, `ULTRACOOK_ACTION_SHAPE`, `ULTRACOOK_BRANCH`, `ULTRACOOK_AUTONOMY`, `ULTRACOOK_REUSE_WORKTREE`). The script handles slug derivation, worktree creation, and file writes. **`AskUserQuestion` cannot be called from bash** - it must be invoked from this SKILL.md and the answers passed to the script via env vars. See `references/architecture.md` for the two-layer pattern.

## Schemas

- `references/goal-schema.md` - `goal.yaml` shape (v1)
- `references/state-schema.md` - `state.json` shape (v1) + atomic write protocol
- `references/intake-template.md` - the 4 intake questions + answer-to-goal.yaml mapping
- `references/architecture.md` - two-layer SKILL.md ↔ bash-script invariant

## Phase 3 - Executor protocol (manual mode)

After intake (`state.terminal=null`, `current_phase=intake-complete`), the executor loop runs. Each iteration in pseudo-code:

```
while state.terminal is null:
  state = read(goal_dir/state.json)
  if state.terminal: break

  # Decide next action: first unrun in the resolved sequence.
  next = `bash scripts/resolve-workflow.sh {goal_dir}`   # returns 12-row table
  action = pick-first-unrun(next, state.iteration_count)
  if action is "done" or "block":
    update-state.sh terminal={action}
    break

  # Gate? (Phase 4 wires this; Phase 3 manual-mode gates EVERY action.)
  if mode == "manual" or action in gate_default for current mode:
    AskUserQuestion("Run {action}? run / skip / quit")
    if not "run": handle accordingly

  # Dispatch via run-action.sh - returns the invocation hint.
  hint = `bash scripts/run-action.sh --goal-dir {goal_dir} --action {action}`
  case hint.dispatch_kind:
    "skill":    Skill(skill: hint.skill, args: hint.args)
    "agent":    Agent(subagent_type: hint.subagent_type, prompt: ...)
    "monitor":  Monitor(command: hint.shell_cmd, ...)
    "shell":    (already executed by run-action.sh; read hint.exit_code)
    "terminal": (handled above)

  # Verifier (per-action).
  if hint.verifier:
    if hint.verifier.type == "manual_confirm":
      AskUserQuestion(hint.verifier.args.prompt)
      eval-verifier.sh --type manual_confirm --resolve {yes|no} --prompt ...
    else:
      eval-verifier.sh --type {hint.verifier.type} ... → returns JSON
    parse pass/evidence

  # Journal + state.
  append-journal.sh --goal-dir ... --action ... --exit-code ... \
                    --verifier-pass {true|false} --verifier-evidence ...
  echo '{"current_action":"{action}","iteration_count":N+1,"last_action_result":{...}}' \
    | update-state.sh --goal-dir ...
```

**Failure handling (same-signature recognizer):** when a verifier fails, the executor checks `state.last_failure_signature` (computed as `action|verifier_type|exit_code`). If the same signature fires 3 times in a row → write `terminal=blocked` with reason. Otherwise increment `last_failure_count`.

**Budgets:** before each action, check `state.budgets_consumed` against `goal.yaml.budgets`. If any exceeded → `terminal=blocked`.

**Manual_confirm flow** (the only 2-step verifier):
1. `eval-verifier.sh --type manual_confirm --prompt "..."` returns sentinel `{"needs_user_input": true, "prompt": "..."}`
2. SKILL.md detects sentinel → `AskUserQuestion(prompt)` → captures answer.
3. `eval-verifier.sh --type manual_confirm --resolve {yes|no} --prompt "..."` writes the journal-shape JSON.

Phase 4 layers autonomy modes on top of this protocol. Phase 5 swaps the cook+verify loop for delegation to `vd:auto-loop`.

## Sub-verbs

| Sub-verb | Script | Exit codes |
|---|---|---|
| `vd:ultracook status [--all]` | `scripts/status.sh` | 0=done/in-progress-exist · 1=blocked · 2=abandoned · 3=in-progress · 4=no goal found |
| `vd:ultracook kill --reason "..."` | `scripts/kill.sh` | 0=killed · 3=already terminal |
| `vd:ultracook resolve <goal-dir>` | `scripts/resolve-workflow.sh` | 0=resolved (dry-run printed) · 5=unknown action in vocab |
| `vd:ultracook install-hooks [--apply\|--uninstall]` | `scripts/install-hooks.sh` | 0=ok/idempotent · 2=bad-args · 3=needs --apply/conflict · 4=write/parse fail |

`kill.sh` returns a JSON hint - if `needs_auto_loop_cancel: true`, SKILL.md must invoke `Skill(skill: "vd:auto-loop", args: "--cancel")` BEFORE the killed state propagates to consumers. It also writes `{goal-dir}/.ultracook/cancel.sentinel` and (on Codex) prints a `codex_goal_note` reminding the user to `/goal cancel` in the TUI.

## Codex runtime

Codex support lives in `runtimes/codex.md`. Keep shared behavior and user-facing
canonical skill IDs free of runtime prefixes here; runtime-specific invocation
prefixes belong at the boundary where the user actually calls the skill.

## Workflow position

**Typically follows:** a short intent ("ship X to staging and verify").
**Typically composes:** `vd:scout`, `vd:brainstorm`, `vd:plan`, `vd:plan-audit`, `vd:cook`, `vd:ship`, `vd:debug`, `vd:fix`, `vd:research`, `vd:test`, `vd:docs`, `vd:journal`, `vd:worktree`, `vd:auto-loop`.
**Compares to:** `vd:cook` (one phase at a time, no e2e drive) and `vd:auto-loop` (iterate to a verifier, no workflow shape).
