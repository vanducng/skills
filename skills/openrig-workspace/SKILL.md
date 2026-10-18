---
name: openrig-workspace
description: Work inside an org/project/task workspace that any coding harness (Pi, Claude Code, Codex, Grok Build, Cursor) reads out of the box and that OpenRig can drive without a fork. Use when the user says "start a task in <project>", "set up the task dir", "which rig", "feature profile", "bugfix", "sop", "run this ticket with openrig", "attach the rig in herdr", "which project does this repo belong to", "add a project", "name the worktree or branch", "slice names", or when the cwd is under a projects workspace (`$PROJECTS_ROOT`, default `$HOME/projects`). Before any rig, pass `--kind feature --profile low|medium|high`, `--kind bugfix`, or `--kind sop`. Owns the layout (including where worktrees live), the unit of work (slice, worktree, PR) and its names, task lifecycle, that choice, and OpenRig adjustments; defers worktree mechanics to the repo's own worktree command or vd:worktree, artifacts to vd:workbench, pane control to vd:herdr.
license: MIT
metadata:
  author: vanducng
  version: "0.5.0"
---

# OpenRig workspace

One git repo, `$PROJECTS_ROOT` (default `$HOME/projects`), holds org and project context, task records, and machine-local task workdirs. Code stays in its repos. The layout works because every harness reads `AGENTS.md` from the git root down to the cwd, so a task dir inside this repo inherits fleet, org, and project rules automatically. See `references/harness-context.md` for the per-harness discovery rules and sources.

## Layout

```
$PROJECTS_ROOT/
  AGENTS.md  workspace.yaml  fleet/{machines,routing,policy}.yaml  specs/{agents,rigs}/
  .worktrees/<repo>-<slice-id>/                 # gitignored git worktrees, one per repo per slice
  orgs/<org>/
    AGENTS.md  org.yaml  repos.yaml            # repos.yaml is the only place paths live
    <project>/
      AGENTS.md  SPEC.md  project.yaml  repos.yaml
      missions/<mission>/SPEC.md                # frontmatter code:, ticket:, milestone:
      missions/<mission>/slices/<nn>-<slug>/    # committed record: SPEC, PROGRESS, PROOF
      tasks/<task>/                             # gitignored, machine-local, one per rig
        AGENTS.md                               # brief; OpenRig appends seat blocks
        rig.yaml
        <repo> -> ../../../../../.worktrees/<repo>-<slice-id>   # per-slice rig only
```

- **Org** = GitHub owner. **Project** = repos routinely changed in the same ticket. A repo belongs to one org and may appear in several projects.
- A **mission** is an outcome with an owner and a date. A **slice** is one piece of it and the unit of work (see Unit of work). A **task dir** is where a rig runs: one per slice for a per-slice rig, or one long-lived dir for a team rig that works many slices.
- OpenRig catalog IDs are `<org>.<project>`. `$PROJECTS_ROOT` is OpenRig's `workspace.root`.

## Naming

One slice id everywhere, so `rg <slice-id>` finds the record, the worktrees, the branches and the artifacts. Print the names instead of typing them:

```bash
node "$HOME/skills/skills/openrig-workspace/scripts/slice-names.cjs" <slice dir> --repo <repo> [--repo <repo2>] [--type fix]
```

| Thing | Form | Example |
|---|---|---|
| Slice folder | `missions/<mission>/slices/<nn>-<slug>/` (OpenRig adds `<nn>-`) | `missions/m2-checkout/slices/04-login-fix/` |
| Slice id | `<code>-s<nn>`; `code:` from the mission SPEC frontmatter, else the mission folder's `m<n>-` prefix (`milestone:` falls back to that prefix's number) | `m2-s04` |
| Worktree | `$PROJECTS_ROOT/.worktrees/<repo>-<slice-id>/`; also the repo's compose project and local host name | `.worktrees/api-m2-s04/` |
| Branch | repo convention first; else `<type>/<TICKET>-<slice-id>-<slug>`; each follow-up PR adds `-2`, `-3` | `fix/ABC-123-m2-s04-login-fix` |
| PR tag | `[<TICKET>\|M<milestone>\|S<n>]` from the mission frontmatter `ticket:` and `milestone:`, where the workspace tags PRs | `[ABC-123\|M2\|S4]` |
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

`models: default` means every seat uses the routing default for its runtime. Claude Code uses the bare id under `default`. A seat with `runtime: pi` uses `routing.pi.default`, as `provider/id:thinking`. `models: role` uses the named key (`owner`, `implement`, `design`, `review`) in that same map. Routing wins over model strings baked into the template.

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

