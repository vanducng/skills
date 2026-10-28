---
name: openrig-workspace
description: Work inside an org/project/task workspace across coding harnesses and fleet hosts. Use for task directories, rig selection, feature profiles, bugfix or SOP runs, project discovery, worktree and slice names, seat effort, quota adjustments, or projects workspace sync across macOS and Linux. Also applies when the cwd is under a projects workspace (`$PROJECTS_ROOT`, default `$HOME/projects`), when a seat treats a one-turn classifier refusal as a standing ban, and when the operator messages a rig from outside it (captain-signed messages). Before any rig, pass `--kind feature --profile low|medium|high`, `--kind bugfix`, or `--kind sop`. Owns the workspace layout, unit of work (slice, worktree, PR), task lifecycle, OpenRig adjustments, and fleet sync diagnosis; defers worktree mechanics to the repo's own command or vd:worktree, artifacts to vd:workbench, and pane control to vd:herdr.
license: MIT
metadata:
  author: vanducng
  version: "0.9.0"
---

# OpenRig workspace

One git repo, `$PROJECTS_ROOT` (default `$HOME/projects`), holds org and project context, task records, and machine-local task workdirs. Code stays in its repos. The layout works because every harness reads `AGENTS.md` from the git root down to the cwd, so a task dir inside this repo inherits fleet, org, and project rules automatically. See `references/harness-context.md` for the per-harness discovery rules and sources.

`$HOME/projects` may be a symlink (on mac01 it points at an external disk). Resolve paths from `workspace.yaml`, not from the home dir. The workspace's own `AGENTS.md` and `fleet/policy.yaml` hold the rules; this skill covers the mechanics and does not repeat them.

## Fleet workspace sync

For workspace sync or Git failures across laptop, macOS desktop, and Linux hosts, read [references/fleet-sync.md](references/fleet-sync.md). Discover every host from `fleet/machines.yaml`; distinguish machine IDs, SSH aliases, and OpenRig host IDs. Check each host's credentials, scheduler, workspace log, and live GitHub head separately. A successful SSH read or scheduler exit code does not prove background workspace sync works.

## Layout

```
$PROJECTS_ROOT/
  AGENTS.md  workspace.yaml                     # root rules (operator session, captain, messages, file homes)
  fleet/{machines,routing,policy}.yaml          # hosts; seat models; authority and operator identity
  fleet/bin/                                    # project-host, cc-proxy-seat, rig-say, workspace-sync, ...
  specs/{agents,rigs,skills}/                   # seat roles, rig templates, workspace skills
  .worktrees/<repo>-<slice-id>/                 # gitignored git worktrees, one per repo per slice
  orgs/<org>/
    AGENTS.md  org.yaml  repos.yaml  resources.yaml  contacts.yaml   # repos.yaml is the only place paths live
    kb/                                         # the org's knowledge bundle (OKF), kept by <org>-watch
    tasks/<org>-watch/                          # gitignored task dir of the parked watch rig
    projects/<project>/
      AGENTS.md  SPEC.md  project.yaml  repos.yaml (host:)  resources.yaml
      missions/<mission>/SPEC.md                # frontmatter code:, ticket:, milestone:
      missions/<mission>/slices/<nn>-<slug>/    # committed record: SPEC, PROGRESS, PROOF
      tasks/<task>/                             # gitignored, machine-local, one per rig
        AGENTS.md                               # brief; OpenRig appends seat blocks
        rig.yaml
        <repo> -> ../../../../../../.worktrees/<repo>-<slice-id>   # per-slice rig only
$HOME/.share/openrig/<org>/<project>/<mission>/ # cited captures (screenshots, logs), outside git
```

- **Org** = GitHub owner. **Project** = repos routinely changed in the same ticket. A repo belongs to one org and may appear in several projects.
- A **mission** is an outcome with an owner and a date. A **slice** is one piece of it and the unit of work (see Unit of work). A **task dir** is where a rig runs: one per slice for a per-slice rig, or one long-lived dir for a team rig that works many slices.
- OpenRig catalog IDs are `<org>.<project>`. `$PROJECTS_ROOT` is OpenRig's `workspace.root`.

