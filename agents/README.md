# Codex subagent definitions

Custom Codex CLI subagents (`name` / `description` / `developer_instructions` TOMLs). Source of truth — deployed to `~/.codex/agents/` by `vd install codex` (vd-cli `DeployCodexAgents`).

These mirror the Claude Code agent types so the same roles (planner, researcher, code-reviewer, tester, …) are available when Codex spawns subagents or when the `codex-workflow` orchestrator injects a role's `developer_instructions`.

> Codex regression [#26363](https://github.com/openai/codex/issues/26363): since v0.137.0 these aren't selectable at in-session spawn (generic fallback). The `codex-workflow` orchestrator works around it by injecting `developer_instructions` as a prompt override; see the `codex-workflow` skill.
