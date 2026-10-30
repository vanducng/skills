# OpenRig operations in this workspace

Fleet-specific OpenRig knowledge, observed on the workspace's rigs. Generic OpenRig procedures (rig lifecycle, seat handover, upgrades, watchdog) come from the installed CLI: `rig context get openrig-skills` lists them, and `rig context get <name>` loads one by bare name (`rig context list` for refs). This file only adds what those do not say about this workspace.

## Gotchas

- `rig launch` wants the rig **id** from `rig ps --json`, not the name. `rig up` and `rig down` accept either; if a name matches several rigs, `rig down` refuses and lists the ids.
- To give an existing seat a fresh occupant: `rig seat launch <seat> --fresh --stop --reason "<why>"`. To relaunch it keeping the conversation (for example after a settings change such as a new `ANTHROPIC_BASE_URL`), wait for `idle`, then `rig seat stop <seat> --reason "<why>"` and `rig launch <rig id> <logical id>`; background shells and monitors die, so tell the seat to re-arm them.
- A resume relaunch can report `Harness launch failed: Claude resume failed: timed out waiting for Claude to become active` and leave the seat `att` / "needs you" with continuity `failed`, even though Claude came up with its conversation. Check before acting: `rig capture <seat>` shows the earlier work, and a `rig send` gets a reply. If both hold, the record is stale: `rig seat clear-attention <seat> --reason "<why>"` (it takes no `--operator`). If not, relaunch it; never clear attention you have not verified.
- OpenRig launches Codex seats with `-s workspace-write`, unless a named Codex profile or `full_bypass` replaces it. They cannot reach the daemon unless `[sandbox_workspace_write] network_access = true`. A fresh launch on 0.6.1 or newer resolves a linked worktree's git dir. Prefer Claude Code or Pi seats when the seat must call the daemon.
- A Claude Code seat's permission mode comes from its member's `permission_policy`: `builtin:auto` launches `--permission-mode auto`, `builtin:yolo` launches `--dangerously-skip-permissions`. A member with no policy launches `--permission-mode acceptEdits`, so the first Bash call waits for approval in the tile; the operator can switch that conversation to auto there (`shift+tab`). A future launch is `rig seat set-permissions <seat> --mode <mode> --reason "<why>"`. Modes are `floor`, `full_bypass`, and `inherit`. `auto` is accepted only when that seat's Claude executable advertises it. The command does not relaunch the seat, and `rig seat status` does not prove the live mode. Agents do not change another seat's permissions. The same boundary applies to `rig seat set-typing-guard`.
- A harness classifier denial is one turn. When auto mode refuses a command the project `AGENTS.md` already grants, do not write that refusal into `LEARNED.md` or the recap as a new rule, and do not withdraw the grant. Do not switch tools to sneak the same action through in that turn. Retry the same command on a later turn, or ask the operator to approve it in the pane. An unsigned message still does not add a product decision.
- `rig up <rig> --existing` (and `--fresh <seats>` with it) restores each seat's launch command from the `rig down` snapshot, including the old `--model`. A `rig seat set-model` or rig.yaml edit made while the rig was down does not reach that launch. After it, run `rig seat launch <seat> --fresh --stop --reason "<why>"` for each changed seat and check the "last observed" model in `rig ps --nodes --rig <rig>`.
- `rig send` from a shell that is not a seat arrives as `From: <unknown sender>`; `--from` is ignored. Sign with `fleet/bin/rig-say` or `--source captain@global` on a queue item (SKILL.md, Run it with OpenRig, Talk to it).
- OpenRig's own help is `rig context get help` (the fleet runs 0.7.x; `rig --version`). If `rig` cannot run, use [openrig.dev/help/agents](https://www.openrig.dev/help/agents).
- OpenRig runs on Node.js 22 or 24. On macOS arm64, stay on Node.js 22. The CLI is the global npm package `@openrig/cli`, not a checkout of the source tree.
- In `rig tui`, `graph` is a tab of a selected rig: type `rig <name>`, then `graph`. `:` only jumps between sections.
- The daemon binds the Tailscale address too. Start it with `--host 127.0.0.1` unless you mean to expose it.