## Naming

One slice id everywhere, so `rg <slice-id>` finds the record, the worktrees, the branches and the artifacts. Print the names (and the PR title prefix and `## Scope` lines) instead of typing them:

```bash
node "$HOME/skills/skills/openrig-workspace/scripts/slice-names.cjs" <slice dir> --repo <repo> [--repo <repo2>] [--type fix]
```

| Thing | Form | Example |
|---|---|---|
| Slice folder | `missions/<mission>/slices/<nn>-<slug>/` (OpenRig adds `<nn>-`) | `missions/m2-checkout/slices/04-login-fix/` |
| Slice id | `<code>-s<nn>`; `code:` from the mission SPEC frontmatter, else the mission folder's `m<n>-` prefix (`milestone:` falls back to that prefix's number) | `m2-s04` |
| Worktree | `$PROJECTS_ROOT/.worktrees/<repo>-<slice-id>/`; also the repo's compose project and local host name | `.worktrees/api-m2-s04/` |
| Branch | repo convention first; else `<type>/<TICKET>-<slice-id>-<slug>`; each follow-up PR adds `-2`, `-3` | `fix/ABC-123-m2-s04-login-fix` |
| PR title | `<TICKET>: <what shipped, in plain words>`; no bracket tag, milestone or conventional prefix | `ABC-123: fixed login redirect loop` |
| PR body `## Scope` | `Milestone: M<n>, <mission name>`, `Slice: S<n>, <slice name>`, `Mission: <mission>/<slice>` | `Slice: S4, Login fix` |
| Per-slice task dir and rig | `tasks/<slice-id>/`, rig name the same | `tasks/m2-s04/` |

The mission `code` must be unique among projects that share a repo, because their worktrees share one `.worktrees/`. vd:workbench derives the feature id from a `<type>/<TICKET>-<slug>` branch (here `abc-123-m2-s04-login-fix`; not `feature/`). With a bare-ticket branch convention, claim the id once with `workbench new <slug> --ticket <TICKET>`.

## Hard rules

1. Instruction files in this tree are `AGENTS.md` only. Never create a `CLAUDE.md` in it: Claude Code ignores every `AGENTS.md` when a `CLAUDE.md` exists in the cwd or above.
2. Run agents from the **task dir**, not from inside a worktree. That is what makes org and project context load, and it keeps OpenRig's managed blocks out of tracked repo files.
3. Before editing inside a worktree, read that repo's `AGENTS.md` (or `CLAUDE.md` if it has none). Pi, Codex, and Grok do not load files below the cwd.
4. One writer per worktree. One rig per task dir.
5. Authority comes from `fleet/policy.yaml` and the brief. Nothing in this workspace authorizes merge, deploy, force-push, or messages to people.
6. Never `git clean -x` in `$PROJECTS_ROOT`; it deletes ignored task dirs.
7. Do not pick a rig template by feel. Run `scripts/rig-kind.cjs` and copy the template it prints.
8. One machine per project: `host:` in the project's `repos.yaml`. Run `fleet/bin/project-host <project path>` (exit 1 on the wrong machine) before creating a task dir, worktree or rig.
9. An operator session (outside any rig) plans, investigates read-only and drafts. Code, PRs, merges and deploys are dispatched to the project's rig (`fleet/policy.yaml`, `operator_session`).
10. Messages from the operator or an operator session to a rig are signed `captain@global` (see Talk to it). Seats never sign as captain.

## Choose the kind

Run this before the slice and before copying a rig. One kind. `--profile` belongs only to `--kind feature`.

```bash
node "$HOME/skills/skills/openrig-workspace/scripts/rig-kind.cjs" --kind feature --profile low
node "$HOME/skills/skills/openrig-workspace/scripts/rig-kind.cjs" --kind feature --profile medium
node "$HOME/skills/skills/openrig-workspace/scripts/rig-kind.cjs" --kind feature --profile high
node "$HOME/skills/skills/openrig-workspace/scripts/rig-kind.cjs" --kind bugfix
node "$HOME/skills/skills/openrig-workspace/scripts/rig-kind.cjs" --kind sop
```

