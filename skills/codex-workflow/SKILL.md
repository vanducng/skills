---
name: codex-workflow
description: "Run deterministic multi-step agent workflows in Codex — fan-out, parallel, schema-validated structured output — via the codex-workflow MCP orchestrator (run_workflow), with native in-chat fallbacks. Use when you want Claude-Code-Workflow-style orchestration in Codex: 'run a workflow', 'fan out subagents', 'review each file in parallel', 'orchestrate these steps'. Triggers: 'codex-workflow', 'run_workflow', 'orchestrate in codex'."
license: MIT
metadata:
  author: vanducng
  version: "1.0.0"
---

# Codex Workflow

Deterministic multi-agent orchestration in Codex — the analog of Claude Code's Workflow tool. Pick the right level for the job.

## Three levels (cheapest first)

| Need | Use | Determinism |
|---|---|---|
| Ad-hoc "spawn one agent per X, summarize" in a chat | **native NL spawn** | low (model decides) |
| Fixed fan-out over a worklist (one worker per row, schema'd) | **`spawn_agents_on_csv`** | medium |
| Collision-free parallel *implementation* | **`worktree + codex exec &`** | high (isolated) |
| Scripted multi-step pipeline with structured output you parse | **`run_workflow`** (the orchestrator MCP) | high |

Reach for `run_workflow` when you'd otherwise hand-wire `codex exec` calls; reach for the native paths for quick in-session work.

## `run_workflow` — the orchestrator

Installed as the `codex-workflow` MCP extension (`vd mcp install codex-workflow`). Call the `run_workflow` tool with a spec:

```jsonc
{
  "steps": [
    { "id": "scan",   "prompt": "List changed files vs main.", "output_schema": {"type":"object","properties":{"files":{"type":"array"}}} },
    { "id": "review", "prompt": "Review {file} for bugs.", "agent": "code-reviewer", "parallel_group": "g1" }
  ]
}
```

- **v1 shape:** sequential steps + one `parallel_group` + per-step `output_schema`. NOT loops/conditionals (those are a later iteration — script them outside, or use multiple `run_workflow` calls).
- `agent` (optional) names a `~/.codex/agents/*.toml` role; its `developer_instructions` are injected as a prompt override (see #26363 below).
- Concurrency is capped by `[agents].max_threads` (config).
- Returns one structured result per step: `{id, status, output}`.

## Native fallbacks (no orchestrator needed)

### `spawn_agents_on_csv` — deterministic batch
One worker per CSV row; each calls `report_agent_job_result` exactly once. Params: `csv_path`, `instruction` (with `{column}` placeholders), `id_column`, `output_schema`, `output_csv_path`, `max_concurrency`. Best for "review/audit/transform one file|package|service per row." See [references/native-orchestration.md](references/native-orchestration.md).

### `worktree + codex exec &` — collision-free parallel writes
Pairs with `vd:worktree`. One worktree + background `codex exec` per task; `wait`. Each agent writes in isolation, no merge collisions mid-flight.

### Natural-language spawn
"Spawn one agent per review point, wait for all, summarize each." Codex orchestrates spawn/route/wait/close. Lowest ceremony, lowest determinism — keep fan-out at **3–5** (token cost is linear; human review is the real ceiling).

## Patterns (translated from Claude's Workflow)
- **Loop-until-dry:** repeat a finder step until K rounds return nothing new (script with repeated `run_workflow` calls).
- **Adversarial N-vote verify:** a parallel_group of N skeptics per finding; keep if majority confirm.
- **Multi-modal sweep:** parallel steps each searching a different way, blind to each other.
- **Pipeline:** chain `run_workflow` calls, feeding step outputs forward.

## Caveat — regression #26363 (while open)
Since Codex v0.137.0, custom `~/.codex/agents/*.toml` are not selectable at in-session spawn (generic fallback). `run_workflow` works around it by injecting the named agent's `developer_instructions` as a prompt override. For raw NL spawns, do the same by hand: paste the role's instructions into the spawn prompt. Drop this workaround when OpenAI restores `agent_type` selection.

## Integration
- **Composes:** `vd:worktree` (parallel writes), the `~/.codex/agents/*.toml` roles.
- **Install/manage:** `vd mcp install|list|doctor codex-workflow`.
- **Not this:** FableCodex (a workflow-discipline gate, separate skill).
