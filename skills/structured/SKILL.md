---
name: structured
description: "Operate the Structured day planner through the structured CLI: read a day or the inbox, show the plan to a person as a text timeline, and, with explicit authorization, create, edit, complete, or delete tasks and their subtasks. Use when the user mentions Structured tasks, their day plan, subtasks or checklists in Structured, the Structured TUI, or a structured CLI error. Reads are safe. Writes need explicit user authorization."
license: MIT
argument-hint: "<Structured read, plan review, or authorized change>"
metadata:
  author: vanducng
  version: "0.2.0"
  binary: structured
---

# structured

Use the `structured` binary. `structured <command> --help` is the flag contract. Do not call the Structured MCP server directly.

```text
  agent ── structured ... --json ──▶ Structured Cloud ◀── Structured apps
    │                                      ▲
    └─ structured today --text ──▶ person  │
                                    person reviews and fixes in `structured` (TUI)
```

## Start

```bash
command -v structured && structured --version
structured today --json
```

Missing binary: install the latest GitHub release archive for this machine, or `cargo install --git https://github.com/vanducng/structured`.

If stderr has `"code":"AUTH"`, ask the user to run `structured login` in their own terminal. It opens a browser. Never run login from an agent shell. Never read, print, or commit `$XDG_CONFIG_HOME/structured/auth.json` (or `~/.config/structured/auth.json`).

## Output contract

- Success: one JSON object on stdout when `--json` is set or stdout is not a terminal. Lists are `{"ok":true,"tasks":[...]}` (`list` adds `"truncated"`). Every write is `{"ok":true,"result":{"operation","scope","ref","task"}}`, where `scope` is `task`, `day`, or `series`.
- Failure: one JSON object on stderr, argument errors included: `{"ok":false,"error":{"code","message","retryable","next_steps"}}`. Codes: `AUTH`, `USAGE`, `NOT_FOUND`, `API`, `NETWORK`, `IO`, `DATA`.
- Retry only when `retryable` is true. Otherwise follow `next_steps` in order. Usage errors exit 2, others exit 1.
- Every task carries `ref`. Pass that string back as `REF`. Do not build refs by hand. Field details: [references/json.md](references/json.md).

## Read

```bash
structured today --json
structured day tomorrow --json            # YYYY-MM-DD, today, tomorrow, yesterday, +N, -N
structured inbox --json
structured list --from today --to +7 --open --search standup --json
structured subtask list REF --json
```

Report counts, times, and refs. Keep task titles and notes out of logs unless the user asked to see them.

## Show the plan to a person

When the user asks "what's my day" or wants to review a plan, print the text view and paste it unchanged in a fenced `text` block. Do not rebuild it as a table.

```bash
structured today --text
structured day +1 --text
structured inbox --text
```

```text
Fri 23 Oct 2026 (today) · 4 tasks, 1 done · 4h 45m planned

  All day
                      [ ] Read 20 pages  repeats
  08:30-09:15    45m  [x] Team sync
  09:00-09:30    30m  [ ] Review the pull request  ! overlaps
                         · 3h 30m free
  13:00-16:30 3h 30m  [ ] Finish the billing export  (1/3)
                         [x] Map the fields
                         [ ] Write the backfill
                         [ ] Dry run on staging
```

How to read it: `[x]` is done. `(1/3)` counts finished subtasks. `repeats` is one day of a recurring task. `! overlaps` starts before the previous task ends. `· free` is an open gap of 30 minutes or more. `--- now HH:MM ---` marks the current time on today.

## Write

Create, edit, complete, reopen, or delete only after the user explicitly authorizes that operation. A read is not authorization. Confirm the target by `ref` before writing. When the person wants to see the exact change first, add `--dry-run`: reads still run, and the write prints `"dry_run": true` with the tool and arguments it would send.

```bash
structured add "Write the note" --day +1 --time 09:30 --duration 30 --subtask Outline --subtask Draft --json
structured add "Someday" --json                     # no day, time, or --all-day: inbox
structured done REF --json
structured undo REF --json
structured edit REF --title "New title" --time 10:00 --json
structured edit RID@2026-10-23 --time 07:00 --scope series --json   # a recurring day needs --scope
structured delete REF --yes --dry-run --json
structured delete REF --yes --json
structured subtask add REF "Draft" "Review" --json
structured subtask done REF 2 --json                # SUB is a 1-based number or a subtask id
structured subtask edit REF 2 "Review with Sam" --json
structured subtask delete REF 2 --yes --json
```

- `--time` alone schedules today. `--day` alone is all-day. Duration is 0 to 1439 minutes.
- `delete` and `subtask delete` refuse to run without `--yes`.
- The server replaces a task's whole checklist on every subtask write. The CLI reads the current list first and keeps existing ids, so run subtask commands one at a time per task. Prefer the subtask id over its number when the person may be editing the same checklist in the TUI.
- The default symbol is `text.badge.checkmark`. Use `--symbol` only with a code the user named.
- This CLI does not create recurring series.

### Recurring tasks

| Change on a `RECURRING_ID@DAY` ref | Scope |
| --- | --- |
| `done`, `undo`, `delete`, subtask ticks | that day only |
| `edit ... --scope day` | that day only; the day is split off the series and gets a new `ref` |
| `edit ... --scope series` | every repeat; moves (`--move-day`, `--inbox`) are refused |
| add, rename, or remove a subtask | that day only (splits it off, Pro plan) |

`edit` on a recurring day without `--scope` is a `USAGE` error that lists both choices. Ask the person which one they mean, and say the scope back before a series-wide edit. After a split, `result.ref` is the new standalone task's ref; use it for the next write. Deleting a calendar-imported task hides it in Structured. The external calendar event stays.

## Hand off for review in the TUI

After a batch of writes, or when the user wants to adjust the plan themselves, tell them to open the TUI in their terminal. Do not launch it from an agent shell.

```text
structured            # or: structured tui
```

Point them at what changed. For example: "Today now has 13:00-16:30 Billing export with 3 subtasks. Press `enter` on it to tick or edit the checklist." The TUI paints every edit at once, saves in the background, and puts the old value back if a save fails. Layout and keys: [references/tui.md](references/tui.md).

## Recover

| Code | Do this |
| --- | --- |
| `AUTH` | Ask the person to run `structured login` in their own terminal, then retry the read. `login` refuses to run without a terminal. |
| `USAGE` | Fix the flags from `--help`. Do not retry unchanged. |
| `NOT_FOUND` | Follow `next_steps`: refresh refs with `structured today --json` or `structured list --from DAY --json`, or the checklist with `structured subtask list REF --json`. The lookup covers the inbox, upcoming days, and 60 days back. |
| `API` | Read `message`. A plan limit (for example a Pro-only recurring edit) needs the user's decision. |
| `NETWORK` | Retry once. |
