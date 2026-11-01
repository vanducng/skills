---
name: openrig-workspace
description: Work inside the org/project/task projects workspace (`$PROJECTS_ROOT`, default `$HOME/projects`) across harnesses and fleet hosts. Use whenever the cwd is under it or a task touches a project, mission, slice, task dir, worktree, rig or seat there, such as rig kind (`--kind feature --profile low|medium|high`, `--kind bugfix`, `--kind sop`), slice and worktree names, starting or finishing a task, restarting or moving a rig, seat effort and quota, captain-signed messages, a seat treating a one-turn classifier refusal as a ban, Rex server upgrades on rig hosts, and workspace sync across macOS and Linux ('sync fleet', 'fleet sync'). Also owns resources.yaml and contacts.yaml ('update resources.yaml', 'collect resources for <project>', 'add this channel/thread/person', 'refresh contacts', 'who do we talk to about <topic>'). Defers OpenRig itself to `rig context get openrig-skills`, worktree mechanics to the repo's own command or vd:worktree, artifacts to vd:workbench, and pane control to Rex's rex skill.
license: MIT
metadata:
  author: vanducng
  version: "0.13.2"
---

# OpenRig workspace

One git repo, `$PROJECTS_ROOT` (default `$HOME/projects`), holds org and project context, task records, and machine-local task workdirs. Code stays in its repos. The layout works because every harness reads `AGENTS.md` from the git root down to the cwd, so a task dir inside this repo inherits fleet, org, and project rules automatically. See `references/harness-context.md` for the per-harness discovery rules and sources.

`$HOME/projects` may be a symlink (on some hosts it points at an external disk). Resolve paths from `workspace.yaml`, not from the home dir. The workspace's own `AGENTS.md` and `fleet/policy.yaml` hold the rules; this skill covers the mechanics and does not repeat them. Every `AGENTS.md` in the workspace points here, so a seat or operator session that touches a project, slice, task dir, rig, seat or resources file loads this skill first.

## Fleet workspace sync

When the operator says "sync fleet", run the recipe at the top of [references/fleet-sync.md](references/fleet-sync.md): check, full run, check again, report. For workspace sync or Git failures across laptop, macOS desktop, and Linux hosts, read the rest of that file. Discover every host from `fleet/machines.yaml`; distinguish machine IDs, SSH aliases, and OpenRig host IDs. Check each host's credentials, scheduler, workspace log, and live GitHub head separately. A successful SSH read or scheduler exit code does not prove background workspace sync works.

## Layout