## Restart or move a team rig

OpenRig restores seats from the snapshot taken at `rig down`, which still holds the old cwd, and a seat stopped on its own stays stopped. So:

- **Plain restart, no move:** `rig down <rig>`, then `rig up <rig> --existing`. Conversations resume with the launch settings in the snapshot (see the `--existing` model gotcha above). Never stop seats one by one first.
- **Move (cwd changes):**
  1. Each seat updates PROGRESS.md, its `LEARNED.md`, and runs `rig context recap-write`; that RECAP is what a successor is primed from.
  2. Move the task dir (on the other host, `mv` the gitignored dirs by hand).
  3. `rig seat set-cwd <seat> --cwd <new absolute path> --reason move` for each seat.
  4. One seat at a time: `rig seat handover <seat> --source rebuild --reason move --dry-run`, then without `--dry-run`. A seat with no live tmux session cannot hand over; use `rig seat launch <seat> --fresh --reason move`.
  5. No `rig down`, `rig up --existing` or fork between steps 3 and 4. A fork source is a session name (`fork:dev-impl@<rig>`), and it will not find a conversation whose cwd moved.
- **Rex server upgrade or restart on a host with rigs:** read `references/rex-upgrade.md` first. Seats in tmux usually survive, Rex views of them do not, and on Linux a tmux started from a Rex pane dies with the Rex unit.
- **Stopped rig whose saved cwd no longer exists:** `cd <task dir> && rig up rig.yaml --plan && rig up rig.yaml`. Same rig name, same topology seat dirs, so earlier RECAP and LEARNED still prime a rebuild.

## Tune seat effort to stretch a shared quota

Seats on one subscription share its 5-hour and weekly limits, and so does every other project on it.

- **Read the budget.** `cpq` (or `cpq --json`) prints used, left, reset and pace for every cli-proxy Claude and Codex account; `$OPENRIG_HOME/state/provider-usage/*.json` holds the native seat's own `rateLimits`. Pace is used percent over the elapsed share of the window; a weekly pace above about 100% means cut, and above about 110% move seats to `grok-4.7` on cli-proxy (`fleet/routing.yaml`).
- **Pick levels.** Planning, routing and the core engine writer keep the template's top effort. Breadth seats (a second writer, docs and briefs, runbook QA) drop one level. A reviewer drops from `xhigh` to `high` when CI and review bots also gate the merge.
- **Save it, no restart.** `rig seat set-effort <seat> --effort <level> --reason "<why>"` applies at the seat's next managed continuation; `rig seat effort <seat>` shows requested, saved, launched and native. Mirror the level in the task `rig.yaml` so a rebuild keeps it.
- **Apply it now, only while idle.** Wait for `idle` in `rig ps --nodes --rig <rig>`, then `rig send <seat> "/effort <level>" --raw` and accept the confirm prompt (option 1). Claude Code drops the prompt cache once and re-reads the full history on the next message. Never switch a seat mid-turn: `rig send` still types into a busy pane, and the confirm prompt then waits there. `/effort` also saves the level as the user-wide default for that model (`modelSettings.<model>.effortLevel` in `~/.claude/settings.json`), and `/model` rewrites the top-level `model` default the same way, so put those values back after each switch; seats are unaffected because OpenRig launches them with `--model` and `--effort`. To change a seat's model between native Claude ids, `rig seat set-model <seat> --model <id> --reason "<why>"` saves it, then `/model <id>` on the idle seat applies it now. Moving to or from a cli-proxy id changes the base URL, so `/model` is not enough: set the model in rig.yaml, run `rig seat set-model` and `fleet/bin/cc-proxy-seat <seat cwd> <id>`, then `rig seat launch <seat> --fresh --stop --reason "<why>"` once the seat has checkpointed in PROGRESS.
- **Trim context too.** Every turn re-reads the context. Ask a seat past about 500k tokens to checkpoint in PROGRESS and run `/compact` itself at a quiet point (after a deploy, never mid-merge) instead of setting a compaction cap that can fire mid-task.
