# Org watch rig: set one up, run it, audit it

One parked rig per org collects that org's events into its knowledge tree (`kb/`, an Open Knowledge Format bundle filed by PARA). It has four pi-tui seats: `inbox`, `meetings` and `tickets` collect, and `dream` consolidates. The collectors start with the rig. The dream is parked until the operator enables it (see below). Once the template carries it, the rig also has a human seat (see below). There is no committer seat: the workspace sync job commits the tree on the org's watch host, behind `kb gate`. What a seat may do is in its role files and the workspace okf skill, not here. Where knowledge rules live: [org-knowledge.md](org-knowledge.md).

## Set up an org watch rig

Run it on the org's watch host. Each step has a check; stop at the first one that fails.

1. **Sources.** Add every source the rig reads to the org `resources.yaml`, one id per source (a Slack channel, a mailbox label, a calendar, a tracker project, a Drive folder). The id is the `source_ref` of its anchors, so each anchor must resolve to an entry. Accounts, channels, direct-message ids and the search order are data there, not in a role file. Check: every source id is in the org `resources.yaml`, and `scripts/check-resources.sh <project dir>` exits 0 for each project that lists one. For a tracker, also add a top-level `ticket_scope:` key (`source`, `involving`, `projects`, `exclude_done`, `first_run_days_back`): the tickets seat reads only that key and does nothing, reporting to the desk, when it is missing. A source whose kind has no anchor form (for example Teams) is not collected: say so in the resources file and tell the operator.
2. **Host.** Set `kb_host:` in `org.yaml` to a machine id from `fleet/machines.yaml`. Set it only at cutover: the field turns on the commit gate for that org on that host.
3. **Tree.** `"${PROJECTS_ROOT:-$HOME/projects}/bin/kb" init <org>`. It writes the root index, `log.md` and `inbox/triage.md` and no empty buckets. Check: `kb lint <org>` exits 0.
4. **Render the rig** from the template (no render script; the steps are these):
   1. Make `orgs/<org>/tasks/<org>-watch/` (gitignored) and copy `specs/rigs/org-watch/rig.yaml`, `AGENTS.md` and `watchdogs/` into it.
   2. In `rig.yaml` set `name: <org>-watch` and rewrite every pi-seat `agent_ref` to `local:../../../../specs/agents/pi-seat` (the path from that task dir; the human seat's `builtin:terminal` stays as it is). Keep each member's `env.PI_TUI_ROLE`: the launcher reads the role's skills and startup files from `specs/agents/<role>`.
   3. Once the template carries the human seat, this copy brings it along with the other members (it is part of `rig.yaml`; nothing extra to copy). In each `watchdogs/<member>.yaml` replace `<org>` with the org id. Copy `dream.member.yaml` into the task dir too (it stays unused until the dream is enabled).
   4. `fleet/bin/rig-to-pi convert rig.yaml watch` writes every model from the `watch` profile of `fleet/routing.yaml`: collectors at medium, the dream at high. Check quota with `cpq` and that each model id is live on the gateway first.
5. **Cursors.** For a new org, set each source's cursor 7 days back with `kb cursor set` (the first value, not a backward move). A migration resets cursors through its own plan, never through this step. Check: `kb due <org> <seat>` runs for each seat.
6. **Launch.** Run `fleet/bin/fleet-sync`, then `"${PROJECTS_ROOT:-$HOME/projects}/bin/fleet" toolchain --check`. Then in the task dir: `rig up rig.yaml --plan`, `rig up rig.yaml`, and register one watchdog for each collector:

   ```bash
   rig watchdog register --spec watchdogs/<member>.yaml --policy periodic-reminder \
     --target-session watch-<member>@<org>-watch --interval-seconds 1800 --registered-by <your session, or operator>
   ```

   Check: `rig ps --nodes --rig <org>-watch` shows three running collector seats (and the human seat once the template carries it), `fleet/bin/pi-rig-check <org>-watch` shows each seat's footer, and `rig watchdog list` shows three jobs with the one-line message.

## Enable the dream

The dream's member is not in `rig.yaml`, so the first launch never starts it. When it has passed review, run one command from the task dir:

```bash
rig add <org>-watch watch dream.member.yaml --rig-root "$PWD" && rig watchdog register --spec watchdogs/dream.yaml \
  --policy periodic-reminder --target-session watch-dream@<org>-watch --interval-seconds 1800 --registered-by <your session, or operator>
```

Check: `rig ps --nodes --rig <org>-watch` shows the dream running with the three collectors (and the human seat once the template carries it) and `rig watchdog list` shows the dream's job. To park it again, `rig watchdog stop <job id>` and `rig seat stop watch-dream@<org>-watch`.

## Human seat (once the template carries it)

The workspace rule is that every rig with more than two seats has one terminal member `<first pod>-human` that opens a shell running Pi, and the operator uses it to talk to the team. In an org watch rig the first pod is `watch`, so the session is `watch-human@<org>-watch`. Step 4's copy of the template brings it along; no step adds it by hand.

- It is not a collector: no role, no model, no watchdog and no `kb due`. The `agent_ref` rewrite and the model conversion leave it alone.
- Seats never route work to it and never type into it. A rig-wide broadcast lands there too, so message named seats.
- Until the template carries it, a watch rig has no human seat and nothing in this procedure needs one.

## Standing rules

- The rig runs only on its `kb_host` machine. Never launch it on another host.
- The only committer is the workspace sync job behind `kb gate`. A seat never runs `git`.
- To move a rig: stop it, change `kb_host`, run fleet-sync, and render and launch it on the new host (step 4 to 6). Cursors live in the task dir's `state/`, so copy `state/` over before launching or set them again.
- To retire one: stop it, remove the rig, and drop the org's `kb_host` so the gate stops running for it. The tree stays.
- To change a model: check the live list and `cpq`, edit the `watch` profile, rerun `rig-to-pi convert` (the dream's model is in `dream.member.yaml`; keep it equal to the profile), then `rig seat set-model` and `rig seat launch --fresh --stop` per seat.
- A seat that cannot continue sends one queue row to the org's conductor desk and stops. It never works around a refused command.

## Weekly audit

**This section starts when the audit job lands, after the first rollout. Until then no one runs it and the desk does nothing about it.** It names no command that the CLI does not have yet; the job's commands are added here when it ships.

The org's conductor desk runs it, read-only: it writes nothing to the tree. A model from a different family than the dream's checks the dream's work.

1. **Sample.** Ask the audit job's sample command for 20 Facts and 5 supersessions the dream wrote in one ISO week. The sample is deterministic and carries each item's citation, resolved.
2. **Check each item.** The cited day entry exists and supports every Jira key, number and date in the line, and says what the Fact says. A superseded line sits in `## History` with its evidence.
3. **Hand over.** Send the dream one queue row: the supported count and, for each failure, the path and code (never page text). The dream writes the audit log line through the CLI's log command.
4. **Cadence.** Weekly for the first four weeks after the job starts, then monthly.
5. **Below 90% supported.** Open a decision row for the operator to move the dream to a stronger model chosen per the model picker. The desk never changes a model.