```
$PROJECTS_ROOT/
  AGENTS.md  workspace.yaml                     # root rules (operator session, captain, messages, file homes)
  fleet/{machines,routing,policy}.yaml          # hosts; seat models; authority and operator identity
  fleet/bin/                                    # project-host, rig-to-pi, pi-rig-check, rig-say, workspace-sync, ...
  specs/{agents,rigs,skills}/                   # seat roles, rig templates, workspace skills
  .worktrees/<repo>-<slice-id>/                 # gitignored git worktrees, one per repo per slice
  orgs/<org>/
    AGENTS.md  org.yaml  repos.yaml  resources.yaml  contacts.yaml   # repos.yaml is the only place paths live
    kb/                                         # the org's knowledge bundle (OKF, PARA buckets per vd:para), kept by <org>-watch
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

Every template is a pi-tui rig. A seat's model comes from its role (`PI_TUI_ROLE`) in one profile under `pi.profiles` in `fleet/routing.yaml`; `pi.default_profile` applies unless the operator or the project names another. Routing wins over model strings baked into the template.

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

1. **Rig spec.** Copy `$PROJECTS_ROOT/specs/rigs/<template>/rig.yaml` to `$T/rig.yaml`, using the template from `rig-kind.cjs`. Set `name: <slice-id>` and every member's `cwd: "."`, and rewrite each `agent_ref` to `local:../../../../../../specs/agents/pi-seat` (the path relative to the task dir), keeping each member's `env.PI_TUI_ROLE`: the pi-tui launcher reads that role's skills and startup files from `specs/agents/<role>`. Keep `managed_blocks: { claude-code: CLAUDE.local.md }` so OpenRig never writes a `CLAUDE.md` (hard rule 1). For more than one repo, add a `workspace:` block (`workspace_root`, `repos[]` of `{name, path, kind: project}`, `default_repo`). A missing template is a stop, not a guess. Keep the human seat that every template with more than two seats carries: a `runtime: terminal` member `human`, listed first in the first pod so it is the first tile in every view, whose startup action types `pi`, so the operator has a Pi shell inside the rig to talk to the team. When you build a spec with more than two seats by hand, add it the same way.
2. **Models.** Run `fleet/bin/rig-to-pi convert "$T/rig.yaml" [profile]`: it sets every agent seat's model from the profile and the seat's role. Check quota with `cpq` and that each id is live on the gateway (`/v1/models`) and in the operator's Pi `models.json` first. Each seat's Pi folder (`$OPENRIG_HOME/state/pi-tui/<seat>/agent`) is provisioned by the launcher at every launch from the operator's own Pi setup: models, footer with the seat name, title, board hook, workspace trust, role skills and startup files. Nothing is written by hand. A running rig still on Claude Code or Codex moves with `rig-to-pi recap <rig>`, then `rig-to-pi switch <rig.yaml> [profile]`, which keeps addresses, queue rows and claims and briefs each successor with its recap and previous conversation.
3. **Launch.**
   ```bash
   cd "$T" && rig up rig.yaml --plan && rig up rig.yaml
   ```
   Then check `rig ps --nodes --rig <name>` (every seat `run`) and `fleet/bin/pi-rig-check <name>`: each seat's footer shows its seat name and the intended model, with no gateway or launcher error. OpenRig reads no activity or model for a pi-tui seat, so its `unknown` there is expected. If a seat is at a shell, read the launcher's message in its pane before retrying.
4. **Look at it.** Views are Rex only: `rig terminal open <name> --provider rex` opens every running seat as tiles in a Rex session. Always name the provider: with none, OpenRig picks Rex only when the command runs inside a Rex block and otherwise falls back to Herdr. Run `rig tui` inside Rex for the same reason, since its `term ▸` link uses the same rule. Keep one view per rig: a second viewer on the same seats stops the tmux hook from fitting each window to its tile. Closing a tile never stops a seat.
5. **Talk to it.** A shell outside a seat has no sender identity: a plain `rig send` arrives as `From: <unknown sender>`, which seats treat as information only. The From line comes from `OPENRIG_SESSION_NAME`, so the operator and operator sessions sign as `captain@global` (workspace `AGENTS.md`, Captain):
   - A message: `fleet/bin/rig-say <seat> "<text>"` (signs, then checks the pane; do not resend what it reports delivered or queued).
   - Work: a queue item to the owner, so it is tracked: `rig queue create --source captain@global --destination <owner seat> --summary "<one line>" --body-file <brief>`. From a human seat, the seat's own `OPENRIG_SESSION_NAME` wins over `--source`, so prefix the command with `OPENRIG_SESSION_NAME=captain@global`. For a rig on another host add `--host <openrig_id>`, and read the row back with `OPENRIG_URL=<openrig_url> rig queue list` (ids and urls from `fleet/machines.yaml`).
   - Team rig: address the owner. Steer the writer directly only to unblock or abort it. Broadcast (`OPENRIG_SESSION_NAME=captain@global rig send --rig <rig> "<text>"`) only for a stop or a rule every seat needs now; record a standing rule in an `AGENTS.md` first and name the file in the message.
   - Human seat (`<first pod>-human@<rig>`): the operator's Pi shell in the rig. Pi there is an operator session: it signs as captain with `rig-say` and the queue, and sends work to the owner instead of doing it. Seats never route work to it or type into it, and a broadcast lands there too.
   - Solo rig: type in the tile or use `rig-say`. A pi-tui seat takes plain text; Pi's own slash commands (`/reload`, `/compact`) work in its tile. Never type into a seat whose editor holds someone's draft.
   - Chat is not recorded. Ask the seat to update `PROGRESS.md` or its queue item.
6. **Finish.** Update the slice, then remove each of its worktrees with the repo's own remove command or vd:worktree once it is merged or abandoned, never with unlanded work. A per-slice rig also runs `rig down <name>` (which strips OpenRig blocks from `$T/AGENTS.md`), deletes each `$T/<repo>` link and deletes `$T`. A team rig keeps running and keeps its task dir; only the slice's worktrees go.

## After a merge

- Refresh that repo's main checkout: fetch, then fast-forward its default branch only if the checkout is clean. Refresh any read-only reference copies the same way.
- Active worktrees pick the change up when they next merge the base (right before their own merge, or on a conflict) and rerun the repo's setup, which should add new `.env.example` keys without overwriting values.
- Stop and remove the merged worktree's stack and worktree.

## OpenRig operations

OpenRig's own procedures come from the installed CLI, so they always match the running version: `rig context get openrig-skills` is the index, and `rig context get <name>` loads one by its bare name (`rig-lifecycle`, `seat-continuity-and-handover`, `openrig-upgrade`, `watchdog`, `mission-slice-sop`), and `rig context get help` is the troubleshooting guide. This skill adds only what is specific to this workspace:

| When | Read |
|---|---|
| A seat misbehaves, a relaunch or resume looks wrong, permissions, `rig send` identity | [references/openrig-ops.md](references/openrig-ops.md), Gotchas |
| Restarting a team rig, moving a task dir or project to another cwd or host | [references/openrig-ops.md](references/openrig-ops.md), Restart or move a team rig |
| Changing a seat's effort or model, quota running hot | [references/openrig-ops.md](references/openrig-ops.md), Tune seat effort |
| Upgrading or restarting the Rex server on a host with rigs | [references/rex-upgrade.md](references/rex-upgrade.md) |
| Running, moving, viewing or growing the operator's conductor rig; adding or archiving a desk | [references/conductor.md](references/conductor.md) |

## Project resources and contacts

`resources.yaml` (org and project) and the org `contacts.yaml` are how seats find people, conversations, environments and provider objects. Collect and change them only through [references/project-resources.md](references/project-resources.md): read-only collection, a diff with evidence, a write only on the user's yes, then `scripts/check-resources.sh <project dir>`. Schema: [references/resources-schema.md](references/resources-schema.md).

## Org knowledge and watch rigs

Each org keeps a knowledge tree that a parked watch rig fills. To set one up, run it or audit it, follow [references/org-watch-rig.md](references/org-watch-rig.md). Where the tree's rules live, and the commands a seat uses, are in [references/org-knowledge.md](references/org-knowledge.md).

## Add a project

1. Create `orgs/<org>/projects/<project>/` (the folder name is the team rig's name) containing `AGENTS.md` (what it is, a repo table with each repo's role, rules), `SPEC.md` (frontmatter `intent:`), `project.yaml` (`schema: openrig.project/v0alpha1`, `metadata.id: <org>.<project>`), `repos.yaml` (with `host: <machine id>` from `fleet/machines.yaml`, the only machine it runs on), `resources.yaml` (the channels, docs, dashboards, meetings and Jira this project cares about; data only, no secrets), and `missions/`. The org keeps its own `orgs/<org>/resources.yaml`.
2. Add `{id, root}` to `workspace.yaml`.
3. Add any new repo to `orgs/<org>/repos.yaml` with its per-machine paths.

## Workflow position

- **Composes:** vd:worktree (worktree mechanics), vd:workbench (artifacts), Rex's own `rex` skill (Rex panes).
- **Upstream OpenRig skills:** `rigs` (install, start, attach from your own session), `openrig-skills` and `rig context get` (OpenRig itself, inside a rig), `refocusing` (a long-running seat that lost the outcome). This skill covers only the workspace convention and the fleet's observed gotchas.
