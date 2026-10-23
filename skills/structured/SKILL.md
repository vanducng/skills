---
name: structured
description: "Operate the Structured day planner through the structured CLI. Use when listing, completing, creating, editing, or deleting Structured tasks, opening the Structured TUI, or recovering from structured CLI errors. Reads are safe. Writes need explicit user authorization."
license: MIT
argument-hint: "<Structured task read or authorized change>"
metadata:
  author: vanducng
  version: "0.1.0"
---

# structured

Use the `structured` binary. `--help` on the command you are about to run is the flag contract. Do not call the Structured MCP server directly.

## Start

```bash
command -v structured
structured --version
structured today --help
```

Install the latest GitHub release archive for this machine, or:

```bash
cargo install --git https://github.com/vanducng/structured
```

Confirm with `structured --version`.

## Sign in

Start with a read:

```bash
structured today --json
```

If stderr has `"code":"AUTH"`, ask the user to run `structured login` in an interactive terminal. Login opens a browser and stores tokens at `$XDG_CONFIG_HOME/structured/auth.json`, or `~/.config/structured/auth.json`. Do not run login from a non-interactive shell. Do not read, print, or commit that file.

## Output

- Success is one JSON object on stdout when `--json` is set or stdout is not a terminal.
- Failure is one JSON object on stderr: `error.code`, `error.message`, `error.retryable`, `error.next_steps`.
- Retry only when `retryable` is true. Follow `next_steps` in order.
- `--help` and `--version` are human text, not JSON.
- Usage mistakes exit 2. Other failures exit 1.

## Read

```bash
structured today --json
structured inbox --json
structured list --from 2026-10-01 --to 2026-10-07 --json
structured account --json
```

Keep task titles out of logs unless the user asked to see them. Report counts and ids.

A recurring row may have an empty `id` and a `recurring_id`. Later commands for that row need the recurring id and `--day YYYY-MM-DD`.

## Write

Create, edit, complete, reopen, or delete only after the user explicitly authorizes that operation. A read is not authorization.

```bash
structured add "Write the note" --day 2026-10-24 --time 09:30 --duration 30 --json
structured add "Someday" --inbox --json
structured done TASK_ID --json
structured undo TASK_ID --json
structured edit TASK_ID --title "New title" --json
structured delete TASK_ID --yes --json
```

- No day, or `--inbox`, creates an inbox task.
- A day without `--time` is all-day. `--time` is `HH:MM`. Duration is minutes.
- `delete` refuses to run without `--yes`.
- For a recurring id, pass `--day`. `delete` then removes that day only.
- Deleting a calendar-imported task hides it in Structured. It does not delete the event from the external calendar.
- The default symbol is `text.badge.checkmark`. Override with `--symbol` when the user names one.
- This CLI does not create recurring series.

## TUI

A person runs `structured` in a terminal to open the task manager. `structured tui` does the same. Do not launch the TUI from an agent shell. Keys: `j`/`k`, `gg`/`G`, `h`/`l`, `[`/`]`, `x` or space to tick, `a` add, `e` edit title, `d` then `y` delete, `r` refresh, `q` quit.