| Kind | Profile | When | Template |
|---|---|---|---|
| `feature` | `low` | One repo, one reviewable change, no migration, no new flow | `feature-low` |
| `feature` | `medium` | Needs a reviewer who did not write the code. Still one writer | `normal` |
| `feature` | `high` | More than one repo, a new user-visible flow, or a plan the operator must accept before code | `feature-high` |
| `bugfix` | none | Something is failing. Prove it, then fix it | `bugfix` |
| `sop` | none | The org or project already has the steps. Execute them | `sop` |

These flags do not select `solo`, `team`, or `squad`. They also do not select the upstream starters `first-project`, `first-project-claude`, or `first-project-mixed`. Those are two-seat recipes for a repository with no org layout.

`models: default` means every seat takes `default` from `fleet/routing.yaml`; `models: role` takes the seat's key under `seats:` (`owner`, `impl`, `review`, `qa`, `pm`). Each key names a `catalog:` entry (model, effort, window). Routing wins over model strings baked into the template.

Put the choice on the first line of the task `AGENTS.md`: `Kind: feature medium`.

**Feature.** Low is the owner writing alone. Medium adds one writer and a fresh reviewer; the owner does not edit that worktree. High does not start implementation until the operator has accepted the plan. The product seat is for user-visible behavior, briefs, and docs.

**Bug fix.** No code until a check is red or the cause is proven from evidence. Same seats as a medium feature. Create the slice with `--template bug-fix`.

**SOP.** Read the procedure in this order: a path the user named, then the project `AGENTS.md`, then the org `AGENTS.md`. Copy its steps into the slice mini-requirements and do them in that order. One seat. If no procedure exists, stop and ask. Do not promote it to a feature rig.

A hand run with no OpenRig seats still uses the same kind. Low, bugfix, and sop can be one harness in the task dir. Medium and high still get the review or plan gate in the brief even when you do not launch the extra seats.

## Unit of work

