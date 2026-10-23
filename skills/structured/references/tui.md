# The TUI, for the person reviewing

`structured` with no command opens it in a terminal. Agents describe it. They do not run it.

```text
 Friday 23 October 2026  Today        Mon 19 … [Fri 23] Sat 24 Sun 25  │  Inbox 5
╭ Today · 11 tasks ──── 3 done · 9h planned ╮╭ Details ──────────────────────────╮
│       ALL DAY                             ││ ██ Finish the billing export ████ │
│       ▍ ○ Read 20 pages                ↻  ││                                   │
│ 08:30 ▍ ○ Team sync                  45m  ││ Date      Fri 23 Oct 2026 · today │
│ 09:00 ▍ ○ Review the pull…  overlap  30m  ││ Time      13:00-16:30 · 3h 30m    │
│       ┆  3h 30m free                      ││                                   │
│ 13:00 ▍ ○ Finish the billi…  1/3  3h 30m  ││ SUBTASKS  1/3                     │
│ 23:44 ────────────────────────────── now  ││   ☑ Map the fields                │
╰───────────────────────────────────────────╯╰───────────────────────────────────╯
 SUBTASKS ✓ subtasks saved              x tick  a add  e rename  d delete  ? help
   │            │                                  │
   mode chip    save status (fades after 4s)       keys for what has focus
```

- Header: the viewed date, a week strip with the viewed day highlighted, and the inbox count.
- Left pane: the day as a timeline. The colored bar is the task's color. `○` open, `✓` done, `↻` recurring, `1/3` subtasks done, `overlap` in yellow, `┆ free` gaps, a red now-line on today. The inbox lists open tasks, then `Done · N`.
- Right pane: the selected task with a colored title band, date, time, repeat, energy, the subtask checklist, the note, and its `ref`.
- Footer: a mode chip (`FIND`, `SUBTASKS`, a prompt name, `DELETE`, `HELP`), the save status, and the keys that work right now. `?` shows them all.

## Keys

| Keys | Action |
| --- | --- |
| `j` `k` `↑` `↓`, `gg` `G`, `ctrl-d` `ctrl-u` | move |
| `t`, `i`, `tab`, `[` `]` `←` `→` | today, inbox, flip, day before or after |
| `/` or `f` | find in titles, notes, and subtasks. `n` `N` next and previous. `esc` clears |
| `x` or space | done or not |
| `a`, `e`, `d` then `y` | add, edit title, delete |
| `D`, `T`, `m`, `,` `.` | date, time, minutes, move one day |
| `enter` or `l` | open the subtasks: `j` `k`, `x` tick, `a` add (typed in place, `⏎` keeps adding), `e` rename, `d` delete, `J` `K` reorder, `h` or `esc` back |
| `A` | add a subtask from the list |
| `ctrl-g` | edit the note in `$VISUAL` or `$EDITOR` |
| `r`, `?`, `q` or `ctrl-c` | refresh, help, quit |

Prompts edit on one line at the bottom: `←` `→`, `home` `end`, `ctrl-w`, `ctrl-u`. `↑` `↓` step a date by a day and a time or duration by 15 minutes. A rejected value keeps the draft. `esc` cancels. On a recurring task the prompt chip says `every repeat` (title, time, minutes) or `this day only` (date, subtasks). `q` waits for pending saves before it quits. A search that matched through a subtask or note marks the row `↳ subtask` or `↳ note`.

## A review pass

1. `t` for today. Scan for `overlap` and the gaps.
2. `j` to a task, `enter` to open its checklist, `x` to tick, `a` to add a missing step.
3. `T` to move a time, `m` to change minutes, `.` to push a task to tomorrow.
4. `i` for the inbox. `D` then `today` schedules an inbox task for today.