1. **Resolve.** Find the project (`workspace.yaml`, `orgs/<org>/<project>/repos.yaml`) and each repo's path for this machine (`orgs/<org>/repos.yaml`, key `paths.<machine>`). A missing path is a question, not a clone. Pick the kind above.
2. **Record.** If the ticket has no slice yet:
   ```bash
   rig scope slice create <mission> <slug> --template <sliceTemplate> --workspace "$PROJECTS_ROOT/orgs/<org>/<project>"
   ```
   Fill `SPEC.md`: intent, mini-requirements, proof contract, repos, territory. Print its names with `slice-names.cjs <slice dir> --repo <repo>`. Check with `rig scope audit --workspace … --mission <mission>`. On OpenRig 0.6.1 or newer, read that project's execution view with `rig view show execution --project <org>.<project> --mission <mission> --json`. Omitting `--project` reads only the default workspace.
3. **Workdir.** A per-slice rig: `T="$PROJECTS_ROOT/orgs/<org>/<project>/tasks/<slice-id>"; mkdir -p "$T"`. A team rig already has its task dir.
4. **Worktrees.** One per repo, under `$PROJECTS_ROOT/.worktrees/`, named `<repo>-<slice-id>` from the helper.
   - Refresh the main checkout first when it is clean: `git fetch && git switch <default> && git pull --ff-only`.
   - **The repo has its own worktree command** (its `AGENTS.md` or docs name it, for example a `mise run worktree` task): run that from the main checkout, with its root variable pointed at `$PROJECTS_ROOT/.worktrees` and the name above.
   - **Otherwise** use vd:worktree:
     ```bash
     node "$HOME/skills/skills/worktree/scripts/worktree.cjs" create <branch> --no-prefix --no-enter \
       --worktree-root "$PROJECTS_ROOT/.worktrees" --name <repo>-<slice-id>
     ```
   - A per-slice rig links it into the task dir: `ln -s ../../../../../.worktrees/<repo>-<slice-id> "$T/<repo>"`, so rig specs and briefs keep using `<repo>`. A team rig's task dir holds no links; the baton names the worktree.
   - `.env`: let the repo's setup build it from `.env.example`. Never copy a checkout's `.env` that holds live provider keys into a worktree.
   - On an external disk with Docker bind mounts, prove the disk once per machine: a container writes a few thousand small files into a bind mount under `.worktrees/` behind a watchdog. If it hangs, restart the container runtime and keep that repo's worktrees on the internal disk until disk access is fixed.
   - Hand a worktree to a seat with the exact queue line `worktree_path=<real path>`. One writer per worktree. vd:workbench artifacts still land in the repo's main checkout.
5. **Brief.** Write `$T/AGENTS.md`. First line is `Kind: <kind> <profile>` (`profile` only for a feature). Then ticket, objective, which `<repo>/` dirs are in scope, branch and base, validation commands, stopping point, and the slice path. Add the line "Before editing in a repo dir, read its AGENTS.md." Cursor does not read parent files, so also point to `../../AGENTS.md` and `../../../AGENTS.md`.
6. **Run.** `cd "$T"` and start any harness. For an OpenRig rig, continue below.

## Run it with OpenRig

1. **Rig spec.** Copy `$PROJECTS_ROOT/specs/rigs/<template>/rig.yaml` to `$T/rig.yaml`, using the template from `rig-kind.cjs`. Set `name: <slice-id>` and every member's `cwd: "."`, and rewrite each `agent_ref` to `local:../../../../../specs/agents/<role>` (the path relative to the task dir). Keep `managed_blocks: { claude-code: CLAUDE.local.md }` so OpenRig never writes a `CLAUDE.md` (hard rule 1). For more than one repo, add a `workspace:` block (`workspace_root`, `repos[]` of `{name, path, kind: project}`, `default_repo`). A missing template is a stop, not a guess.
2. **Models.** Take them from `fleet/routing.yaml`. The default seat is Claude Code with a bare model id (`claude-opus-5-5`). A seat that opts into `runtime: pi` uses `routing.pi`, as `provider/id:thinking`. When the script says `models: role`, use the named key in that same map.
3. **Pi seat auth (Pi seats only).** A Pi seat gets a blank agent dir at `$OPENRIG_HOME/state/pi/<pod>-<member>@<rig>/agent`, and custom-provider env vars are not forwarded. Before `rig up`, put a `models.json` there (or a symlink to one shared file). It carries the provider's non-secret fields plus an `apiKey` of the form `"!<secret read command>"`. Never write a literal key.
4. **Launch.**
   ```bash
   cd "$T" && rig up rig.yaml --plan && rig up rig.yaml
   ```
   Then check `rig ps --nodes --rig <name>`. If a seat shows `att` or `needs-input`, read its pane before retrying.