- **Slice** is the unit of work: one outcome, one SPEC, one file territory, one owner seat from dispatch to cleanup. A seat is a role, not a unit. Keeping a slice on one seat reuses the context that built it; a relaunched seat re-reads the slice SPEC and PROGRESS.
- **Worktree** belongs to the slice, not to a seat or a PR: one per repo the slice touches, created at dispatch, removed by the cleanup gate. One writer at a time; hand it over with the queue line `worktree_path=<real path>`.
- **PR** is a shipping step of the slice. One by default, carrying code, tests and docs. A follow-up (a finding after merge, a staging defect) is a new branch from the updated base in the same worktree, with the same slice tag. A slice's PRs run one after another; work that needs two writers at once is two slices. Never merge one feature branch into another.
- A slice that spans repos gets one worktree and PR per repo, merged in the order its SPEC names. Past about 800 changed lines in one PR, split the slice.
- Every PR belongs to a slice. A defect found during a slice is fixed in it; one with no slice gets its own small slice, so tags stay true.
- **Waves prevent conflicts.** The lead dispatches the slices that run in parallel with disjoint file territories and keeps the project's hotspot list (files several slices tend to touch, in the project `AGENTS.md`). Only one open slice touches a hotspot; overlap means serialize.
- Merge the base into an open PR only right before it merges, or when it conflicts.
- A switch that differs by environment (a test window, a flag) belongs in per-environment config, not in a PR per flip.
- The slice SPEC names the smallest local setup that proves the change (for example `Local stack: tests only`, `data`, `backend` or `ui`, as the repo's docs define them). Run a stack only while proving something, then stop it.
- Cleanup is part of done: after the merge and the post-merge verification, remove the worktree with the repo's remove command (it must stop the worktree's containers and drop only that worktree's databases, buckets and keys), delete its task-dir link (if any) and the branch, and record one `cleaned` line in the slice PROGRESS.

## Start a task

1. **Resolve.** Run `$PROJECTS_ROOT/fleet/bin/project-host $PROJECTS_ROOT/orgs/<org>/projects/<project>` first: a project runs only on the machine pinned by `host:` in its `repos.yaml`. On any other machine, stop and work there (`ssh <alias>`, or `rig up <rig.yaml> --host <openrig host>`); never create a task dir, worktree or rig here. Then find the project (`workspace.yaml`, `orgs/<org>/projects/<project>/repos.yaml`) and each repo's path for this machine (`orgs/<org>/repos.yaml`, key `paths.<machine>`). A missing path is a question, not a clone. Pick the kind above.
2. **Record.** If the ticket has no slice yet:
   ```bash
   rig scope slice create <mission> <slug> --template <sliceTemplate> --workspace "$PROJECTS_ROOT/orgs/<org>/projects/<project>"
   ```
   Fill `SPEC.md`: intent, mini-requirements, proof contract, repos, territory. Print its names with `slice-names.cjs <slice dir> --repo <repo>`. Check with `rig scope audit --workspace … --mission <mission>`. Read that project's execution view with `rig view show execution --project <org>.<project> --mission <mission> --json`. Omitting `--project` reads only the default workspace.
3. **Workdir.** A per-slice rig: `T="$PROJECTS_ROOT/orgs/<org>/projects/<project>/tasks/<slice-id>"; mkdir -p "$T"`. A team rig already has its task dir.
4. **Worktrees.** One per repo, under `$PROJECTS_ROOT/.worktrees/`, named `<repo>-<slice-id>` from the helper.
   - Refresh the main checkout first when it is clean: `git fetch && git switch <default> && git pull --ff-only`.
   - **The repo has its own worktree command** (its `AGENTS.md` or docs name it, for example a `mise run worktree` task): run that from the main checkout, with its root variable pointed at `$PROJECTS_ROOT/.worktrees` and the name above.
   - **Otherwise** use vd:worktree:
     ```bash
     node "$HOME/skills/skills/worktree/scripts/worktree.cjs" create <branch> --no-prefix --no-enter \
       --worktree-root "$PROJECTS_ROOT/.worktrees" --name <repo>-<slice-id>
     ```
   - A per-slice rig links it into the task dir: `ln -s ../../../../../../.worktrees/<repo>-<slice-id> "$T/<repo>"`, so rig specs and briefs keep using `<repo>`. A team rig's task dir holds no links; the baton names the worktree.
   - `.env`: let the repo's setup build it from `.env.example`. Never copy a checkout's `.env` that holds live provider keys into a worktree.
   - On an external disk with Docker bind mounts, prove the disk once per machine: a container writes a few thousand small files into a bind mount under `.worktrees/` behind a watchdog. If it hangs, restart the container runtime and keep that repo's worktrees on the internal disk until disk access is fixed.
   - Hand a worktree to a seat with the exact queue line `worktree_path=<real path>`. One writer per worktree. vd:workbench artifacts still land in the repo's main checkout.
5. **Brief.** Write `$T/AGENTS.md`. First line is `Kind: <kind> <profile>` (`profile` only for a feature). Then ticket, objective, which `<repo>/` dirs are in scope, branch and base, validation commands, stopping point, and the slice path. Add the line "Before editing in a repo dir, read its AGENTS.md." Cursor does not read parent files, so also point to `../../AGENTS.md` (project) and `../../../../AGENTS.md` (org).
6. **Run.** `cd "$T"` and start any harness. For an OpenRig rig, continue below.

## Run it with OpenRig

1. **Rig spec.** Copy `$PROJECTS_ROOT/specs/rigs/<template>/rig.yaml` to `$T/rig.yaml`, using the template from `rig-kind.cjs`. Set `name: <slice-id>` and every member's `cwd: "."`, and rewrite each `agent_ref` to `local:../../../../../../specs/agents/<role>` (the path relative to the task dir). Keep `managed_blocks: { claude-code: CLAUDE.local.md }` so OpenRig never writes a `CLAUDE.md` (hard rule 1). For more than one repo, add a `workspace:` block (`workspace_root`, `repos[]` of `{name, path, kind: project}`, `default_repo`). A missing template is a stop, not a guess.
2. **Models.** Take them from `fleet/routing.yaml` (every seat runs on Claude Code). Check quota with `cpq` and that the id is live on cli-proxy (`/v1/models`) first. A native Claude id needs nothing more. A cli-proxy id (`grok-4.7`, `glm-5.3`, ...) needs `fleet/bin/cc-proxy-seat <seat cwd> <model>` before launch: it writes that cwd's `.claude/settings.local.json` (proxy URL, key helper, compact window). Seats that share a cwd share that file, so seats on different models need different cwds. A seat that opts into another runtime (Codex, Pi) follows the notes in `fleet/routing.yaml`; a Pi seat also needs a `models.json` in `$OPENRIG_HOME/state/pi/<pod>-<member>@<rig>/agent` whose `apiKey` is `"!<secret read command>"`, never a literal key.
3. **Launch.**
   ```bash
   cd "$T" && rig up rig.yaml --plan && rig up rig.yaml
   ```
   Then check `rig ps --nodes --rig <name>`: every seat `run`, and each `Model (...)` line's "last observed" matches "configured". If a seat shows `att` or `needs-input`, read its pane before retrying.
4. **Look at it in Herdr.** `rig terminal open <name>` opens every running seat in a new workspace named after the rig, up to 16 seats per tab. Herdr is the default provider. A second open does not reuse that workspace; it suffixes another (`<name> (2)`). The TUI link `term ▸ rig <name>` does the same open. To keep one Herdr workspace per org, create a tab there and run `tmux attach -t <seat>` (see vd:herdr). Closing a tile never stops a seat.
5. **Talk to it.** A shell outside a seat has no sender identity: a plain `rig send` arrives as `From: <unknown sender>`, which seats treat as information only. The From line comes from `OPENRIG_SESSION_NAME`, so the operator and operator sessions sign as `captain@global` (workspace `AGENTS.md`, Captain):
   - A message: `fleet/bin/rig-say <seat> "<text>"` (signs, then checks the pane; do not resend what it reports delivered or queued).
   - Work: a queue item to the owner, so it is tracked: `rig queue create --source captain@global --destination <owner seat> --summary "<one line>" --body-file <brief>`.
   - Team rig: address the owner. Steer the writer directly only to unblock or abort it. Broadcast (`OPENRIG_SESSION_NAME=captain@global rig send --rig <rig> "<text>"`) only for a stop or a rule every seat needs now; record a standing rule in an `AGENTS.md` first and name the file in the message.
   - Solo rig: type in the tile or use `rig-say`. Pi runner prefixes are `/followup <text>` and `/abort`; Claude Code seats take plain text.
   - Chat is not recorded. Ask the seat to update `PROGRESS.md` or its queue item.
6. **Finish.** Update the slice, then remove each of its worktrees with the repo's own remove command or vd:worktree once it is merged or abandoned, never with unlanded work. A per-slice rig also runs `rig down <name>` (which strips OpenRig blocks from `$T/AGENTS.md`), deletes each `$T/<repo>` link and deletes `$T`. A team rig keeps running and keeps its task dir; only the slice's worktrees go.

## After a merge

- Refresh that repo's main checkout: fetch, then fast-forward its default branch only if the checkout is clean. Refresh any read-only reference copies the same way.
- Active worktrees pick the change up when they next merge the base (right before their own merge, or on a conflict) and rerun the repo's setup, which should add new `.env.example` keys without overwriting values.
- Stop and remove the merged worktree's stack and worktree.

## OpenRig gotchas

- `rig launch` wants the rig **id** from `rig ps --json`, not the name. `rig up` and `rig down` accept either; if a name matches several rigs, `rig down` refuses and lists the ids.
- To give an existing seat a fresh occupant: `rig seat launch <seat> --fresh --stop --reason "<why>"`. To relaunch it keeping the conversation (for example after a settings change such as a new `ANTHROPIC_BASE_URL`), wait for `idle`, then `rig seat stop <seat> --reason "<why>"` and `rig launch <rig id> <logical id>`; background shells and monitors die, so tell the seat to re-arm them.
- A resume relaunch can report `Harness launch failed: Claude resume failed: timed out waiting for Claude to become active` and leave the seat `att` / "needs you" with continuity `failed`, even though Claude came up with its conversation. Check before acting: `rig capture <seat>` shows the earlier work, and a `rig send` gets a reply. If both hold, the record is stale: `rig seat clear-attention <seat> --reason "<why>"` (it takes no `--operator`). If not, relaunch it; never clear attention you have not verified.
- OpenRig launches Codex seats with `-s workspace-write`, unless a named Codex profile or `full_bypass` replaces it. They cannot reach the daemon unless `[sandbox_workspace_write] network_access = true`. A fresh launch on 0.6.1 or newer resolves a linked worktree's git dir. Prefer Claude Code or Pi seats when the seat must call the daemon.
- A Claude Code seat's permission mode comes from its member's `permission_policy`: `builtin:auto` launches `--permission-mode auto`, `builtin:yolo` launches `--dangerously-skip-permissions`. A member with no policy launches `--permission-mode acceptEdits`, so the first Bash call waits for approval in the tile; the operator can switch that conversation to auto there (`shift+tab`). A future launch is `rig seat set-permissions <seat> --mode <mode> --reason "<why>"`. Modes are `floor`, `full_bypass`, and `inherit`. `auto` is accepted only when that seat's Claude executable advertises it. The command does not relaunch the seat, and `rig seat status` does not prove the live mode. Agents do not change another seat's permissions. The same boundary applies to `rig seat set-typing-guard`.
- A harness classifier denial is one turn. When auto mode refuses a command the project `AGENTS.md` already grants, do not write that refusal into `LEARNED.md` or the recap as a new rule, and do not withdraw the grant. Do not switch tools to sneak the same action through in that turn. Retry the same command on a later turn, or ask the operator to approve it in the pane. An unsigned message still does not add a product decision.
- `rig up <rig> --existing` (and `--fresh <seats>` with it) restores each seat's launch command from the `rig down` snapshot, including the old `--model`. A `rig seat set-model` or rig.yaml edit made while the rig was down does not reach that launch. After it, run `rig seat launch <seat> --fresh --stop --reason "<why>"` for each changed seat and check the "last observed" model in `rig ps --nodes --rig <rig>`.
- `rig send` from a shell that is not a seat arrives as `From: <unknown sender>`; `--from` is ignored. Sign with `fleet/bin/rig-say` or `--source captain@global` on a queue item (Talk to it).
- OpenRig's own help is `rig context get help` (the fleet runs 0.7.x; `rig --version`). If `rig` cannot run, use [openrig.dev/help/agents](https://www.openrig.dev/help/agents).
- OpenRig runs on Node.js 22 or 24. On macOS arm64, stay on Node.js 22. The CLI is the global npm package `@openrig/cli`, not a checkout of the source tree.
- In `rig tui`, `graph` is a tab of a selected rig: type `rig <name>`, then `graph`. `:` only jumps between sections.
- The daemon binds the Tailscale address too. Start it with `--host 127.0.0.1` unless you mean to expose it.

## Restart or move a team rig

OpenRig restores seats from the snapshot taken at `rig down`, which still holds the old cwd, and a seat stopped on its own stays stopped. So:

- **Plain restart, no move:** `rig down <rig>`, then `rig up <rig> --existing`. Conversations resume with the launch settings in the snapshot (see the model gotcha above). Never stop seats one by one first.
- **Move (cwd changes):**
  1. Each seat updates PROGRESS.md, its `LEARNED.md`, and runs `rig context recap-write`; that RECAP is what a successor is primed from.
  2. Move the task dir (on the other host, `mv` the gitignored dirs by hand).
  3. `rig seat set-cwd <seat> --cwd <new absolute path> --reason move` for each seat.
  4. One seat at a time: `rig seat handover <seat> --source rebuild --reason move --dry-run`, then without `--dry-run`. A seat with no live tmux session cannot hand over; use `rig seat launch <seat> --fresh --reason move`.
  5. No `rig down`, `rig up --existing` or fork between steps 3 and 4. A fork source is a session name (`fork:dev-impl@<rig>`), and it will not find a conversation whose cwd moved.
- **Stopped rig whose saved cwd no longer exists:** `cd <task dir> && rig up rig.yaml --plan && rig up rig.yaml`. Same rig name, same topology seat dirs, so earlier RECAP and LEARNED still prime a rebuild.

## Tune seat effort to stretch a shared quota

Seats on one subscription share its 5-hour and weekly limits, and so does every other project on it.

- **Read the budget.** `cpq` (or `cpq --json`) prints used, left, reset and pace for every cli-proxy Claude and Codex account; `$OPENRIG_HOME/state/provider-usage/*.json` holds the native seat's own `rateLimits`. Pace is used percent over the elapsed share of the window; a weekly pace above about 100% means cut, and above about 110% move seats to `grok-4.7` on cli-proxy (`fleet/routing.yaml`).
- **Pick levels.** Planning, routing and the core engine writer keep the template's top effort. Breadth seats (a second writer, docs and briefs, runbook QA) drop one level. A reviewer drops from `xhigh` to `high` when CI and review bots also gate the merge.
- **Save it, no restart.** `rig seat set-effort <seat> --effort <level> --reason "<why>"` applies at the seat's next managed continuation; `rig seat effort <seat>` shows requested, saved, launched and native. Mirror the level in the task `rig.yaml` so a rebuild keeps it.
- **Apply it now, only while idle.** Wait for `idle` in `rig ps --nodes --rig <rig>`, then `rig send <seat> "/effort <level>" --raw` and accept the confirm prompt (option 1). Claude Code drops the prompt cache once and re-reads the full history on the next message. Never switch a seat mid-turn: `rig send` still types into a busy pane, and the confirm prompt then waits there. `/effort` also saves the level as the user-wide default for that model (`modelSettings.<model>.effortLevel` in `~/.claude/settings.json`), and `/model` rewrites the top-level `model` default the same way, so put those values back after each switch; seats are unaffected because OpenRig launches them with `--model` and `--effort`. To change a seat's model between native Claude ids, `rig seat set-model <seat> --model <id> --reason "<why>"` saves it, then `/model <id>` on the idle seat applies it now. Moving to or from a cli-proxy id changes the base URL, so `/model` is not enough: set the model in rig.yaml, run `rig seat set-model` and `fleet/bin/cc-proxy-seat <seat cwd> <id>`, then `rig seat launch <seat> --fresh --stop --reason "<why>"` once the seat has checkpointed in PROGRESS.
- **Trim context too.** Every turn re-reads the context. Ask a seat past about 500k tokens to checkpoint in PROGRESS and run `/compact` itself at a quiet point (after a deploy, never mid-merge) instead of setting a compaction cap that can fire mid-task.

## Add a project

1. Create `orgs/<org>/projects/<project>/` (the folder name is the team rig's name) containing `AGENTS.md` (what it is, a repo table with each repo's role, rules), `SPEC.md` (frontmatter `intent:`), `project.yaml` (`schema: openrig.project/v0alpha1`, `metadata.id: <org>.<project>`), `repos.yaml` (with `host: <machine id>` from `fleet/machines.yaml`, the only machine it runs on), `resources.yaml` (the channels, docs, dashboards, meetings and Jira this project cares about; data only, no secrets), and `missions/`. The org keeps its own `orgs/<org>/resources.yaml`.
2. Add `{id, root}` to `workspace.yaml`.
3. Add any new repo to `orgs/<org>/repos.yaml` with its per-machine paths.

## Workflow position

- **Composes:** vd:worktree (worktree mechanics), vd:workbench (artifacts), vd:herdr (panes and tabs).
- **Upstream OpenRig skills:** `openrig-skills` and `openrig-herdr` cover OpenRig itself. This skill only covers the workspace convention.
