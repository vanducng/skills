# state.json schema (v2)

One file per goal. Source of truth for "where are we now?" after context compaction.

v1 (`current_action`, `goal.yaml`, closed action names) is retired. New runs write v2 only. Old v1 files can be listed by `status.sh --all` but are not resumed - start a new goal.

## Top-level keys

| Key | Type | Description |
|---|---|---|
| `version` | int | Always `2` |
| `goal` | string | Short goal text |
| `mode` | string | `direct` (should not have a file) / `pipeline` / `fan-out` |
| `autonomy` | string | `manual` / `semi` / `auto` |
| `terminal` | enum or null | `null` (in-progress) / `done` / `blocked` / `abandoned` |
| `terminal_reason` | string or null | Set when terminal != null |
| `current_stage` | string or null | Stage `id` now running |
| `iteration_count` | int | Stages attempted, including retries |
| `stages` | array | See below |
| `created_at` | RFC3339 | Set on `--init` |
| `updated_at` | RFC3339 | Set on every write |

## Stage object

| Key | Type | Description |
|---|---|---|
| `id` | string | Stable handle (`plan`, `cook`, `ship`) |
| `skill` | string | Canonical skill id (`vd:plan`) plus flags if needed (`vd:cook --auto`) |
| `done_when` | string | Checkable completion criterion |
| `status` | string | `pending` / `in_progress` / `done` / `skipped` |
| `evidence` | string or omitted | Pointer that proves `done_when` (command output summary, path, URL) |

Resume = first stage whose status is neither `done` nor `skipped`.

## Worked example

```json
{
  "version": 2,
  "goal": "add export-to-csv on the settings page",
  "mode": "pipeline",
  "autonomy": "semi",
  "terminal": null,
  "terminal_reason": null,
  "current_stage": "cook",
  "iteration_count": 2,
  "stages": [
    {
      "id": "plan",
      "skill": "vd:plan",
      "done_when": "plan.md exists with phases and a Definition of Done block",
      "status": "done",
      "evidence": "plans/260822-1012-settings-csv/plan.md"
    },
    {
      "id": "cook",
      "skill": "vd:cook",
      "done_when": "eval-dod.sh exits 0 on the plan",
      "status": "in_progress"
    },
    {
      "id": "ship",
      "skill": "vd:ship",
      "done_when": "PR url recorded and checks green",
      "status": "pending"
    }
  ],
  "created_at": "2026-08-22T10:12:00Z",
  "updated_at": "2026-08-22T10:40:00Z"
}
```

## Scripts

```bash
# create
cat state.json | bash scripts/update-state.sh --init --goal-dir "$GOAL_DIR"

# patch (JSON merge; stages array is replaced when present)
echo '{"iteration_count": 3}' | bash scripts/update-state.sh --goal-dir "$GOAL_DIR"

# status / kill
bash scripts/status.sh [--goal-dir "$GOAL_DIR"] [--all]
bash scripts/kill.sh --goal-dir "$GOAL_DIR" --reason "user stop"
```

`update-state.sh` refuses a crashed prior write (`state.json.tmp` present). `kill.sh` refuses to overwrite a non-null `terminal`.
