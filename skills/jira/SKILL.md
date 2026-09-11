---
name: jira
description: "Manage Jira issues via CLI and REST. View, create, update, transition, assign, comment, and run sprint ops, including evidence follow-ups, native mentions, inline images, structured ADF comments, and board-column moves. Use when user mentions issue keys (PROJ-123), tickets, follow-ups, sprints, or keywords like jira/ticket/backlog."
license: MIT
argument-hint: "[--project ALIAS] [--type bug|task] [ISSUE-KEY|request]"
metadata:
  author: vanducng
  version: "1.3.0"
---

# Jira Integration (CLI Backend)

Uses the [`vanducng/jira-cli`](https://github.com/vanducng/jira-cli) fork, which preserves upstream compatibility and adds native inline local-image comments. Confirm the active binary supports the feature before an image write:

```bash
jira issue comment add --help | rg -- '--image'
```

## Invocation Flags

```text
vd:jira --project acme --type bug create ticket for the failed import
vd:jira --project acme --type task create ticket for the cleanup
```

- `--project ALIAS`: Load `~/.config/vd/jira-rules/<alias>.jira-rules.md`.
- `--type bug|task`: Set the issue type and apply that type's local defaults.
- Infer the project alias from the issue key only when a loaded rule maps that prefix. Ask when missing or ambiguous.

Copy `references/project.jira-rules.example.md` to the local rules directory and customize it. Never commit local company rule files.

## Authentication (MANDATORY - run FIRST)

Before any Jira operation:

1. Resolve `--project` and load `~/.config/vd/jira-rules/<alias>.jira-rules.md` completely.
2. Read the base URL, token environment variable, email environment variable, and optional board defaults from that file.
3. Source the configured environment file and export `JIRA_API_TOKEN`, `JIRA_USER_EMAIL`, and `JIRA_BASE_URL` without printing their values.
4. Prepend the same setup to every Jira CLI and curl command in the session.

Refuse to proceed when the rules file is missing connection metadata. Never print, commit, attach, or copy tokens into tickets, logs, or rule samples.

## Ticket Content

For Bug and Task creation, keep the ticket direct:

- State the bare symptom and basic finding.
- Include one short sample error when available.
- Put provided screenshots and diagrams **inline in the description** (REST v3 ADF `mediaSingle`, left-aligned, 100% width). Upload as an attachment only as the media source. Never leave evidence as attachment-only or as a CLI 200 px thumbnail.
- Load `references/inline-images.md` before any image write (create, edit, or comment).
- Omit implementation details, proposed code, and speculative analysis unless requested.
- Apply assignee, sprint, parent, and initial status from the matching local type rules.

## Instance Rules (MANDATORY - load before writes)

One file per Jira instance at `~/.config/vd/jira-rules/<instance>.jira-rules.md`, authoritative for issue-type mapping, assignee, sprint, parent, initial status, and ticket content. Resolve dynamic values (`me`, the current active sprint, transition IDs) from Jira before showing the proposed payload. If the requested type is not a native Jira type, use the rule's Jira type and labels. Explicit user instructions override the rule file - state the override. No rule file → continue with the base safety protocol and tell the user no instance defaults were applied.

## Safety Protocol (MANDATORY)

1. **Read before write** - always fetch current state before modifications
2. **Show before execute** - display proposed changes (every rule-derived field), get approval (`AskUserQuestion` in Claude Code; plain-text question elsewhere)
3. **Verify after execute** - confirm the operation succeeded
4. **No bulk changes** without explicit user approval
5. **Never transition** without checking available transitions first

## Quick Reference

### View & Search
```bash
jira issue view ISSUE-KEY                    # View issue
jira issue view ISSUE-KEY --raw             # Raw fields for parent/sprint/custom fields
jira issue view ISSUE-KEY --raw | jq '{key:.key,parent:.fields.parent.key,sprint:.fields.customfield_10016}'
jira issue list -a$(jira me)                 # My issues
jira issue list -s"In Progress"              # By status
jira issue list -q"JQL_QUERY"               # Raw JQL
jira sprint list --state active              # Active sprint
```

### Create
```bash
jira issue create -tBug -s"Summary" -b"Description" -yHigh
jira issue create -tTask -s"Summary" -a$(jira me) --no-input
```

**Multi-line descriptions:** Write to `/tmp` first, then use `-b"$(cat /tmp/jira_body.md)"`. When headings/lists must render cleanly, use the REST ADF pattern below instead of CLI `-b`.

**CRITICAL - Underscore escaping bug:** The `jira` CLI escapes `_` to `\_` in descriptions, breaking code blocks. After creating/editing an issue with code snippets or underscored identifiers, ALWAYS update the description via REST API:
```bash
curl -s -X PUT "${JIRA_BASE_URL}/rest/api/3/issue/<KEY>" \
  -u "${JIRA_USER_EMAIL}:${JIRA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @/tmp/jira_update.json
```
Use Atlassian Document Format (ADF) with `codeBlock` node for code. See the REST ADF Description Pattern section below for the ADF payload structure.

### Modify
```bash
jira issue move ISSUE-KEY "In Progress"      # Transition
jira issue assign ISSUE-KEY $(jira me)       # Assign to self
jira issue comment add ISSUE-KEY "Comment"   # Add comment (positional body, no -b flag)
jira sprint add SPRINT-ID ISSUE-KEY          # Add to active/known sprint
jira issue link ISSUE-1 ISSUE-2 Relates      # Link issues
```

### Follow-up Comments and Board Columns

Read [`references/follow-up.md`](references/follow-up.md) before posting an evidence update with JSON/code or native mentions, or when the user names a board column (review, QA, staging) instead of an exact workflow status. It carries the REST v3 ADF recipes (plain `@Display Name` does not notify) and the board-column → status-ID → available-transition resolution - never assume the column label is the status name.

### REST ADF Description Pattern
Use this for clean Jira descriptions with sections and bullets (CLI `-b` paragraphs containing `- item` render as plain text):
```bash
payload=$(jq -n '{fields:{description:{type:"doc",version:1,content:[
  {type:"heading",attrs:{level:3},content:[{type:"text",text:"Goal"}]},
  {type:"paragraph",content:[{type:"text",text:"…"}]},
  {type:"bulletList",content:[{type:"listItem",content:[{type:"paragraph",content:[{type:"text",text:"…"}]}]}]}
]}}}')
curl -sS -X PUT "${JIRA_BASE_URL}/rest/api/3/issue/<KEY>" \
  -u "${JIRA_USER_EMAIL}:${JIRA_API_TOKEN}" \
  -H "Accept: application/json" -H "Content-Type: application/json" \
  -d "$payload" -w "\nHTTP %{http_code}\n"
```

### Other
```bash
jira me                                      # Current user
jira open ISSUE-KEY                          # Open in browser
jira project list                            # List projects
jira board list                              # List boards
```

## When to Load Full References

- `references/commands.md` - multi-line creation templates, advanced filtering (labels, priority, dates, pagination), sprint add/close, issue linking, complex JQL.
- `references/jql.md` - JQL syntax, operators, functions, relative dates, ordering.
- `references/follow-up.md` and `references/inline-images.md` are announced at their point of use above.

**Skip references** for simple view/list/assign operations - use quick reference above.

## Attachments

**Default for every provided screenshot or diagram:** inline ADF in the issue **description** on create and in the **comment** on follow-up - uploading a file and stopping is incomplete. Method selection (public URL, readable local `mediaSingle`, reuse existing attachment, quick thumbnail, repair) is the decision table in [`references/inline-images.md`](references/inline-images.md); it also carries the layout rules (`align-start`, width `100`, `widthType: percentage` - media dimensions alone still render at Jira's default 50% width) and the never-put-the-numeric-attachment-ID-in-a-`media`-node rule. The CLI `--image` path renders a centered 200 px thumbnail - not for ticket evidence.

## REST API Version Notes

| Endpoint | Use API Version | Notes |
|----------|----------------|-------|
| Description update (ADF) | **v3** | v2 returns "value must be a string" |
| Simple inline image comment | **v2** | String body supports existing-attachment markup |
| Structured inline image comment | **v3** | ADF requires the Media Services UUID, not the attachment ID |
| Attachment upload | **v2** | v3 returns "Issue does not exist" |
| Attachment metadata | v2 or v3 | Both work |
| Issue GET (view) | **v3** | May return 404 even when issue exists - see Known API Issues |
| Issue PUT (update) | **v3** | Works reliably with basic auth |
| JQL search | **v3** `/search/jql` | Old `/search` endpoint returns 410 (deprecated) |

## Known API Issues

- **GET `/rest/api/3/issue/KEY` returns 404 but PUT works (204):** Jira Cloud permission quirk. If GET fails, verify issue exists via JQL search (`/rest/api/3/search/jql?jql=key=KEY`), then proceed directly with PUT.
- **`/rest/api/3/search` deprecated (410):** Must use `/rest/api/3/search/jql` endpoint instead.
- **`/rest/api/2/myself` returns 401:** May be deprecated on some instances. Skip identity verification - if JQL search works, auth is valid.
- **`JIRA_BASE_URL` is unset:** Export the base URL from the selected local rules file.

## Known CLI Issues

- Upstream/Homebrew `jira-cli` builds do not support `--image`; if the check at the top of this skill prints nothing, reinstall the `vanducng/jira-cli` fork
- The fork's `--image` output is a centered 200 px ADF thumbnail; use the structured ADF workflow for readable screenshots and diagrams
- `jira project list` may fail with shell escaping errors - use `jira issue list` or REST API instead
- `jira me` and `jira issue create/view` work reliably
- `jira issue create` can still hang despite `--no-input` when combining a large `-b"$(cat file)"` body with `-a`/`-P` flags in one call (observed: hung the full 10min timeout). Wrap in `timeout 60 jira issue create ...`; if it times out, create the issue via REST API (`POST /rest/api/3/issue`) instead
- Config location: `$HOME/.config/.jira/.config.yml`

## Error Handling

- Auth errors → run `jira init` to reconfigure
- "transition not available" → check available transitions with `jira issue view`
- Field validation → check project issue types with `jira project list`
- `ATTACHMENT_VALIDATION_ERROR` → use the compact CLI thumbnail fallback or resolve the Media Services UUID per `references/inline-images.md`
- `jira project list` shell errors → use the REST API, or fall back to the project key from the loaded rules file
