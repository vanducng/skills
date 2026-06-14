---
runtime: codex
phase: v0.4
---

# Codex runtime adapter

Loaded by top-level `SKILL.md` when `scripts/detect-runtime.sh` returns `codex`. Mirrors the shape of `runtimes/claude-code.md` but uses Codex primitives instead of Claude Code tools.

## Detection assumption

`CLAUDE_*` tools (`AskUserQuestion`, `Skill`, `Monitor`, `Agent`) are NOT available in a Codex session. This file uses Codex equivalents below. If you reached this file from Claude Code, the detector misfired — set `ULTRACOOK_RUNTIME=claude-code` and retry.

## Codex primitive map

| Claude Code primitive | Codex equivalent | Used in this skill |
|---|---|---|
| `AskUserQuestion` | `ask_user_question` (Codex native, TUI-only) | Intake, semi-mode gates, `manual_confirm` verifier |
| `Skill` (invoke another skill) | `codex exec resume --last "use <skill> ..."` via `scripts/codex-bridge.sh codex_exec_resume_last` | Dispatching `vd:plan`, `vd:cook`, `vd:ship`, etc. |
| `Agent` (subagent dispatch) | Native Codex subagents | Code review, audit (Phase 5) |
| `Monitor` (event-driven external command) | PostToolUse hook + `additionalContext` injection (Phase 3) — see `references/codex-gap-workarounds.md` | `wait_ci`, `image_build_wait`, `rollout_check` |
| `PushNotification` | `scripts/notify.sh` (Phase 4) — terminal-notifier / ntfy.sh / Slack / log fallback | Terminal=blocked notifications |
| `TaskCreate` / `TaskUpdate` | File-based — ultracook's `iterations/NNN-*.md` journal | Already runtime-agnostic |

## Conductor modes + autonomy mapping (Codex)

Triage happens in `SKILL.md` (see `references/conductor.md`). How each mode lands on
Codex primitives:

| Mode | Codex primitive |
|---|---|
| `direct` | Do it in the current session (read/apply-patch). No goal-dir, no executor. |
| `pipeline` | Intake → executor; dispatch each action via `codex exec resume` (`codex-bridge.sh`); iterate via `vd:auto-loop --codex` (native `/goal`); wait on CI via PostToolUse hook + `additionalContext`. |
| `fan-out` | Native Codex subagents (`[agents] max_threads`, `max_depth`); `explorer` agent for read-only packets, `worker` for bounded write packets. Each packet gets a self-contained prompt — don't pair an agent type with a full-history fork. |

**Autonomy ↔ approval/sandbox.** Codex gates with `--ask-for-approval`
(`untrusted` / `on-request` / `never`) × `--sandbox`
(`read-only` / `workspace-write` / `danger-full-access`). Ultracook's `should-gate.sh`
remains the source of truth for *when* to gate; the idiomatic posture per autonomy:

| Autonomy | Codex posture |
|---|---|
| `manual` | `--ask-for-approval on-request --sandbox workspace-write` (TUI confirms each gate via `ask_user_question`) |
| `semi` (default) | interactive through the plan-approval gate, then resume autonomously: `codex exec --continue <session> --ask-for-approval never --sandbox workspace-write` |
| `auto` | `--ask-for-approval never --sandbox workspace-write` from the start; hard gates still surface via `notify.sh` |

Never use `--sandbox danger-full-access` for ultracook runs. The hard gates in
`references/conductor.md` (delete, deploy, migration, secrets, broad codemod) hold
regardless of approval mode.

**Runtime detection.** `detect-runtime.sh` returns `codex` from Codex env signals;
`codex-exec` only under the explicit `ULTRACOOK_EXEC=1` contract (below). Layered
instructions come from `AGENTS.md` (global → repo → dir); keep ultracook's invariants
in the repo `AGENTS.md` so subagents inherit them.

## `codex exec` (non-interactive) mode handling — v0.3 default-answer mode

