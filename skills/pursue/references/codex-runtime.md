# Codex runtime — v0.2 (shipped)

`vd:pursue` v0.2 ships **Claude Code + Codex TUI parity** via a Dual-SKILL.md architecture: top-level `SKILL.md` is a router that detects the runtime and dispatches to `runtimes/claude-code.md` or `runtimes/codex.md`. Bash scripts + references + project profiles are shared across both runtimes verbatim.

## What's supported on Codex (TUI)

| Feature | Status | Notes |
|---|---|---|
| Skill discovery | ✓ | `vd install codex pursue` symlinks into `~/.agents/skills/pursue/` (auto-discovered) |
| Intake (4 ask_user_question prompts) | ✓ | Mirrors Claude Code's AskUserQuestion flow |
| Sequential executor | ✓ | Same protocol as Claude Code; all 21 actions wired |
| Skill-to-skill dispatch (`vd:plan`, `vd:cook`, etc.) | ✓ | Via `codex exec resume --last "use vd:<skill> ..."` — see Workaround 1 |
| Loop primitive (cook+verify iteration) | ✓ | Delegates to `vd:auto-loop --codex` → native `/goal` |
| Monitor analog (wait_ci, image_build_wait, rollout_check) | ✓ | PostToolUse hook + `additionalContext` — see Workaround 2 |
| Subagent dispatch (code-reviewer, audit) | ✓ | Native Codex subagents |
| Push notifications (terminal=blocked) | ✓ | `scripts/notify.sh` — terminal-notifier / ntfy / Slack / log fallback |
| Token telemetry per action | ✓ | `--json` event-stream parsing via `codex-bridge.sh json-parse` |
| Cross-session resume | ✓ | Via on-disk `state.json` (no Codex-specific state) |
| Cross-runtime resume (Claude ↔ Codex same goal) | ✓ | Phase 5 keystone test |

## What's NOT yet (v0.3+)

- **`codex exec` (non-interactive) parity** — `ask_user_question` is unavailable in exec mode. v0.2 intake refuses + suggests interactive `codex` TUI. v0.3 ships default-answer-mode flags for CI.
- **Cross-runtime DAG / multi-goal concurrency** — v0.3+.
- **Automated CI cross-runtime test** — v0.2 manually dogfood-validated only.
- **Plugin marketplace vs `vd install` symlink conflict resolution** — v0.3.
- **Codex /goal native pause/resume integration with pursue's kill sub-verb** — pursue kill writes terminal=abandoned; user must also `/goal cancel` manually on Codex. v0.3 wires this.
- **`install-hooks` sub-verb** — v0.2 ships hook scripts but user must manually register them in `~/.codex/config.toml`. v0.3 automates.

## vs Claude Code

The semantic shape is identical — same `goal.yaml` / `state.json` / `iterations/` layout, same 21-action vocabulary, same verifier types. The differences are mechanical (which tool primitive dispatches each kind):

| Surface | Claude Code | Codex |
|---|---|---|
| Interactive prompt | `AskUserQuestion` tool | `ask_user_question` (Codex native) |
| Skill invocation | `Skill` tool | `codex exec resume --last "use ..."` |
| Subagent | `Agent` tool | Native Codex subagent |
| Long-running wait | `Monitor` tool | PostToolUse hook + additionalContext |
| Loop primitive | auto-loop's Stop hook | auto-loop --codex → native /goal |
| Push notification | (Claude Code may add native; today: `notify.sh`) | `notify.sh` |

Performance: comparable. Token usage on Codex ~10-20% higher per goal due to `/goal` overhead (acceptable; documented in Phase 5 dogfood notes).

## Setup

After `vd install codex pursue`, register the Codex hooks in your config:

```toml
# ~/.codex/config.toml
[[hooks]]
event = "PostToolUse"
command = "bash ~/.agents/skills/pursue/scripts/codex-monitor-hook.sh"

[[hooks]]
event = "SessionStart"
command = "bash ~/.agents/skills/pursue/scripts/codex-hook-cleanup.sh"
```

Without hooks, Monitor-style actions (`wait_ci`, `image_build_wait`, `rollout_check`) won't get status updates. They'll still execute, but the executor blocks until they exit instead of getting event-driven updates.

v0.3 will ship an `install-hooks` sub-verb that does this automatically.

## See also

- `references/codex-gap-workarounds.md` — concrete workaround details (4 workarounds + isolation tests + limitations)
- `runtimes/codex.md` — the executor body
- `runtimes/detect.md` — runtime detection precedence
- `~/skills/plans/260525-1501-pursue-v0.2-codex/` — v0.2 plan + dogfood notes
- `~/skills/plans/reports/researcher-260525-1446-pursue-v0.2-codex-adapter.md` — original research that justified the v0.2 design

## Open questions

- Codex `ask_user_question` UX divergence from Claude Code's AskUserQuestion (tab navigation, default selection) — to be measured in Phase 5 dogfood.
- additionalContext budget under realistic CI-wait load (200-char cap per Monitor inject, many waits per goal) — measure in Phase 5.
- Skill-to-skill auto-match false-match rate (Codex picking wrong skill from description overlap) — measure in Phase 5.
