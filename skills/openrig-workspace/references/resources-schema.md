# resources.yaml v2 and contacts.yaml

`resources.yaml` is data only: what a seat needs to find and reach a project's people, conversations, tools and environments. Never secrets, full phone numbers or emails of outside people.

v1 kept a flat channel list (`{id, name, channel_id, tags}`) in the org file and `{ref, why}` pointers in the project file. It had no place for DMs, threads, people, per-app ids or what a seat may do there. v2 adds that with one model for every messaging app.

## Model

Four layers, the same in every app:

| Layer | Slack | Teams | Discord | Google Chat | Telegram | Email |
|---|---|---|---|---|---|---|
| workspace | team `T…` | tenant + team | guild | Workspace domain | bot/account | mailbox |
| conversation | channel `C…`, private `G…`/`C…`, DM `D…`, group DM | channel `19:…@thread.tacv2`, chat `19:…@unq.gbl.spaces` | channel | `spaces/…` (space or DM) | `chat_id` | label or list |
| thread | `thread_ts` | reply chain (message id) | thread channel | `spaces/…/threads/…` | `message_thread_id` | thread id |
| message | `ts` | message id | message id | `…/messages/…` | message id | Message-ID |
| contact | `U…` | AAD object id | user id | `users/…` | user id | address (own org only) |

## Keys

```yaml
schema: projects.resources/v2
workspaces:                    # org file; projects ref them
  - id: slack                  # local slug, referenced everywhere below
    kind: slack                # slack | teams | discord | google-chat | telegram | whatsapp | sms | email | matrix
    url: https://<org>.slack.com
    native: {team_id: T…}      # provider ids, as the provider names them
    read_via: {tool: aside, account: u1}
    write_via: {tool: aside, account: u1}
    hazards: ["opening a DM marks it read"]

conversations:                 # channels, DMs, group DMs, spaces, mailing lists
  - id: <channel-slug>
    workspace: slack
    kind: channel              # channel | private-channel | dm | group-dm | space | list
    name: "#<channel>"
    native: {channel_id: C…}
    url: https://<org>.slack.com/archives/C…
    with: [<contact key>]              # people ids, for dm and group-dm
    purpose: product decisions and releases
    policy: {read: yes, post: owner-only}   # yes | owner-only | never
    tags: [project:<project>]

threads:                       # long-lived threads worth returning to
  - id: <person>-<topic>
    conversation: dm-<person>
    native: {thread_ts: "<ts>"}
    url: https://<org>.slack.com/archives/D…/p<ts without dot>
    topic: <what is being decided>
    opened: <YYYY-MM-DD>
    state: open                # open | answered | closed

contacts:                      # project file: who matters here, by key into the org contacts.yaml
  - {ref: <contact key>, role: <their role in this project>}
```

`orgs/<org>/contacts.yaml` holds each person once, keyed by a short name:

```yaml
schema: projects.contacts/v1
org: <org>
contacts:
  <contact key>:
    name: <full name>
    title: <profile title>
    tz: <IANA zone>
    handles: {slack: {user_id: U…, dm: D…, dm_url: https://<org>.slack.com/archives/D…}}
    topics: [<topic slugs from message evidence>]
    projects: [<project ids>]
```

Rules:

- `id` is a local slug; `native` holds the app's own ids, so a seat can build an API call or URL without guessing. `url` is the deep link a person can open.
- The org file holds `workspaces` and org-wide `conversations`; `contacts.yaml` beside it holds people, keyed by name. A project file holds its own conversations, threads and people, and may `ref:` an org entry instead of repeating it (`- {ref: <channel-slug>, why: …}`).
- `policy` states what a seat may do there. Default is `read: yes, post: never`: posting stays with the owner unless a brief grants it.
- `threads` are for threads that carry an open question or a decision. Close them (`state`) rather than delete them, so the history stays findable.
- People live once in the org `contacts.yaml`; projects list `contacts: [{ref: <key>, role: …}]` and conversations name them in `with: [<key>]`. Role, timezone and topics come from message evidence. No phone numbers, no personal emails.

## Validation

`scripts/check-resources.sh <project dir>` checks: every `contacts[].ref` exists in the org `contacts.yaml`, every `with:` key exists, every thread's `conversation` exists, and no file holds a full phone number, a home path, or a key-like value.

## Migration

v1 files keep working. Move a file to v2 when it is next edited: `messaging[].channels[]` become `workspaces` + `conversations`, `channel_id` moves under `native`.
