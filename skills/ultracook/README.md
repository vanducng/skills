# vd:ultracook - dynamic workflow conductor

Hand ultracook a task; it classifies the work and runs the smallest viable workflow:

- **direct** - trivial/clear → just do it, no machinery.
- **pipeline** - a real feature/fix → **brainstorm → plan → cook → ship → verify**, gating
  at high-blast transitions, then autonomous; resumes across context compaction.
- **fan-out** - repo-wide / migration / N-finder audit → parallel packets via the
  runtime's native primitive; the parent owns integration.

It stays human-in-the-loop until a gate clears, then drives autonomously to a verified
terminal state (or a graceful block). Dual-runtime (Claude Code + Codex). Triage logic
lives in `references/conductor.md`.

> Renamed from `vd:pursue` (v0.4). Migration: env vars `PURSUE_*` → `ULTRACOOK_*`, the
> goal sentinel dir `.pursue/` → `.ultracook/`; Codex users re-run
> `vd:ultracook install-hooks --apply`. In-flight pre-rename goals won't auto-resume.

## Install

**Claude Code (marketplace):**

```
/plugin marketplace add vanducng/skills
/plugin install vd@vd-skills
```

**Codex (TUI):**

```
brew install vanducng/tap/vd
vd install codex ultracook
vd:ultracook install-hooks --apply    # register Codex hooks in ~/.codex/config.toml
```

**Dev / local (both runtimes):**

```
brew install vanducng/tap/vd
vd install claude --dev ultracook    # symlink for Claude Code dev work
vd install codex ultracook            # symlink for Codex TUI dev work
```

After install, invoke the skill with the runtime's prefix: slash in Claude Code,
dollar in Codex. Examples below omit the prefix and use canonical skill IDs.

## Runtime support (v0.4)

| Feature | Claude Code | Codex TUI | Codex exec |
|---|---|---|---|
| Intake | ✓ | ✓ | ✓ default-answer flags (`ULTRACOOK_EXEC=1` + `--target-kind/--action-shape/--autonomy`) |
| Sequential executor | ✓ | ✓ | ✓ |
| Skill-to-skill dispatch | ✓ Skill tool | ✓ `codex exec resume` | ✓ |
| Cook+verify iteration | ✓ `vd:auto-loop` Stop-hook | ✓ `vd:auto-loop --codex` → /goal | ✓ |
| Monitor (wait_ci, etc.) | ✓ Monitor tool | ✓ PostToolUse hook + additionalContext | ✓ |
| Cross-session resume | ✓ via state.json | ✓ via state.json | ✓ |
| Cross-runtime resume (same goal) | ✓ both directions via state.json | | |
| Push notifications | ✓ Claude Code native (or `notify.sh`) | ✓ `notify.sh` (terminal-notifier / ntfy / Slack / log) | ✓ `notify.sh` |

`codex exec` mode skips the interactive intake and reads the answers from flags - see `references/codex-runtime.md` → "CI / non-interactive usage". Detection requires the explicit `ULTRACOOK_EXEC=1` contract.

## Quick start

```
vd:ultracook "implement cron retry, ship to staging, verify"
```

Intake will ask up to 4 questions (target kind, action shape, branch name, autonomy). Then a worktree + `<state-base>/{date}-{slug}/goal.yaml` + `state.json` get created. The executor loop drives through plan → cook → ship → verify, gating at high-blast-radius transitions.

## Sub-verbs

```
vd:ultracook status                    # one-screen state summary (exit code = terminal state)
vd:ultracook status --all              # enumerate ALL goal-dirs (slug, state, age, last-action) - #66
vd:ultracook kill --reason "<text>"    # terminal=abandoned + cancel.sentinel; cancels vd:auto-loop / signals Codex /goal
vd:ultracook resolve <goal-dir>        # dry-run: print the resolved workflow without executing
vd:ultracook install-hooks [--apply|--uninstall]   # register/remove Codex hooks in ~/.codex/config.toml
```

When more than one goal is in-flight, bare `vd:ultracook` (resume) and `status --all` list them so you can pick - no silent newest-wins. `kill` writes a cooperative `cancel.sentinel`; on Codex it also reminds you to `/goal cancel` in the TUI (codex CLI has no programmatic cancel).

## Modes

| Flag | Behaviour |
|---|---|
| `--manual` | Every action gated |
| `--semi` (default) | Gates on first `plan`, `ship`, final `verify_*` |
| `--auto` | No gates; only stops on terminal state or budget exhaustion |
| `--reuse` | Write into current repo; skip worktree creation |

