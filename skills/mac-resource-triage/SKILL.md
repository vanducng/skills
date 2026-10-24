---
name: mac-resource-triage
description: "Diagnose and relieve an overloaded macOS workstation: high load average, memory pressure and swap, CPU-hungry helper processes, idle agent sessions and dev containers, file indexers and system scans, plus slow new-terminal / zsh startup. Read-only snapshot first, actions ranked by expected gain, explicit confirmation before stopping anything, then a before/after re-check. Activates when the user says 'it is so busy now', 'check the current resources', 'my mac is slow', 'what is eating CPU', 'load average is high', 'memory pressure', 'swap is full', 'too many agents running', 'terminal takes long to open', or 'shell startup is slow'. Do not use for disk space cleanup (computer-clean) or web page performance (web-perf)."
license: MIT
category: utilities
keywords: [macos, performance, cpu, memory, swap, load, processes, containers, zsh, startup]
metadata:
  author: vanducng
  version: "1.0.0"
---

# Mac Resource Triage

> Snapshot, attribute by app, rank actions by gain, confirm, act, re-snapshot. Never kill on a hunch.

## What this skill is - and isn't

| Situation | Owner |
|---|---|
| Mac slow, fans loud, load / memory / swap high, new terminal slow to open | this skill |
| Disk full, reclaim space | `computer-clean` |
| Slow web page, Core Web Vitals | `web-perf` |
| One app or service erroring or crashing | `debug`, then `fix` |

## Hard rules

1. **Read-only until the user approves a named action list.** Each item names exact targets (PIDs, compose projects, settings keys) and its undo. The user owns these processes; stopping the wrong container or session destroys in-flight work.
2. **Judge by CPU idle, sys %, and memory pressure, not the load number.** macOS load average counts runnable threads only (no disk wait), so fifty queued browser renderers read as "load 400" while each uses little CPU. It is also a 1/5/15-minute moving average that lags every action, so a fix that worked still shows high load for minutes.
3. **High sys % (over ~30%) usually means memory pressure.** The evidence is compressor size, swap used vs total, and sys %. "PhysMem used" near total is normal on macOS, and `memory_pressure`'s free % counts reclaimable cache, so read it next to compressor and swap.
4. **Attribute by app bundle, not by process.** Browsers and Electron apps run 50-100 helpers; a per-process list hides that one app holds 16 GB. Use `scripts/resource-snapshot.sh`.
5. **Close idle agent sessions only on evidence.** Candidate = registry status `idle` AND transcript untouched for a long time (default 24 h). Process age means nothing: a two-day-old session may have been used five minutes ago. Never touch the current session or its ancestors, status `busy`/`shell`/`waiting`, orchestrator-managed seats (`--name x@y`, launched by tmux-send wrappers), or native-messaging hosts. Send SIGTERM, verify exit, then re-check leftover children by PID before killing them, because PIDs are reused within seconds.
6. **Containers: `docker compose -p <project> stop`, never `down`, `rm`, or `prune`.** Stop a stack only when nothing uses it: no non-health API requests for hours, no live session referencing it, last touched long ago. Report the matching `start` command.
7. **Sample before reconfiguring a background service.** Watch what an indexer or launcher actually opens (`lsof -p <pid>` a few times) and fix the real cause, such as a scope of all of `~` crawling `~/.pyenv`, instead of excluding paths its defaults already skip. Back up the setting, quit the app before writing its defaults (a running app can overwrite them), then relaunch.
8. **Trace unknown long-running scripts to their owner first.** Follow the ppid chain; an agent's `du` or `find` sweep is someone's task.
9. **Measurements under load lie.** Use best-of-N, compare against a baseline taken under the same conditions, and confirm on an idle host when one exists (the same config over ssh on another machine).

## Workflow

