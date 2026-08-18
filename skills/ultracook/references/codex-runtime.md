# Codex runtime - v0.2 (shipped)

`vd:ultracook` v0.2 ships **Claude Code + Codex TUI parity** via a Dual-SKILL.md architecture: top-level `SKILL.md` is a router that detects the runtime and dispatches to `runtimes/claude-code.md` or `runtimes/codex.md`. Bash scripts + references + project profiles are shared across both runtimes verbatim.

## What's supported on Codex (TUI)

| Feature | Status | Notes |
|---|---|---|
| Skill discovery | ✓ | `vd install codex ultracook` symlinks into `~/.agents/skills/ultracook/` (auto-discovered) |
| Intake (4 ask_user_question prompts) | ✓ | Mirrors Claude Code's AskUserQuestion flow |
| Sequential executor | ✓ | Same protocol as Claude Code; all 22 actions wired |
| Skill-to-skill dispatch (`vd:plan`, `vd:cook`, etc.) | ✓ | Via `codex exec resume --last "use vd:<skill> ..."` - see Workaround 1 |
| Loop primitive (cook+verify iteration) | ✓ | Delegates to `vd:auto-loop --codex` → native `/goal` |
| Monitor analog (wait_ci, image_build_wait, rollout_check) | ✓ | PostToolUse hook + `additionalContext` - see Workaround 2 |
| Subagent dispatch (code-reviewer, audit) | ✓ | Native Codex subagents |
| Push notifications (terminal=blocked) | ✓ | `scripts/notify.sh` - terminal-notifier / ntfy / Slack / log fallback |
| Token telemetry per action | ✓ | `--json` event-stream parsing via `codex-bridge.sh json-parse` |
| Cross-session resume | ✓ | Via on-disk `state.json` (no Codex-specific state) |
| Cross-runtime resume (Claude ↔ Codex same goal) | ✓ | Phase 5 keystone test |

## v0.3 (shipped)

- **`codex exec` (non-interactive) parity** - `detect-runtime.sh` emits `codex-exec` when the explicit exec contract is set (`ULTRACOOK_EXEC=1` / `ULTRACOOK_RUNTIME=codex-exec`). In that mode ultracook skips the `ask_user_question` intake and reads default-answer flags instead. See "CI / non-interactive usage" below.
- **`install-hooks` sub-verb** - `vd:ultracook install-hooks [--apply|--uninstall]` registers the Codex hooks in `~/.codex/config.toml` (marker-wrapped append, backup + re-parse guard, symlink-aware). Replaces the manual edit below.
- **Codex /goal cancel propagation** - `vd:ultracook kill` now writes a `cancel.sentinel` (before flipping terminal) that `codex-monitor-hook.sh` reads to halt the loop on the next PostToolUse turn, and prints a loud "also run `/goal cancel`" instruction. Cooperative only - codex CLI exposes no programmatic `/goal` cancel.
- **Multi-goal disambiguation** - `vd:ultracook status --all` (alias `--list`) enumerates every goal-dir; bare-resume lists in-flight goals to pick when more than one is non-terminal.
- **Plugin marketplace vs symlink conflict detection** - `scripts/check-install-conflicts.sh` (run by `scripts/install.sh`) warns when a skill is installed BOTH as a vd symlink and a marketplace plugin copy.

## Still deferred (v0.3+)

- **Automated CI cross-runtime test** (#63) - blocked on a real dual-runtime dogfood (#62) and now on exercising the `codex-exec` default-answer path end-to-end in CI.
- **Real cross-runtime TUI dogfood** (#62) - the bash-level keystone is proven; the live Claude⇄Codex TUI handoff is still unrun.

## vs Claude Code

The semantic shape is identical - same `goal.yaml` / `state.json` / `iterations/` layout, same 21-action vocabulary, same verifier types. The differences are mechanical (which tool primitive dispatches each kind):

| Surface | Claude Code | Codex |
|---|---|---|
| Interactive prompt | `AskUserQuestion` tool | `ask_user_question` (Codex native) |
| Skill invocation | `Skill` tool | `codex exec resume --last "use ..."` |
| Subagent | `Agent` tool | Native Codex subagent |
| Long-running wait | `Monitor` tool | PostToolUse hook + additionalContext |
| Loop primitive | `vd:auto-loop` Stop hook | `vd:auto-loop --codex` → native /goal |
| Push notification | (Claude Code may add native; today: `notify.sh`) | `notify.sh` |

Performance: comparable. Token usage on Codex ~10-20% higher per goal due to `/goal` overhead (acceptable; documented in Phase 5 dogfood notes).

## Setup

After installing the skill, register the Codex hooks:

```bash
vd:ultracook install-hooks            # detect + print the block (no write)
vd:ultracook install-hooks --apply    # append it to ~/.codex/config.toml (backup + re-parse guard)
```

`install-hooks` is symlink-aware (resolves a dotfiles-symlinked config to its real target and warns), idempotent (marker-wrapped block), and reversible (`--uninstall`). Restart your Codex session after `--apply`; Codex will prompt to trust the new hook commands on first run.

Without hooks, Monitor-style actions (`wait_ci`, `image_build_wait`, `rollout_check`) won't get status updates. They'll still execute, but the executor blocks until they exit instead of getting event-driven updates.

## CI / non-interactive usage (`codex exec`)

`ask_user_question` is unavailable under `codex exec`. Set the exec contract and pass the intake answers as flags so ultracook skips the interactive intake:

```bash
ULTRACOOK_EXEC=1 codex exec "vd:ultracook '<goal>' \
  --target-kind=pr-only --action-shape=plan-only --autonomy=semi [--branch=<b>] [--reuse-worktree]"
```

`scripts/intake-complete.sh` validates the required trio (`--target-kind`, `--action-shape`, `--autonomy`); a missing or invalid value refuses with an actionable message rather than silently falling back to intake. `detect-runtime.sh` only emits `codex-exec` under the explicit contract - there is no env var distinguishing `codex exec` from the `codex` TUI, so it is never inferred from TTY/process state.

## See also

- `references/codex-gap-workarounds.md` - concrete workaround details (4 workarounds + isolation tests + limitations)
- `runtimes/codex.md` - the executor body
- `runtimes/detect.md` - runtime detection precedence
- `~/skills/plans/260525-1501-ultracook-v0.2-codex/` - v0.2 plan + dogfood notes
- `~/skills/plans/reports/researcher-260525-1446-ultracook-v0.2-codex-adapter.md` - original research that justified the v0.2 design

## Open questions

- Codex `ask_user_question` UX divergence from Claude Code's AskUserQuestion (tab navigation, default selection) - to be measured in Phase 5 dogfood.
- additionalContext budget under realistic CI-wait load (200-char cap per Monitor inject, many waits per goal) - measure in Phase 5.
- Skill-to-skill auto-match false-match rate (Codex picking wrong skill from description overlap) - measure in Phase 5.