Switch modes mid-flight by editing `goal.yaml.autonomy` - the executor re-reads each iteration.

## Composes

- `vd:scout`, `vd:research`, `vd:brainstorm`, `vd:plan`, `vd:plan-audit`, `vd:cook`, `vd:ship`, `vd:debug`, `vd:fix`, `vd:docs`, `vd:journal`, `vd:worktree`, `vd:auto-loop`

When an action has a verifier defined (`cook`, `test`), ultracook delegates iteration to `vd:auto-loop` and resumes when it terminates. Requires `vd:auto-loop` installed.

## On-disk state

State base resolves to `$VD_STATE_PATH`, then `<git-root>/.workbench/state` when `.workbench/` exists, then `$XDG_STATE_HOME/vd/ultracook/<repo-id>/goals` (`~/.local/state/...` by default). Legacy `plans/goals` is still scanned for old runs but is not used for new writes.

```
<state-base>/{YYMMDD-HHMM}-{slug}/
  goal.yaml                              # spec - see references/goal-schema.md
  state.json                             # runtime state - see references/state-schema.md
  iterations/
    001-plan.md                          # journal entry per action
    001-plan.log                         # raw stdout+stderr per action
    002-cook.md
    ...
  verify-ultracook-{action}.sh              # auto-generated compound verifier when delegating
  .ultracook/
    delegated-to-auto-loop.json          # marker for cross-session resume
```

All state survives context compaction. Re-invoke `vd:ultracook` in a fresh session - it reads the most recent goal-dir with `terminal=null` and resumes.

## Hard guardrails

- Global iteration cap (default 30)
- Per-phase retry caps (default 3 rebases, 2 CI reruns)
- Same-signature failure recognizer (3× same fail → `blocked`)
- Token-cap prompt-back at 80%
- `PushNotification` on `terminal=blocked` in semi/auto modes

## Per-project profiles

Defined in `projects/*.toml`, picked by `git remote get-url origin`:

- `goclaw.toml` - full cluster pipeline (reconcile + rollout + smoke). Auto-merge OK.
- `infra.toml` - flux-reconcile + manual merge.
- `skills.toml` - PR-only, **no auto-merge** (this repo).
- `_default.toml` - fallback. PR-only, no deploy, no auto-merge.

Adding a new project: drop a `<name>.toml` in `projects/` with `remote_matches` list. No code change needed.

## References

- `SKILL.md` - conductor + runtime router
- `references/conductor.md` - triage: mode/autonomy selection, gate map, fan-out packets
- `references/architecture.md` - two-layer SKILL.md ↔ bash invariant
- `references/goal-schema.md` - goal.yaml v1
- `references/state-schema.md` - state.json v1 + atomic-write
- `references/intake-template.md` - 4 intake questions
- `references/action-vocab.md` + `.yaml` - 21 actions
- `references/verifier-vocab.md` + `.yaml` - 7 verifier types
- `references/autonomy-modes.md` - manual/semi/auto semantics
- `references/monitor-recipes.md` - wait_ci / image_build_wait / rollout_check patterns
- `references/auto-loop-integration.md` - Phase 5 delegation lifecycle
- `references/codex-runtime.md` - Codex runtime notes

## Versioning

- v0.1: Claude Code runtime, intake + sequential executor + `vd:auto-loop` delegation + per-project profiles + 4 sub-verbs.
- v0.2: Codex runtime adapter, shared state resume, monitor hooks, and cross-runtime goal portability.
- v0.3: `codex exec` default-answer mode (#60), `install-hooks` sub-verb (#61), `status --all` + multi-goal resume disambiguation (#66), cooperative Codex `/goal` cancel via `cancel.sentinel` (#65), and `check-install-conflicts.sh` marketplace/symlink duplicate detection (#64). Hardened runtime detection (broadened CLAUDE signal; explicit `ULTRACOOK_EXEC` exec contract). Deferred: real cross-runtime TUI dogfood (#62) + CI cross-runtime test (#63).
- v0.4: renamed `vd:pursue` → `vd:ultracook`, absorbing the former orchestration skill. Added the **conductor** front-end - `direct`/`pipeline`/`fan-out` triage (`references/conductor.md`), brainstorm-first spine, parallel fan-out packets, and research-backed per-runtime autonomy mapping (Claude Code permission posture; Codex `--ask-for-approval`/`--sandbox`). Env `PURSUE_*` → `ULTRACOOK_*`, sentinel `.pursue/` → `.ultracook/`.