1. **Snapshot.** `bash scripts/resource-snapshot.sh` (macOS only, read-only). Summarize load vs cores, CPU idle / sys, compressor, swap, process count. Every number comes from this run.
2. **Attribute.** Name the top consumers by CPU and by memory (by app), and who sits in the run queue. Classify each with the playbook.
3. **Drill only where needed.**
   - Agent sessions: `python3 scripts/agent-sessions.py --idle-hours 24` (reads Claude Code's `~/.claude/sessions/<pid>.json` registry and transcripts; both are internal formats - if missing, fall back to `ps` + `lsof -d cwd` and ask the user).
   - Containers: `docker stats --no-stream`, then map projects to directories with the `com.docker.compose.project.working_dir` label; check API logs and which sessions reference the stack.
   - Indexers and scans: `lsof -p <pid>` samples; `ps -o ppid=` chains.
4. **Propose.** A ranked list: target, expected gain (cores, GB), risk, undo. Ask which to run.
5. **Execute approved items only**, verifying each: process gone, container stopped, setting read back.
6. **Re-snapshot** and show a before/after table. If load is still high, say why: lag, or a consumer the user chose to keep.

## Playbook

| Signal in the snapshot | Usual cause | Confirm with | Action after approval | Undo |
|---|---|---|---|---|
| sys > 30%, compressor > 20 GB, swap near total | memory pressure | top-by-memory list | free the biggest RSS: tabs, idle sessions, idle stacks | reopen / start |
| dozens of `Helper (Renderer)` in the run queue, app > 10 GB | browser tabs | snapshot | ask the user to close tabs; do not kill renderers (tabs crash) | - |
| `Google Chrome Helper (GPU)` > 100% | one heavy tab | Chrome Task Manager | close that tab | - |
| OrbStack / Docker helper > 100% | a container, e.g. an Airflow dag-processor re-parsing constantly | `docker stats` | `docker compose -p P stop` | `docker compose -p P start` |
| many `claude` / `node` / `uv` / MCP processes | idle agent sessions, each with its own MCP servers | `agent-sessions.py` | SIGTERM idle candidates; scope heavy MCP servers per project | `claude --resume <id>` |
| `fseventsd` high plus an indexer helper that keeps restarting | indexer scoped too wide, re-crawling on file events | `lsof` samples of the helper | narrow its scope | restore backup |
| many `mdworker_shared` | Spotlight re-indexing after file churn | wait 10-30 min | exclude dev trees in Spotlight Privacy if it persists | remove exclusion |
| `StorageManagementService`, `ApplicationsStorageExtension` | System Settings > Storage open, sizing everything | process age | close System Settings | - |
| `lazydocker`, `btop`, watch loops running for hours | polling dashboards, which also load the container VM | `ps -o etime=` | quit them | relaunch |
| `du` / `find` running for minutes | an agent's scan | ppid chain | let it finish, or stop with the owner's OK | rerun |
| an orchestrator daemon at steady CPU, spawning `ps` | it polls the full process table; cost grows with process count | children sample | reduce process count first | - |

## Slow new terminal or shell

Profile, don't guess: `python3 scripts/zsh-startup-profile.py --env clean` (a fresh terminal), then `--env inherited` (agent and nested shells, which inherit an exported `FPATH`). Causes, the verified cache helper, and the parity checks are in `references/shell-startup.md`. Typical win: 10-20 s down to under 1 s.

## Remote hosts

From an agent shell use `command ssh host '...'`, not `ssh`: a shell-function wrapper that writes to `/dev/tty` fails without a TTY and hides the real output.

## Anti-patterns

- Killing by name (`pkill node`): it takes out MCP servers, dev servers, and other people's sessions.
- Declaring failure because the 1-minute load is still high right after a fix.
- `docker compose down` or `docker system prune` as "resource cleanup": that is data loss, and disk work belongs to `computer-clean`.
- Calling a session idle from its process age.
- Reading xtrace timings as absolute: xtrace inflates time; use it to rank.
