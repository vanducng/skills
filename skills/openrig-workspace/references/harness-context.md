# Harness context discovery

Checked 2026-09. Re-check when a harness changes its docs.

| Harness | Reads | Above cwd | Below cwd | Source |
|---|---|---|---|---|
| Pi | `AGENTS.md`/`CLAUDE.md` in agent dir, cwd, and every parent. Skills: `.agents/skills` from cwd up to the repo root, plus `~/.agents/skills` | yes, no git boundary | no | Pi `docs/configuration.md`, `docs/skills.md` |
| Claude Code | `CLAUDE.md`/`CLAUDE.local.md` in cwd and every parent. `AGENTS.md` too, but only when no `CLAUDE.md` exists in cwd or above (default "Project instructions" setting) | yes | on demand, when it reads files there | code.claude.com/docs/en/memory |
| Codex | `~/.codex/AGENTS.md`, then git root down to cwd. With no git root, cwd only. 32 KiB cap (`project_doc_max_bytes`) | up to git root | no | learn.chatgpt.com/docs/agent-configuration/agents-md |
| Grok Build | home rules, then repo root down to cwd; reads both `AGENTS.md` and `CLAUDE.md`. With no git root, cwd only. Needs folder trust. Skills walk `.agents/skills` up to the repo root | up to git root | no | xai-org/grok-build `docs/user-guide/12-project-rules.md`, `08-skills.md` |
| Cursor | `AGENTS.md` at the workspace root and nested subdirs (applied when working with files there), `.cursor/rules/*.mdc` | not documented | yes | cursor.com/docs/rules |
| OpenRig seat | writes managed blocks into `<seat cwd>/AGENTS.md` on every launch, whatever the agent spec says | n/a | n/a | OpenRig 0.5.x `rigspec-instantiator.ts` |

## Consequences for the layout

- The only chain every harness reads is git root down to cwd. Putting task dirs inside the workspace repo makes org and project `AGENTS.md` load for Codex and Grok as well as for Pi and Claude.
- One `CLAUDE.md` anywhere in the chain switches Claude off `AGENTS.md`, so the workspace uses `AGENTS.md` only.
- When you start a harness inside a repo worktree that tracks `CLAUDE.md`, Claude reads only the `CLAUDE.md` chain, and task, project, and org `AGENTS.md` are skipped. Start from the task dir, or set Claude's "Project instructions" to `claude-md-and-agents-md` in `/config`.
- Setting an OpenRig seat's cwd to the task dir keeps its managed blocks out of tracked repo files.
- `rg` from a task dir finds files inside nested worktrees even though the parent repo ignores `tasks/`. A search that starts above the ignored path skips them.
