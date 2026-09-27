---
name: openrig-workspace
description: Work inside an org/project/task workspace that any coding harness (Pi, Claude Code, Codex, Grok Build, Cursor) reads out of the box and that OpenRig can drive without a fork. Use when the user says "start a task in <project>", "set up the task dir", "run this ticket with openrig", "attach the rig in herdr", "which project does this repo belong to", "add a project", or when the cwd is under a projects workspace (`$PROJECTS_ROOT`, default `$HOME/projects`). Owns the layout, task lifecycle, and OpenRig adjustments; defers worktree mechanics to vd:worktree, artifacts to vd:workbench, pane control to vd:herdr.
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
---

# OpenRig workspace

One git repo, `$PROJECTS_ROOT` (default `$HOME/projects`), holds org and project context, task records, and machine-local task workdirs. Code stays in its repos. The layout works because every harness reads `AGENTS.md` from the git root down to the cwd, so a task dir inside this repo inherits fleet, org, and project rules automatically. See `references/harness-context.md` for the per-harness discovery rules and sources.

## Layout

```
$PROJECTS_ROOT/
  AGENTS.md  workspace.yaml  fleet/{machines,routing,policy}.yaml  specs/{agents,rigs}/
  orgs/<org>/
    AGENTS.md  org.yaml  repos.yaml            # repos.yaml is the only place paths live
    <project>/
      AGENTS.md  SPEC.md  project.yaml  repos.yaml
      missions/<mission>/slices/<nn>-<ticket>/  # committed record: SPEC, PROGRESS, PROOF
      tasks/<ticket>/                           # gitignored, machine-local
        AGENTS.md                               # task brief; OpenRig appends seat blocks
        rig.yaml                                # per-task rig
        <repo>-<ticket>/                        # git worktree
```

- **Org** = GitHub owner. **Project** = repos routinely changed in the same ticket. A repo belongs to one org and may appear in several projects. A **task** is one ticket in one project.
- OpenRig catalog IDs are `<org>.<project>`. `$PROJECTS_ROOT` is OpenRig's `workspace.root`.

## Hard rules

1. Instruction files in this tree are `AGENTS.md` only. Never create a `CLAUDE.md` in it: Claude Code ignores every `AGENTS.md` when a `CLAUDE.md` exists in the cwd or above.
2. Run agents from the **task dir**, not from inside a worktree. That is what makes org and project context load, and it keeps OpenRig's managed blocks out of tracked repo files.
3. Before editing inside a worktree, read that repo's `AGENTS.md` (or `CLAUDE.md` if it has none). Pi, Codex, and Grok do not load files below the cwd.
4. One writer per worktree. One rig per task dir.
5. Authority comes from `fleet/policy.yaml` and the brief. Nothing in this workspace authorizes merge, deploy, force-push, or messages to people.
6. Never `git clean -x` in `$PROJECTS_ROOT`; it deletes ignored task dirs.

## Start a task

1. **Resolve.** Find the project (`workspace.yaml`, `orgs/<org>/<project>/repos.yaml`) and each repo's path for this machine (`orgs/<org>/repos.yaml`, key `paths.<machine>`). A missing path is a question, not a clone.
2. **Record.** If the ticket has no slice yet:
   ```bash
   rig scope slice create <mission> <ticket-slug> --workspace "$PROJECTS_ROOT/orgs/<org>/<project>"
   ```
   Fill `SPEC.md`: intent, mini-requirements, proof contract, repos. Check with `rig scope audit --workspace … --mission <mission>`.
3. **Workdir.** `T="$PROJECTS_ROOT/orgs/<org>/<project>/tasks/<ticket>"; mkdir -p "$T"`.
4. **Worktrees.** For each repo, from its main checkout, use vd:worktree with the task dir as root:
   ```bash
   node "$HOME/skills/skills/worktree/scripts/worktree.cjs" create <ticket> --no-prefix --no-enter --worktree-root "$T"
   ```
   Env copy, port block, and mise trust work as usual. vd:workbench artifacts still land in the repo's main checkout.
