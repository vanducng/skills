# Subagent definitions

Source of truth for the same 14 subagent roles on both runtimes:

- `*.toml` — Codex CLI subagents (`name` / `description` / `developer_instructions`). Deployed to `~/.codex/agents/` by `vd install codex` (vd-cli `DeployCodexAgents`).
- `*.md` — Claude Code subagents (YAML frontmatter + body). Symlinked into `~/.claude/agents/` by `scripts/install.sh`.

The two sets are hand-maintained parallel copies, not generated from each other. A route/skill change must land in both files for that role.

These mirror the Claude Code agent types so the same roles (planner, researcher, code-reviewer, tester, …) are available when Codex spawns subagents or when the `codex-workflow` orchestrator injects a role's `developer_instructions`.

> Codex regression [#26363](https://github.com/openai/codex/issues/26363): since v0.137.0 these aren't selectable at in-session spawn (generic fallback). The `codex-workflow` orchestrator works around it by injecting `developer_instructions` as a prompt override; see the `codex-workflow` skill.
