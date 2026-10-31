# Conductor: one front door for every rig on every host

The conductor is a workspace project (`<operator-org>.conductor`) whose one rig gives the operator a single place to talk to and decide for every rig on every host. Its rules are the project's own `AGENTS.md`. This page covers how it works and how to run, move, grow and shrink it.

## Shape

| Seat | Role | Model |
|---|---|---|
| `orch-lead@conductor` | `conductor`: the operator's conversation; reads desk digests, sends desks work | reasoning family, medium |
| `orch-human@conductor` | terminal running `rig tui` (Feed, Mission Control) | none |
| `<org>-<desk>@conductor` | `desk`: one project; read-only plus queue rows | execution family, medium |

- Pods are orgs, members are short project names, so addresses never repeat a word.
- Models come from the `conductor` profile in the routing file (`pi.profiles`), applied by the fleet's Pi converter. Keep the conductor off the model reserved for watch rigs.
- Desk state is a record, `desks/<org>-<desk>.md` in the conductor project. Workspace sync commits it on the pinned host, which is what makes the rig portable.
- The human the desks ask (`<operator>@external`) is registered only on the conductor's daemon. Other daemons keep an empty gateway, so a stray direct ask fails loudly.

## Routes

Every machine in the machines file has `openrig_id` and `openrig_url`. Every host carries:

- a route to every `openrig_id`, its own included, so a desk always passes `--host <openrig_id>` and the command works wherever the conductor runs;
- the alias `conductor`, pointing at the pinned host. Project leads escalate with `rig queue create --host conductor --destination <org>-<desk>@conductor ...`, so no brief names a machine.

`conductor routes` writes both on every machine (over ssh) and repoints the alias after a move.

## Run it

All of it goes through `fleet/bin/conductor`:

```bash
fleet/bin/conductor status          # pinned host, where it runs; warns on two copies or a wrong host
fleet/bin/conductor up              # on the pinned host only: sync, render tasks/conductor, convert models, register the human, routes, rig up
fleet/bin/conductor view            # on the pinned host: rig terminal open conductor --provider rex
fleet/bin/conductor down            # commits desk state first; refuses while conductor seats hold open queue rows
fleet/bin/conductor move <machine>  # down, repin repos.yaml, push, repoint routes, up on <machine>
```

`up` refuses on any machine other than the pinned one. While a conductor runs elsewhere it also refuses, unless you pass `--force`, which only warns: two conductors answer the same leads twice, so keep one.

What a move carries: the roster, roles, routes and desk files. What it leaves behind on the old daemon: queue history, gateway asks and answers, and seat conversations. Drain open rows before moving.

## Look at it from any machine

The view is a Rex session on the conductor host's own Rex server. From another machine, connect with that server's address (`rex_url` in the machines file): `rex -S <rex_url> ls`, or add the host in the Rex app. Don't attach to the seats' tmux over ssh. Keep one view per rig.

## Add a desk

1. Add the member under its org pod in the conductor project's `rig.yaml`, with `PI_TUI_ROLE: desk`, `DESK_PROJECT: <org>.<project>` and `restore_policy: relaunch_fresh`, plus the two edges (`delegates_to` from `orch.lead`, `escalates_to` back). Add `desks/<org>-<desk>.md`. Commit.
2. On the conductor host, run `conductor down && conductor up`. Or, to avoid restarting the other seats, add it live with `rig add conductor <org> <member fragment>` and convert the fragment's model first.
3. Check `rig ps --nodes --rig conductor` and the seat's Pi footer.
4. Point the project lead's brief at the desk (the escalation line above).

## Archive a desk

Run this only as part of archiving its project, after the operator says to archive.

1. **Drain.** `rig queue list --destination <org>-<desk>@conductor` shows no open row. Close each truthfully or hand it to `orch-lead@conductor`.
2. **Last word.** The desk sends one `--human-intent update`: "<project> archived, nothing waiting".
3. **Keep the digest.** Copy the desk file to `~/.share/openrig/<org>/<project>/conductor-final-digest.md` and cite it from the project hub with an `evidence:` line.
4. **Remove live.** `rig remove <conductor rig id> <org>.<desk> --fallback orch-lead@conductor`.
5. **Remove from the roster.** Delete the member, its edges and its desk file. Run `rig up <task>/rig.yaml --plan` from the rendered task dir to confirm no dangling edge. Commit.
6. **Verify.** `rig ps --nodes --rig conductor` no longer lists it. Record one `conductor desk removed` line in the project's PROGRESS.

## Costs

Idle desks cost nothing. They wake on queue events: a lead's ask, a human answer, or the lead sending work. Don't give each desk a periodic reminder, because every wake is a model turn. If digests must be refreshed on a schedule, use a deterministic script that fingerprints `rig ps` and the queue and nudges only the desks whose fingerprint changed.
