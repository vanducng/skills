# Project resources and contacts

Seats find people, conversations and provider objects through data files, not memory. Keep those files complete, keyed and private, and change them only with the user's yes.

Read this when the user says "update resources.yaml", "collect resources for <project>", "map the channels and people for <project>", "add this channel/thread/person", "refresh contacts", "who do we talk to about <topic>", or "record this thread so seats can find it".

Files (paths from `$PROJECTS_ROOT`):

- `orgs/<org>/contacts.yaml` - every person once, keyed by a short name.
- `orgs/<org>/resources.yaml` - workspaces (Slack, Teams, email...), org-wide conversations, services, `secrets:`.
- `orgs/<org>/projects/<project>/resources.yaml` - the project's conversations, threads, environments, provider objects, links, and `contacts: [{ref: <key>, role}]`.

Format: [resources-schema.md](resources-schema.md). Read it before the first edit. Driving a logged-in app is the workspace's browser skill (Aside, agent-browser). Replying, posting or reacting in any channel is nobody's job here: the owner does that.

## Rules

1. **Review before write.** Build the full proposed change, show it as a diff grouped by file (added, changed, removed, with the evidence for each line), and write nothing until the user says yes. These files steer every seat; a wrong channel id or person sends work to the wrong place silently.
2. **Read-only collection.** Never post, reply, react, join a channel or change a setting while collecting. Opening a DM in a browser often marks it read: prefer search and channel history APIs, and list DMs you opened in the report.
3. **Evidence or nothing.** Every person's role, timezone and topics, and every conversation's purpose, comes from something you read (profile, messages, records). Mark gaps as unknown. Never infer pronouns or roles from a name.
4. **Private by default.** No secrets, tokens, API keys, full phone numbers (last 4 only, as `***1234`), or personal emails. If a source shows a secret, leave it out and report the exposure to the user; never rotate or test it.
5. **One home per fact.** A person lives once in the org `contacts.yaml`; projects reference the key. A workspace-wide channel lives in the org file; a project references it with `{ref: <id>, why}`.
6. **Native ids plus a deep link.** Store the app's own ids under `native:` (channel id, `thread_ts`, user id, agent id) and the URL a person can open. Names change; ids do not.
7. **Validate after writing.** `bash "$HOME/skills/skills/openrig-workspace/scripts/check-resources.sh" <project dir>` must exit 0. A dangling ref or a leaked phone fails it.

## Workflow

1. **Resolve scope.** Project dir, its org dir, and what the user wants covered (all, one topic, one new thread). Read the current project `resources.yaml`, the org `resources.yaml` and `contacts.yaml`.
2. **Collect**, cheapest first, recording where each fact came from:

   | Source | Yields | How |
   |---|---|---|
   | Project records (`AGENTS.md`, `SPEC.md`, missions, slice `PROGRESS.md`) | tickets, docs, environments, repo links | `rg -o 'https?://\S+'` over the project tree |
   | Agent session transcripts for this workspace | thread links, ids, people, decisions | grep the harness's transcript dir for URLs, channel and thread ids and names; read only the matching lines |
   | Queue rows and seat messages | open asks, who asked what | `rig queue` with `--full` bodies |
   | Messaging apps | channels, DMs, pinned links, people with title and timezone | the browser skill or the app CLI, read-only search over about 60 days on the project's watch terms |
   | Provider CLIs (voice, telephony, cloud) | agent and flow ids, tags, numbers (last 4), consoles | the provider's CLI, ids and names only |

3. **Draft.** Map each fact to the schema (conversation, thread with `state: open|answered|closed`, contact, project contact ref, link, environment, provider object) with its evidence.
4. **Show the diff and stop.** Per file, with the evidence column and what was left out (secrets, unverifiable people, DMs that were marked read). Ask for yes, edits, or no.
5. **Write on yes** with `yq -i` or exact text edits. Keep comments and style; do not reformat untouched entries.
6. **Validate and report** what changed, what was skipped and why, and any exposure found.

## Anti-patterns

- Writing straight into the file because the user asked to "update" it: the update is the proposal; the write follows the review.
- Copying a people dump into a project file instead of `contacts: [{ref}]`.
- A conversation entry with only a name: no `native` id, no URL, no purpose.
- "Probably owns X" from one message: say what the evidence shows or leave the topic out.
