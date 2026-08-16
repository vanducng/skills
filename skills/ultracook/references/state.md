# state.json schema (v2)

One file per goal: `<state-base>/<slug>/state.json`. It is the single source of truth for "where are we" and survives context compaction - resume means "read this file, continue from the first non-done stage."

State base resolves in order: `$VD_STATE_PATH` → `<git-root>/.workbench/state` when `.workbench/` exists → `$XDG_STATE_HOME/vd/ultracook/<repo-id>/goals` (`~/.local/state/...` by default). Never write ultracook state into the project tree outside `.workbench/`.

All writes go through `scripts/update-state.sh` (`init` for creation, `patch` for merge-patch updates - atomic tmp+rename, auto-sets `updated_at`).

## Shape

```json
{
  "version": 2,
  "goal": "implement settings export, ship to staging, verify",
  "mode": "pipeline",
  "autonomy": "semi",
  "branch": "feat/settings-export",
  "worktree": "/path/to/worktree or null",
  "plan_dir": "path once vd:plan has run, else null",
  "pr_url": null,
  "stages": [
    { "skill": "plan",        "status": "done",    "done_when": "plan files written and user approved (Plannotator or gate)", "evidence": "plans/260816-0930-settings-export/ approved" },
    { "skill": "cook",        "status": "running", "done_when": "all phases completed and eval-dod.sh exits 0",              "evidence": null },
    { "skill": "code-review", "status": "pending", "done_when": "review pass with no blocking findings",                     "evidence": null },
    { "skill": "ship",        "status": "pending", "done_when": "PR open and CI green",                                      "evidence": null }
  ],
  "iteration_count": 4,
  "last_failure_signature": "cook|npm test|1",
  "last_failure_count": 1,
  "terminal": null,
  "terminal_reason": null,
  "created_at": "2026-08-16T06:00:00Z",
  "updated_at": "2026-08-16T06:40:00Z"
}
```

## Field notes

- **`stages`** - the flow, in order. Each entry is a *skill name* plus a checkable `done_when` gate and, once done, one line of `evidence`. Stage `status`: `pending` / `running` / `done` / `failed` / `skipped`. Adding a capability to ultracook = adding a stage entry naming a skill - no vocabulary to extend.
- **`done_when`** - must be checkable ("all tests pass", "PR open and CI green"), never "proceed if confident". Prefer delegating the check to the stage skill's own gate (cook's `eval-dod.sh`, ship's CI watch).
- **`evidence`** - one line of proof captured when the stage completes ("go test → 142 passed", "PR #91 CI green"). Enough for `status.sh` to answer "how do we know?" without re-reading transcripts.
- **`iteration_count`** - incremented per stage attempt including retries. Hard cap 30 → `blocked`.
- **`last_failure_signature`** / **`last_failure_count`** - the repeat-failure recognizer: signature = `stage|failing command|exit code`. Three identical signatures in a row → `blocked` (don't burn iterations re-hitting the same wall; surface it).
- **`terminal`** - `null` (in progress) / `done` / `blocked` / `abandoned`, with `terminal_reason` set whenever non-null. `kill.sh` sets `abandoned` and drops `cancel.sentinel` for any loop still watching.
- **`autonomy`** - `manual` / `semi` / `auto`; editable mid-flight (the executor re-reads state each iteration). See `autonomy-modes.md`.

## Crash recovery

If `state.json.tmp` exists, the previous write crashed - `update-state.sh` refuses to proceed and prints the recovery step (delete the tmp; `state.json` still holds the last good state).
