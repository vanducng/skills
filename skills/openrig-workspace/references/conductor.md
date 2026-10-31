# Conductor: one front door for every rig on every host

The conductor is a workspace project (`<operator-org>.conductor`) whose one rig gives the operator a single place to talk to and decide for every rig on every host. Its rules are the project's own `AGENTS.md`. This page covers how it works and how to run, move, grow and shrink it.

## Shape

| Seat | Role | Model |
|---|---|---|
| `orch-lead@conductor` | `conductor`: the operator's conversation; reads desk digests, sends desks work | reasoning family, medium |
| `orch-human@conductor` | terminal running `rig tui` (Feed, Mission Control) | none |
| `desk-<org>@conductor` | `desk`: every active project of one org; read-only plus queue rows | execution family, medium |

- One desk per org, not per project, so the seat count tracks orgs and a new project needs no roster change. Pod `desk`, member = org, so addresses never repeat a word.
- Models come from the `conductor` profile in the routing file (`pi.profiles`), applied by the fleet's Pi converter. Keep the conductor off the model reserved for watch rigs.
- Desk state is a record, `desks/<org>.md` in the conductor project, one section per project. Workspace sync commits it on the pinned host, which is what makes the rig portable.
- The human the desks ask (`<operator>@external`) is registered only on the conductor's daemon. Other daemons keep an empty gateway, so a stray direct ask fails loudly.

## Routes

Every machine in the machines file has `openrig_id` and `openrig_url`. Every host carries a route to every *other* machine's `openrig_id`. It never carries a route to itself or an alias: `rig tui` lists every registry entry as a host, so a self route or an alias shows the same rigs twice.

- A desk passes `--host <openrig_id>` for `rig ps` and `rig queue create`, and `OPENRIG_URL=<openrig_url>` for the queue verbs that have no `--host` (`list`, `show`, `handoff`). Both are dropped when the project's machine is the conductor's own.
- A project lead escalates with `rig queue create --host "$(fleet/bin/conductor where)" --destination desk-<org>@conductor ...`. `where` reads the pin from git, so no brief names a machine, and it prints nothing on the conductor's own host.

`conductor routes` keeps every machine's registry in this shape over ssh, and removes self routes and old aliases.

## Run it

All of it goes through `fleet/bin/conductor`:

```bash
fleet/bin/conductor status          # pinned host, where it runs; warns on two copies or a wrong host
fleet/bin/conductor up              # on the pinned host only: sync, render tasks/conductor, convert models, register the human, routes, rig up
fleet/bin/conductor view            # on the pinned host: the one Rex view (rig terminal open conductor --provider rex)
fleet/bin/conductor down            # commits desk state first; refuses while conductor seats hold open queue rows
fleet/bin/conductor move <machine>  # down, repin repos.yaml, push, repoint routes, up on <machine>
```

`up` refuses on any machine other than the pinned one. While a conductor runs elsewhere it also refuses, unless you pass `--force`, which only warns: two conductors answer the same leads twice, so keep one.

What a move carries: the roster, roles, routes and desk files. What it leaves behind on the old daemon: queue history, gateway asks and answers, and seat conversations. Drain open rows before moving. The old copy is archived there, hidden from `rig ps` and the TUI; `rig unarchive <rig id>` brings that history back. A later `rig up` on that host creates a new rig and leaves the archived one hidden.

## Talk to it from any machine

`conductor view` opens the rig's one Rex view, `rig terminal open conductor --provider rex`, on the conductor host's own Rex server: one tile per seat, and the lead's tile is where the operator types. Keep it the only view: a second view on the same seats makes the tmux tile-fit hook resize them back and forth. Open that session from the Rex app on a desktop or phone, after adding the host by its server address (`rex_url` in the machines file). Don't attach to the seats' tmux over ssh.

## Add a desk

Only a new org gets a desk. A new project in an existing org is picked up by that org's desk from the workspace file, with no roster change.

1. Add the member under pod `desk` in the conductor project's `rig.yaml`, with `PI_TUI_ROLE: desk`, `DESK_ORG: <org>` and `restore_policy: relaunch_fresh`, plus the two edges (`delegates_to` from `orch.lead`, `escalates_to` back). Add `desks/<org>.md`. Commit.
2. On the conductor host, run `conductor down && conductor up`, or add it live with `rig add conductor desk <member fragment>` after converting the fragment's model.
3. Check `rig ps --nodes --rig conductor` and the seat's Pi footer.
4. Point the org's project leads at the desk (the escalation line above).

## Archive a project's section

When a project is archived, its desk drops it: the project's `resources.yaml` gets `status: archived`, and the desk skips it from then on.

1. **Drain.** No open row on `desk-<org>@conductor` names the project. Close each truthfully or hand it to `orch-lead@conductor`.
2. **Last word.** The desk sends one `--human-intent update`: "<project> archived, nothing waiting".
3. **Keep the digest.** Copy the project's section to `~/.share/openrig/<org>/<project>/conductor-final-digest.md`, cite it from the project hub with an `evidence:` line, and delete the section. Commit.

Remove a whole desk only when its org has no active project left: drain it, `rig remove <conductor rig id> desk.<org> --fallback orch-lead@conductor`, delete the member, its edges and `desks/<org>.md`, and check `rig up <task>/rig.yaml --plan` from the rendered task dir.

## Costs

Idle desks cost nothing. They wake on queue events: a lead's ask, a human answer, or the lead sending work. Don't give each desk a periodic reminder, because every wake is a model turn. If digests must be refreshed on a schedule, use a deterministic script that fingerprints `rig ps` and the queue and nudges only the desks whose fingerprint changed.