`ask_user_question` is **unavailable in `codex exec`** (per [Codex docs](https://developers.openai.com/codex/noninteractive)). Instead of the interactive intake, exec mode reads the answers from flags.

Detection: `detect-runtime.sh` emits `codex-exec` ONLY under the explicit contract `ULTRACOOK_EXEC=1` (or `ULTRACOOK_RUNTIME=codex-exec`) — never inferred from TTY/process state, because no env var distinguishes `codex exec` from the `codex` TUI in codex-cli.

In `codex-exec`, skip intake and:

1. Read default-answer flags into `ULTRACOOK_*` env: `--target-kind` `--action-shape` `--autonomy` (required), `--branch` `--reuse-worktree` (optional).
2. `bash scripts/intake-complete.sh` — prints `ready` (exit 0), `missing: <flags>` (exit 2), or `invalid: <details>` (exit 3).
3. If `ready` → call `init-goal.sh` directly. Otherwise refuse with that exact line — NEVER silently fall back to interactive intake (that is the refuse-loop this mode removes).

```
ULTRACOOK_EXEC=1 codex exec "vd:ultracook '<goal>' --target-kind=pr-only --action-shape=plan-only --autonomy=semi"
```

See `references/codex-runtime.md` → "CI / non-interactive usage".

## Entry routing — intake OR resume

Same shape as `runtimes/claude-code.md`. The executor's first decision branches on `$1`:

```
if $1 is empty (bare `vd:ultracook`):
  # Resume mode — auto-detect most recent in-progress goal-dir.
  # Scans BOTH <state-base> ($VD_STATE_PATH → <git-root>/.workbench/state → XDG user state) AND legacy plans/goals.
  goal_dir = scan [state_base, "plans/goals"] dedup sort-r \
             | while read d; do
                 if jq -e '.terminal == null' "$d/state.json" >/dev/null 2>&1; then
                   echo "$d"; break
                 fi
               done
  if goal_dir found:
    print "resuming goal {slug} (current_phase={current_phase})"
    jump to executor loop (skip intake)
  else:
    print "no in-progress goal. Pass a goal: vd:ultracook \"<short goal>\""
    exit 0

elif $1 == "status" or "kill" or "resolve":
  dispatch to scripts/status.sh / kill.sh / resolve-workflow.sh (sub-verbs)

else:
  # New-goal mode — $1 is the short goal text.
  run Intake flow (next section)
```

**This mirrors Claude Code's `runtimes/claude-code.md` exactly.** The state.json portability invariant requires both adapters to read/write the same shape and to use the same resume entry logic. Phase 5 keystone test verifies this.

## Phase 1 — Intake (new-goal mode)

`vd:ultracook "<short goal>"` runs:

1. Four `ask_user_question` prompts (see `references/intake-template.md` for the question shape):
   - target kind (local / pr-only / cluster)
   - action shape (brainstorm-first / plan-only / fix-and-ship / refactor)
   - branch name (suggested from slug; skip when `--reuse`)
   - autonomy (manual / semi / auto; default semi)
2. Read the 4 answers, set env vars: `ULTRACOOK_TARGET_KIND`, `ULTRACOOK_ACTION_SHAPE`, `ULTRACOOK_BRANCH`, `ULTRACOOK_AUTONOMY`, `ULTRACOOK_REUSE_WORKTREE` (if `--reuse`).
3. Invoke `bash scripts/init-goal.sh "<short_goal>"` — this script is runtime-agnostic; it writes goal.yaml + state.json + (optionally) creates worktree.
4. Print the goal-dir path returned by init-goal.sh.
5. Jump to the sequential executor (next section).

Implementation note: Codex's `ask_user_question` uses a tabbed UI (per [issue #9926](https://github.com/openai/codex/issues/9926)). The argument shape is question text + array of options (each with label + description); single-select unless multiSelect is set. Match `references/intake-template.md`'s structure exactly.

## Sequential executor (Phase 2 scope — simple actions only)

The executor loop in pseudocode:

```
while state.terminal is null:
  state = read(goal_dir/state.json)
  if state.terminal: break

  next_action = bash scripts/resolve-workflow.sh {goal_dir} | head-pick first pending action
  if next_action in ("done", "block"):
    bash scripts/update-state.sh --goal-dir {goal_dir} <<<'{"terminal": "<action>"}'
    break

  # Gate? (semi mode: gate on first plan/ship/verify_smoke; manual mode: gate all; auto: never gate)
  gate = bash scripts/should-gate.sh --mode {autonomy} --action {next_action} --phase-state {first|repeat}
  if gate == 0 (gate required):
    answer = ask_user_question("Run {next_action}? run / skip / quit")
    handle answer accordingly (skip → advance state.current_action without dispatch; quit → set terminal=abandoned)

  # Dispatch via run-action.sh (returns JSON hint)
  hint = bash scripts/run-action.sh --goal-dir {goal_dir} --action {next_action}
  case hint.dispatch_kind:
    "skill":  bash scripts/codex-bridge.sh resume-last {hint.skill} "{hint.args}"
    "agent":  spawn native Codex subagent (Phase 3 details)
    "monitor": PostToolUse hook + additionalContext (Phase 3 — STUB for now; sets terminal=blocked with phase-2-stub reason)
    "shell":  bash exec (already executed by run-action.sh; read hint.exit_code)
    "terminal": handled above

  # Verifier (per-action)
  if hint.verifier:
    if hint.verifier.type == "manual_confirm":
      # 2-step protocol: eval-verifier returns sentinel → ask_user_question → eval-verifier --resolve
      answer = ask_user_question(hint.verifier.args.prompt)
      bash scripts/eval-verifier.sh --type manual_confirm --resolve {yes|no} --prompt ... → JSON
    else:
      bash scripts/eval-verifier.sh --type {hint.verifier.type} ... → JSON
    parse pass / evidence from JSON

  # Journal + state update
  bash scripts/append-journal.sh --goal-dir ... --action ... --exit-code ... --verifier-pass ... --verifier-evidence ...
  echo '{"current_action":"{action}","iteration_count":N+1,"last_action_result":{...}}' \
    | bash scripts/update-state.sh --goal-dir ...
```

**Failure handling** (same-signature recognizer): identical to claude-code.md.
**Budget checks**: identical to claude-code.md.

## Action dispatch table (Phase 2 wiring)

Per `references/action-vocab.yaml`. Most actions work via the generic skill dispatch above; specific Codex notes:

| Action | Phase 2 status | Codex dispatch detail |
|---|---|---|
| `scout`, `research`, `brainstorm` | ✓ Phase 2 wired | `codex_exec_resume_last vd:<skill> ...` |
| `plan`, `plan_audit` | ✓ Phase 2 wired | Same |
| `cook`, `test` | ✓ Phase 3 wired | Delegates to `vd:auto-loop --codex` (auto-detected runtime adds `--codex` flag); see `references/auto-loop-integration.md` + `references/codex-gap-workarounds.md` Workaround 3 |
| `code_review` | ✓ Phase 2 wired | Native Codex subagent |
| `ship` | ✓ Phase 2 wired | `codex_exec_resume_last vd:ship ...` |
| `wait_ci`, `image_build_wait`, `rollout_check` | ✓ Phase 3 wired | PostToolUse hook + `additionalContext` via `scripts/codex-monitor-hook.sh`; see `references/codex-gap-workarounds.md` Workaround 2 |
| `verify_pod_image`, `verify_smoke` | ✓ Phase 2 wired | Shell dispatch (run-action.sh handles inline) |
| `debug`, `fix`, `docs`, `journal` | ✓ Phase 2 wired | `codex_exec_resume_last vd:<skill> ...` |
| `done`, `block` | ✓ Phase 2 wired | Terminal state write |

Stubbed actions (Phase 2 placeholder): when dispatched, set `state.terminal=blocked` with `terminal_reason="phase-2-stub: <action> deferred to Phase 3"`. Allows Phase 5 keystone test to use a non-stubbed action sequence (e.g. `[plan, done]`).

## Hard rules (same as claude-code.md)

1. State on disk is source of truth — `state.json` portable across runtimes.
2. Loop primitive = `vd:auto-loop` (`--codex` mode on Codex). NOT `ScheduleWakeup`.
3. No auto-merge on the skills repo.
4. Closed-set verifier vocabulary + `shell` escape.
5. Two verifier layers (per-action vs target.verifiers).
6. Hard guardrails: global iter cap, per-phase retry caps, same-signature recognizer, token-cap prompt-back.
7. Composes existing `vd:*` skills via `codex_exec_resume_last`.

## Modes (autonomy)

Same as claude-code.md: `manual` / `semi` (default) / `auto`. Gate decisions go through `scripts/should-gate.sh` — runtime-agnostic.

## Sub-verbs

Identical to claude-code.md — `status`, `kill`, `resolve` short-circuit to their respective scripts, all runtime-agnostic.

## Cross-session resume

On Codex, sessions persist as JSONL under `~/.codex/sessions/`. ultracook's resume invariant doesn't rely on this — it relies on `state.json` on disk. Bare `vd:ultracook` (no args) re-reads state.json and continues. Phase 5 keystone proves this works across runtime boundaries (Claude → Codex on the same goal).

## See also

- `runtimes/claude-code.md` — Claude Code adapter (mirror of this)
- `runtimes/detect.md` — runtime detection precedence
- `references/codex-runtime.md` — Codex-specific notes + v0.3 deferrals
- `references/codex-gap-workarounds.md` — Phase 3 work: Monitor/Skill-to-skill/`vd:auto-loop` details
- `references/architecture.md` — two-layer SKILL.md ↔ bash invariant
- `scripts/codex-bridge.sh` — Codex helpers (resume, hook payload, JSON parse)
