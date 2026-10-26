---
name: project-resources
description: Collects and maintains a projects-workspace project's resources.yaml (conversations, threads, environments, provider objects, links) and its org's contacts.yaml (people keyed by name) from live channels, agent session transcripts, queue rows and slice records, then shows the proposed diff and writes only after the user approves it. Activates when the user says 'update resources.yaml', 'collect resources for <project>', 'map the Slack channels and people for <project>', 'add this channel/thread/person to the project', 'refresh contacts', 'who do we talk to about <topic>', or 'record this thread so seats can find it'. Do not use for the workspace layout, task dirs or slice names - that is vd:openrig-workspace; it does not post or reply in any channel.
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
---

# Project resources

> Seats find people, conversations and provider objects through data files, not memory. Keep those files complete, keyed and private, and change them only with the user's yes.

## What this skill is - and isn't

| Job | Owner |
|---|---|
| Collect, propose and write `resources.yaml` / `contacts.yaml` entries | this skill |
| Workspace layout, task dirs, slices, worktrees | `vd:openrig-workspace` |
| Driving the browser for a logged-in app | the workspace's browser skill (Aside, agent-browser) |
| Replying, posting, reacting in any channel | nobody here: the owner does that |

Files (paths from `$PROJECTS_ROOT`, default `$HOME/projects`):

- `orgs/<org>/contacts.yaml` - every person once, keyed by a short name.
- `orgs/<org>/resources.yaml` - workspaces (Slack, Teams, email...), org-wide conversations, services.
- `orgs/<org>/projects/<project>/resources.yaml` - the project's conversations, threads, environments, provider objects, links, and `contacts: [{ref: <key>, role}]`.

Format: [references/resources-schema.md](references/resources-schema.md). Read it before the first edit.

## Hard rules

1. **Review before write.** Build the full proposed change, show it as a diff grouped by file (added, changed, removed, with the evidence for each line), and write nothing until the user says yes. Why: these files steer every seat; a wrong channel id or person sends work to the wrong place silently.
2. **Read-only collection.** Never post, reply, react, join a channel or change a setting while collecting. Opening a DM in a browser often marks it read: prefer search and channel history APIs, list DMs you opened in the report. Why: the owner speaks for the org; seats never message people.
3. **Evidence or nothing.** Every person's role, timezone and topics, and every conversation's purpose, comes from something you read (profile, messages, records). Mark gaps as unknown instead of guessing. Never infer pronouns or roles from a name.
4. **Private by default.** No secrets, tokens, API keys, full phone numbers (last 4 only, as `***1234`), or personal emails. If a source shows a secret (a key pasted in a DM), leave it out and report the exposure to the user; never rotate or test it.
5. **One home per fact.** A person lives once in the org `contacts.yaml`; projects reference the key. A workspace-wide channel lives in the org file; a project references it with `{ref: <id>, why}`. Why: duplicated entries drift apart.
6. **Native ids plus a deep link.** Store the app's own ids under `native:` (channel id, `thread_ts`, user id, agent id) and the URL a person can open. Names change; ids do not.
7. **Validate after writing.** Run `scripts/check-resources.sh <project dir>`; a dangling ref or a leaked phone fails it. Fix before reporting done.

## Workflow

1. **Resolve scope.** Project dir, its org dir, and what the user wants covered (all, one topic, one new thread). Read the current `resources.yaml`, the org `resources.yaml` and `contacts.yaml`.
2. **Collect from sources**, cheapest first, recording where each fact came from:

   | Source | What it yields | How |
   |---|---|---|
   | Project records (`AGENTS.md`, `SPEC.md`, missions, slice `PROGRESS.md`) | tickets, docs, environments, repo links | `grep -rhoE 'https?://…'` over the project tree |
   | Agent session transcripts for this workspace | thread links, ids, people and decisions from recent work | grep the harness's transcript dir for URLs, channel/thread ids and names; read only the matching lines |
   | Queue rows / seat messages | open asks, who asked what | the rig queue CLI, `--full` bodies |
   | Messaging apps (Slack, Teams...) | channels, DMs, group DMs, pinned/bookmarked links, people with profile title and timezone | the browser skill or the app CLI, read-only search over the last ~60 days on the project's watch terms |
   | Provider CLIs (voice, telephony, cloud) | agent/flow ids, tags, numbers (last 4), consoles | the provider's CLI, ids and names only |

3. **Draft the change.** Map each fact to the schema: new conversation, thread (`state: open|answered|closed`), contact, project contact ref, link, environment, provider object. Mark each with its evidence (message link, file, command).
4. **Show the diff and stop.** Present it per file with the evidence column and the list of anything left out (secrets, unverifiable people, DMs that were marked read). Ask for yes, edits, or no.
5. **Write on yes.** Edit with a YAML-aware tool (`yq -i`) or exact text edits; keep existing comments and style. Do not reformat untouched entries.
6. **Validate and report.** `scripts/check-resources.sh <project dir>` must exit 0. Report what changed, what was skipped and why, and any exposure found.

## Anti-patterns

- Writing straight into the file because the user asked to "update" it: the update is the proposal; the write follows the review.
- Copying a whole people dump into a project file instead of `contacts: [{ref}]`.
- A conversation entry with only a name: no `native` id, no URL, no purpose.
- "Probably owns X" from one message: say what the evidence shows or leave the topic out.
- Opening every DM in the browser to "check": it marks them read for the owner.
