# Native Codex orchestration — recipes

Fallbacks for when you don't need (or haven't installed) the `run_workflow` orchestrator. All native to Codex CLI 0.142+.

## `spawn_agents_on_csv` (deterministic batch)

One worker subagent per CSV row; combined results exported. Each worker MUST call `report_agent_job_result` exactly once — a worker that exits without reporting marks its row an error.

Params:
- `csv_path` — source rows
- `instruction` — worker prompt with `{column_name}` placeholders
- `id_column` — stable per-row id
- `output_schema` — expected JSON result shape (validated)
- `output_csv_path`, `max_concurrency`, `max_runtime_seconds`

Errors land in the output CSV with `status`, `last_error`, `item_id`. Ideal for "review/audit/transform one file|package|service per row."

## `worktree + codex exec &` (collision-free parallel implementation)

```bash
for task in auth-fix search-index export-csv; do
  git worktree add "../$task" -b "$task"
  (cd "../$task" && codex exec --sandbox workspace-write \
    "Implement the $task ticket. Run tests before finishing.") &
done
wait
```

Each agent writes in its own worktree — no mid-flight merge collisions. Pair with `vd:worktree` for standardized `.worktrees/` + port blocks. Worktrees solve *collision*, not *coordination*: keep a mental map of what's merged.

## `codex exec --json --output-schema` (headless, scriptable)

```bash
codex exec --json --output-schema ./schema.json -o ./out.json "Extract metadata"
```

JSONL events on stdout (`thread.started`, `turn.completed`, `item.*`, `error`); final response validated against the schema. Resumable: `codex exec resume --last`. This is what `run_workflow` drives under the hood.

## `[agents]` config

```toml
[agents]
max_threads = 4   # concurrent subagent cap
max_depth   = 1   # nesting depth — keep at 1; raising it multiplies tokens/latency
job_max_runtime_seconds = 900
```

## Custom agent roles

`~/.codex/agents/<name>.toml` — `name`, `description`, `developer_instructions` (+ optional `model`, `sandbox_mode`, `mcp_servers`). Built-ins: `default`, `worker`, `explorer`. Deployed from `~/skills/agents/` by `vd install codex`.

### #26363 workaround (while open)
Since v0.137.0 these aren't selectable at spawn. To use a role's behavior, read its `developer_instructions` and inject them as a prompt override on a generic spawn:

```
Spawn a worker with these instructions: <paste developer_instructions of code-reviewer.toml>. Task: review src/auth.go.
```

`run_workflow` does this automatically when a step names an `agent`.

## Limits (when it breaks down)
- Beyond ~5 concurrent agents, unreviewed output accumulates faster than value.
- Tight inter-task dependencies: worktree isolation doesn't solve coordination.
- Parallel agents can't react to each other mid-run.
- No free parallelism — every subagent spends its own tokens.