5. **Look at it in Herdr.** `rig terminal open <name>` opens every running seat in a new workspace named after the rig, up to 16 seats per tab. Herdr is the default provider. A second open does not reuse that workspace; it suffixes another (`<name> (2)`). The TUI link `term ▸ rig <name>` does the same open. To keep one Herdr workspace per org, create a tab there and run `tmux attach -t <seat>` (see vd:herdr). Closing a tile never stops a seat.
6. **Talk to it.**
   - Solo rig: type in the tile or use `rig send <seat> "…"`. Pi runner prefixes are `/followup <text>` and `/abort`; Claude Code seats take plain text.
   - Team rig: talk to the owner, and steer the writer directly only to unblock or abort it.
   - Chat is not recorded. Ask the seat to update `PROGRESS.md` or its queue item.
7. **Finish.** Update the slice, then remove each of its worktrees with the repo's own remove command or vd:worktree once it is merged or abandoned, never with unlanded work. A per-slice rig also runs `rig down <name>` (which strips OpenRig blocks from `$T/AGENTS.md`), deletes each `$T/<repo>` link and deletes `$T`. A team rig keeps running and keeps its task dir; only the slice's worktrees go.

## After a merge

- Refresh that repo's main checkout: fetch, then fast-forward its default branch only if the checkout is clean. Refresh any read-only reference copies the same way.
- Active worktrees pick the change up when they next merge the base (right before their own merge, or on a conflict) and rerun the repo's setup, which should add new `.env.example` keys without overwriting values.
- Stop and remove the merged worktree's stack and worktree.

## OpenRig gotchas

- `rig launch` wants the rig **id** from `rig ps --json`, not the name. `rig up` and `rig down` accept either; if a name matches several rigs, `rig down` refuses and lists the ids.
- To give an existing seat a fresh occupant: `rig seat launch <seat> --fresh --stop --reason "<why>"`.
- OpenRig launches Codex seats with `-s workspace-write`, unless a named Codex profile or `full_bypass` replaces it. They cannot reach the daemon unless `[sandbox_workspace_write] network_access = true`. A fresh launch on 0.6.1 or newer resolves a linked worktree's git dir. Prefer Claude Code or Pi seats when the seat must call the daemon.
- OpenRig launches Claude Code seats with `--permission-mode acceptEdits`, so the first Bash call waits for approval in the tile. The operator can switch that conversation to auto there (`shift+tab`). On 0.6 or newer, a future launch is `rig seat set-permissions <seat> --mode <mode> --reason "<why>"`. Modes are `floor`, `full_bypass`, and `inherit`. `auto` is accepted only when that seat's Claude executable advertises it. The command does not relaunch the seat, and `rig seat status` does not prove the live mode. Agents do not change another seat's permissions. The same boundary applies to `rig seat set-typing-guard`.
- On 0.6.1 or newer, OpenRig's own help is `rig context get help`. If `rig` cannot run, use [openrig.dev/help/agents](https://www.openrig.dev/help/agents).
- OpenRig 0.6 runs on Node.js 22 or 24. On macOS arm64, stay on Node.js 22. The CLI is the global npm package `@openrig/cli`, not a checkout of the source tree.
- In `rig tui`, `graph` is a tab of a selected rig: type `rig <name>`, then `graph`. `:` only jumps between sections.
- The daemon binds the Tailscale address too. Start it with `--host 127.0.0.1` unless you mean to expose it.

## Add a project

1. Create `orgs/<org>/<project>/` containing `AGENTS.md` (what it is, a repo table with each repo's role, rules), `SPEC.md` (frontmatter `intent:`), `project.yaml` (`schema: openrig.project/v0alpha1`, `metadata.id: <org>.<project>`), `repos.yaml`, and `missions/`.
2. Add `{id, root}` to `workspace.yaml`.
3. Add any new repo to `orgs/<org>/repos.yaml` with its per-machine paths.

## Workflow position

- **Composes:** vd:worktree (worktree mechanics), vd:workbench (artifacts), vd:herdr (panes and tabs).
- **Upstream OpenRig skills:** `openrig-skills` and `openrig-herdr` cover OpenRig itself. This skill only covers the workspace convention.
