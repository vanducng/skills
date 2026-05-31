# state.json schema (v1)

Mutable runtime state for a pursue goal. Updated every iteration via atomic write protocol. Round-trips across context compaction; source of truth for "where are we now?"

## Top-level keys

| Key | Type | Description |
|---|---|---|
| `version` | int | Schema version. Always `1` for v0.1. |
| `terminal` | enum or null | `null` (in-progress) / `done` / `blocked` / `abandoned`. |
| `terminal_reason` | string or null | Free-text explanation. Set when terminal != null. |
| `current_phase` | string | High-level stage. e.g. `intake-complete`, `executing`, `delegating-to-auto-loop`. |
| `current_action` | string or null | The action being executed right now. `null` after intake; first set when executor starts Phase 3. |
| `iteration_count` | int | Total actions executed (incremented per action attempt, including retries). |
| `budgets_consumed` | object | Per-budget counter. See "budgets_consumed" below. |
| `last_failure_signature` | string or null | The repeat-fail recognizer's hash of the last failure (action + verifier + exit code). |
| `last_failure_count` | int | How many times the same signature has fired in a row. 3 → `blocked`. |
| `last_action_result` | object or null | See "last_action_result" below. Most recent action's outcome. |
| `journal_path` | string | Relative path from goal-dir to the iterations dir. Always `iterations/`. |
| `pr_number` | int or null | Set when `ship` action lands a PR. Read by `ci_green` verifier. |
| `updated_at` | RFC3339 datetime | Set by `update-state.sh` on every write. |

## `budgets_consumed`

```json
{
  "rebases": 0,
  "ci_reruns": 0,
  "token_pct": 0
}
```

Mirrors `goal.yaml.budgets` keys. The executor compares before each action; if any consumed >= cap → `blocked`.

## `last_action_result`

```json
{
  "action": "cook",
  "started_at": "2026-05-25T14:00:00+07:00",
  "finished_at": "2026-05-25T14:08:23+07:00",
  "exit_code": 0,
  "verifier_pass": true,
  "verifier_evidence": "go test ./... → 142 passed, 0 failed",
  "journal_entry": "iterations/003-cook.md"
}
```

Sufficient for `vd:pursue status` to print a one-line summary without re-reading journal files.

## Worked example: after Phase 1 intake

```json
{
  "version": 1,
  "terminal": null,
  "terminal_reason": null,
  "current_phase": "intake-complete",
  "current_action": null,
  "iteration_count": 0,
  "budgets_consumed": { "rebases": 0, "ci_reruns": 0, "token_pct": 0 },
  "last_failure_signature": null,
  "last_failure_count": 0,
  "last_action_result": null,
  "journal_path": "iterations/",
  "pr_number": null,
  "updated_at": "2026-05-25T13:50:00+07:00"
}
```

## Worked example: mid-cook iteration with one failure

```json
{
  "version": 1,
  "terminal": null,
  "terminal_reason": null,
  "current_phase": "executing",
  "current_action": "cook",
  "iteration_count": 4,
  "budgets_consumed": { "rebases": 0, "ci_reruns": 0, "token_pct": 23 },
  "last_failure_signature": "cook|test_suite_passes|1",
  "last_failure_count": 1,
  "last_action_result": {
    "action": "cook",
    "started_at": "2026-05-25T14:00:00+07:00",
    "finished_at": "2026-05-25T14:08:23+07:00",
    "exit_code": 0,
    "verifier_pass": false,
    "verifier_evidence": "go test ./... → 141 passed, 1 failed: TestCronRetryBackoff",
    "journal_entry": "iterations/004-cook.md"
  },
  "journal_path": "iterations/",
  "pr_number": null,
  "updated_at": "2026-05-25T14:08:25+07:00"
}
```

## Terminal example: done

```json
{
  "version": 1,
  "terminal": "done",
  "terminal_reason": "All workflow-level verifiers passed (ci_green, pod_image_matches, http_status)",
  "current_phase": "completed",
  "current_action": "done",
  "iteration_count": 11,
  ...
  "updated_at": "2026-05-25T16:42:00+07:00"
}
```

## Atomic write protocol

`scripts/update-state.sh` enforces:

```bash
# 1. Read current state.
# 2. Apply JSON-merge-patch from stdin.
# 3. Validate result against this schema (version=1, terminal in enum).
# 4. Write to state.json.tmp in the SAME directory as state.json.
# 5. mv state.json.tmp state.json   (atomic on POSIX same-fs).
# 6. Set updated_at to now() during the merge.
```

`mv` is atomic on the same filesystem; do NOT put goal dirs on different filesystems than `/tmp`. The script uses the goal-dir's own filesystem for the `.tmp` file.

**Concurrent writers:** v0.1 assumes single-writer. Multi-goal concurrency in the same repo is a v0.2 concern with file-level locking.

**Crash recovery:** if `state.json.tmp` exists and `state.json` does not, the previous write crashed. The script refuses to proceed and prints the manual recovery step (delete the .tmp, re-derive state from `goal.yaml` + `iterations/`).

## Schema evolution

`version: 1` is reserved for v0.1. Future schema bumps go through:

1. Add `version: 2` writer.
2. `update-state.sh` reads `version: 1` files and migrates in-memory before merging.
3. CHANGELOG entry documents the migration.

Mid-flight goal files are migrated on next iteration; no separate migration tool.
