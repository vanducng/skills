# JSON shapes

Every command prints one object. Field names come from Structured Cloud and pass through unchanged, so a newer server field shows up without a CLI release.

## Task

```json
{
  "ref": "2304478a-0636-4a2d-b9a1-903c247b0305@2026-10-23",
  "id": "62286ecb-e217-41c6-b80e-2b513068ad8a",
  "recurring_id": "2304478a-0636-4a2d-b9a1-903c247b0305",
  "is_recurring": true,
  "title": "Read 20 pages",
  "note": "",
  "day": "2026-10-23",
  "start_time": null,
  "duration": 0,
  "is_all_day": true,
  "is_in_inbox": false,
  "is_completed": false,
  "completed_at": null,
  "color": "forest",
  "symbol": "text.badge.checkmark",
  "energy_level": 0,
  "subtasks": [],
  "external_calendar_id": null,
  "order_index": null
}
```

| Field | Meaning |
| --- | --- |
| `ref` | Added by the CLI. The value to pass as `REF`. A plain id for one-off tasks, `RECURRING_ID@DAY` for one day of a series. |
| `id` | Present on recurring days too. Do not use it to edit a recurring day; use `ref`. |
| `start_time` | Hours from midnight in the local timezone. `8.5` is 08:30. `null` for all-day and inbox tasks. |
| `duration` | Minutes, 0 to 1439. |
| `is_completed` | Normalised by the CLI from `completed_at`. |
| `subtasks[].completed_at` | `null` when open. |
| `external_calendar_id` | Set for calendar-imported events. Deleting one only hides it in Structured. |
| `energy_level` | -1 rest, 0 neutral, 1 low, 2 medium, 3 high. |

## Lists

```json
{ "ok": true, "tasks": [ { "...": "task" } ], "truncated": false }
```

`truncated` appears on `list` and is true when `--limit` was reached.

`subtask list` prints `{ "ok": true, "ref": "...", "title": "...", "subtasks": [ { "n": 1, "id": "...", "title": "...", "completed_at": null, "done": false } ] }`.

## Writes

Every write prints one envelope:

```json
{ "ok": true, "result": { "operation": "updated", "scope": "series", "ref": "2304…@2026-10-23", "task": { "...": "task, with ref" } } }
```

| Field | Meaning |
| --- | --- |
| `operation` | `created`, `completed`, `reopened`, `updated`, `deleted`, `detached`, `subtask done`, `subtasks added`, and so on |
| `scope` | `task` for a one-off task, `day` for one recurring day, `series` for every repeat |
| `ref` | the task's ref after the write. After `detached`, it is the new standalone task's id |
| `task` | the server's copy, when it returned one |

`--dry-run` adds `"dry_run": true`, `"tool"`, and `"arguments"`, and sends nothing.

## Errors (stderr)

```json
{ "ok": false, "error": { "code": "NOT_FOUND", "message": "task 7c0e… not found in the inbox, upcoming days, or the last 60 days", "retryable": false, "next_steps": ["structured today --json", "structured list --from YYYY-MM-DD --json"] } }
```