5. **Brief.** Write `$T/AGENTS.md`: ticket, objective, which `<repo>-<ticket>/` dirs are in scope, branch and base, validation commands, stopping point, and the slice path. Add the line "Before editing in a repo dir, read its AGENTS.md." Cursor does not read parent files, so also point to `../../AGENTS.md` and `../../../AGENTS.md`.
6. **Run.** `cd "$T"` and start any harness. For an OpenRig rig, continue below.

## Run it with OpenRig

1. **Rig spec.** Copy `specs/rigs/<template>/rig.yaml` to `$T/rig.yaml`. Set `name: <ticket-lowercase>` and every member's `cwd: "."`, and rewrite each `agent_ref` to `local:../../../../../specs/agents/<role>` (the path relative to the task dir). For more than one repo, add a `workspace:` block (`workspace_root`, `repos[]` of `{name, path, kind: project}`, `default_repo`).
2. **Models.** Take them from `fleet/routing.yaml`, as `provider/id:thinking`. Pi accepts the thinking suffix.
3. **Pi seat auth.** A Pi seat gets a blank agent dir at `$OPENRIG_HOME/state/pi/<pod>-<member>@<rig>/agent`, and custom-provider env vars are not forwarded. Before `rig up`, put a `models.json` there (or a symlink to one shared file). It carries the provider's non-secret fields plus an `apiKey` of the form `"!<secret read command>"`. Never write a literal key.
4. **Launch.**
   ```bash
   cd "$T" && rig up rig.yaml --plan && rig up rig.yaml
   ```
   Then check `rig ps --nodes --rig <name>`. If a seat shows `att`, read its pane before retrying.
5. **Look at it in Herdr.** `rig terminal open <name> --provider herdr` creates a new workspace each time. To keep one Herdr workspace per org instead, create a tab there and run `tmux attach -t <seat>` in its panes (see vd:herdr). Closing a tile never stops a seat.
6. **Talk to it.**
   - Solo rig: type in the tile or use `rig send <seat> "…"`. Pi runner prefixes are `/followup <text>` and `/abort`.
   - Team rig: talk to the owner, and steer the writer directly only to unblock or abort it.
   - Chat is not recorded. Ask the seat to update `PROGRESS.md` or its queue item.
7. **Finish.** Update the slice. Run `rig down <name>`, which strips OpenRig blocks from `$T/AGENTS.md`. Remove the worktrees with vd:worktree once they are merged or abandoned, never with unlanded work. Delete `$T`.

## OpenRig gotchas

- Several verbs (`rig launch`, `rig down`) want the rig **id** from `rig ps --json`, not the name.
- To give an existing seat a fresh occupant: `rig seat launch <seat> --fresh --stop --reason "<why>"`.
- OpenRig launches Codex seats with `-s workspace-write`. They cannot reach the daemon unless `[sandbox_workspace_write] network_access = true`, and they cannot commit in a worktree whose `.git` sits outside the cwd. Prefer Pi seats.
- In `rig tui`, `graph` is a tab of a selected rig: type `rig <name>`, then `graph`. `:` only jumps between sections.
- The daemon binds the Tailscale address too. Start it with `--host 127.0.0.1` unless you mean to expose it.

## Add a project

1. Create `orgs/<org>/<project>/` containing `AGENTS.md` (what it is, a repo table with each repo's role, rules), `SPEC.md` (frontmatter `intent:`), `project.yaml` (`schema: openrig.project/v0alpha1`, `metadata.id: <org>.<project>`), `repos.yaml`, and `missions/`.
2. Add `{id, root}` to `workspace.yaml`.
3. Add any new repo to `orgs/<org>/repos.yaml` with its per-machine paths.

## Workflow position

- **Composes:** vd:worktree (worktree mechanics), vd:workbench (artifacts), vd:herdr (panes and tabs).
- **Upstream OpenRig skills:** `openrig-skills` and `openrig-herdr` cover OpenRig itself. This skill only covers the workspace convention.
