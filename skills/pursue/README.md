# vd:pursue — goal-driven workflow orchestrator

Drive a feature/fix end-to-end: **intake → worktree → plan → cook → ship → verify** until a stated goal is verified (or hits a hard guardrail).

## Install

**Claude Code (marketplace):**

```
/plugin marketplace add vanducng/skills
/plugin install vd@vd-skills
```

**Codex (TUI):**

```
brew install vanducng/tap/vd
vd install codex pursue
# THEN register hooks in ~/.codex/config.toml — see references/codex-runtime.md
```

**Dev / local (both runtimes):**

```
brew install vanducng/tap/vd
vd install claude --dev pursue    # symlink for Claude Code dev work
vd install codex pursue            # symlink for Codex TUI dev work
```

After install, `/vd:pursue` is available as a slash command in either runtime.

## Runtime support (v0.2)

| Feature | Claude Code | Codex TUI | Codex exec |
|---|---|---|---|
| Intake | ✓ | ✓ | ✗ (errors — `ask_user_question` unavailable in exec) |
| Sequential executor | ✓ | ✓ | ✗ |
| Skill-to-skill dispatch | ✓ Skill tool | ✓ `codex exec resume` | ✗ |
| Cook+verify iteration | ✓ auto-loop Stop-hook | ✓ auto-loop --codex → /goal | ✗ |
| Monitor (wait_ci, etc.) | ✓ Monitor tool | ✓ PostToolUse hook + additionalContext | ✗ |
| Cross-session resume | ✓ via state.json | ✓ via state.json | n/a |
| Cross-runtime resume (same goal) | ✓ both directions via state.json | | |
| Push notifications | ✓ Claude Code native (or `notify.sh`) | ✓ `notify.sh` (terminal-notifier / ntfy / Slack / log) | ✓ `notify.sh` |

`codex exec` (non-interactive) parity is v0.3.

## Quick start

```
/vd:pursue "implement cron retry, ship to staging, verify"
```

Intake will ask up to 4 questions (target kind, action shape, branch name, autonomy). Then a worktree + `plans/goals/{date}-{slug}/goal.yaml` + `state.json` get created. The executor loop drives through plan → cook → ship → verify, gating at high-blast-radius transitions.

## Sub-verbs

```
/vd:pursue status                    # one-screen state summary (exit code = terminal state)
/vd:pursue kill --reason "<text>"    # write terminal=abandoned, cancel auto-loop if mid-delegation
/vd:pursue resolve <goal-dir>        # dry-run: print the resolved workflow without executing
```

## Modes

| Flag | Behaviour |
|---|---|
| `--manual` | Every action gated |
| `--semi` (default) | Gates on first `plan`, `ship`, final `verify_*` |
| `--auto` | No gates; only stops on terminal state or budget exhaustion |
| `--reuse` | Write into current repo; skip worktree creation |

Switch modes mid-flight by editing `goal.yaml.autonomy` — the executor re-reads each iteration.

## Composes

- `/vd:scout`, `/vd:research`, `/vd:brainstorm`, `/vd:plan`, `/vd:plan-audit`, `/vd:cook`, `/vd:ship`, `/vd:debug`, `/vd:fix`, `/vd:test`, `/vd:docs`, `/vd:journal`, `/vd:worktree`, `/vd:auto-loop`

When an action has a verifier defined (`cook`, `test`), pursue delegates iteration to `/vd:auto-loop` and resumes when it terminates. Requires `vd:auto-loop` installed.

## On-disk state

```
plans/goals/{YYMMDD-HHMM}-{slug}/
  goal.yaml                              # spec — see references/goal-schema.md
  state.json                             # runtime state — see references/state-schema.md
  iterations/
    001-plan.md                          # journal entry per action
    001-plan.log                         # raw stdout+stderr per action
    002-cook.md
    ...
  verify-pursue-{action}.sh              # auto-generated compound verifier when delegating
  .pursue/
    delegated-to-auto-loop.json          # marker for cross-session resume
```

All state survives context compaction. Re-invoke `/vd:pursue` in a fresh session — it reads the most recent goal-dir with `terminal=null` and resumes.

## Hard guardrails

- Global iteration cap (default 30)
- Per-phase retry caps (default 3 rebases, 2 CI reruns)
- Same-signature failure recognizer (3× same fail → `blocked`)
- Token-cap prompt-back at 80%
- `PushNotification` on `terminal=blocked` in semi/auto modes

## Per-project profiles

Defined in `projects/*.toml`, picked by `git remote get-url origin`:

- `goclaw.toml` — full cluster pipeline (reconcile + rollout + smoke). Auto-merge OK.
- `infra.toml` — flux-reconcile + manual merge.
- `skills.toml` — PR-only, **no auto-merge** (this repo).
- `_default.toml` — fallback. PR-only, no deploy, no auto-merge.

Adding a new project: drop a `<name>.toml` in `projects/` with `remote_matches` list. No code change needed.

## References

- `SKILL.md` — full skill body + executor protocol
- `references/architecture.md` — two-layer SKILL.md ↔ bash invariant
- `references/goal-schema.md` — goal.yaml v1
- `references/state-schema.md` — state.json v1 + atomic-write
- `references/intake-template.md` — 4 intake questions
- `references/action-vocab.md` + `.yaml` — 21 actions
- `references/verifier-vocab.md` + `.yaml` — 7 verifier types
- `references/autonomy-modes.md` — manual/semi/auto semantics
- `references/monitor-recipes.md` — wait_ci / image_build_wait / rollout_check patterns
- `references/auto-loop-integration.md` — Phase 5 delegation lifecycle
- `references/codex-deferred.md` — v0.2 Codex adapter plan

## Versioning

- v0.1 (this release): Claude Code only, intake + sequential executor + auto-loop delegation + per-project profiles + 4 sub-verbs.
- v0.2 (planned): Codex runtime adapter, multi-goal concurrency, profile inheritance, replay / cost telemetry, verifier `manual_confirm` two-step UX polish.
