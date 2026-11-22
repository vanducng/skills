# Org seats: where an org's decisions and escalations go

Each org has one seat that takes its decisions and escalations: `<seat>-<org>@<intake rig>`, in an intake rig the operator's workspace project holds. The seat watches the rigs of that org's active projects on every host, keeps the desk state, brings decisions to the operator and routes his answers back to the leads. It is read-only plus queue rows. The workspace's own `AGENTS.md` names the real seat and rig. An org with no seat yet has no fallback address: the operator decides where its decisions go, and until he does, the lines that would name one carry a TODO.

This replaces the older single conductor rig (an `orch-lead` the operator talked to plus one `desk-<org>` seat per org). A workspace that retires it should make its repo lint fail on any live address on the retired rig in instruction and routing files (agent files, briefs, specs, fleet scripts, docs), and leave records alone.

## Reaching the seat

- A project lead escalates with `rig queue create --host "$(bin/fleet project-host --route <intake rig>)" --destination <seat>-<org>@<intake rig> ...`. `--route` reads the rig's pinned machine from the workspace file and the machines file, so no brief names a machine; it prints nothing on that machine, where `--host` is dropped.
- The seat passes `--host <openrig_id>` for `rig ps` and the queue verbs (`create`, `list`, `show`, `handoff`) when a project's machine is not its own.
- Workspace tooling that queues to the org (sync alerts, kb gate routing) reads the seat name from one function, so a new layout (for example one intake rig per org) is a one-line change.

## Routes

Every machine in the machines file has `openrig_id` and `openrig_url`. Every host carries a route to every *other* machine's `openrig_id`, and never a route to itself or an alias: `rig tui` lists every registry entry as a host, so a self route or an alias shows the same rigs twice. The fleet's `rig-routes` script keeps every machine's registry in this shape over ssh and removes self routes and old aliases.

## Desk state

Desk state is a record, `desks/<org>.md` in the intake rig's project, one `## <project>` section each (digest, open asks with their queue ids, last seen in UTC). Workspace sync commits it on the pinned host, so a move to another host starts from it. No secrets, transcripts or client data in it.

## Add or drop a project

A new project needs no change: the seat covers every active project of its org. To drop one (archived, or moved to another org), close or hand off its open rows truthfully, keep its last section as the final digest under the project's capture folder, and delete the section.
