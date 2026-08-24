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

## Scope

Handles Jira issue lookup, creation, updates, transitions, assignment, comments, and sprint operations. Does not manage non-Jira work trackers or expose credentials and private company conventions.

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
- Attach the provided screenshot or evidence when available.
- Omit implementation details, proposed code, and speculative analysis unless requested.
- Apply assignee, sprint, parent, and initial status from the matching local type rules.

## Instance Rules (MANDATORY - load before writes)

After selecting the Jira instance, read its rules before drafting or executing any write:

```text
~/.config/vd/jira-rules/<instance>.jira-rules.md
```

Use `cnb.jira-rules.md` for CNB and `abs.jira-rules.md` for ABS. These rules are authoritative for issue-type mapping, assignee, sprint, parent, initial status, and ticket content. Resolve dynamic values such as `me`, the current active sprint, and transition IDs from Jira before showing the proposed payload.

If the requested type is not a native Jira issue type, use the rule's Jira type and labels. Explicit user instructions override the rule file; state the override. If no rule file exists, continue with the base safety protocol and tell the user that no instance defaults were applied.

## Activation Triggers

Activate when user mentions:
- Issue keys (e.g., ELT-123, PROJ-45)
- Keywords: jira, ticket, issue, sprint, backlog, board, epic
- Actions: create ticket, move to done, assign, check status

## Safety Protocol (MANDATORY)

1. **Read before write** - always fetch current state before modifications
2. **Show before execute** - display proposed changes, get approval for writes
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

**Multi-line descriptions:** Write to `/tmp` first, then use `-b"$(cat /tmp/jira_body.md)"`.

**Structured descriptions:** Use REST API with Atlassian Document Format (ADF), not CLI `-b`, when headings/lists need to render cleanly. Paragraphs containing `- item` render as plain text; native `heading` and `bulletList` nodes render correctly.

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

Read [`references/follow-up.md`](references/follow-up.md) before posting an evidence update with JSON/code or native mentions, or when the user names a board column such as review, QA, or staging instead of an exact workflow status.

- Use REST v3 ADF for native bullets, `codeBlock`, and `mention`; plain `@Display Name` does not prove the user was mentioned.
- Resolve board column to status IDs, then status ID to an available issue transition. Never assume the column label is the status name.
- Show the resolved comment and column/status/transition mapping before writing, then re-read the stored ADF and resulting issue status.

### REST ADF Description Pattern
Use this for clean Jira descriptions with sections and bullets:
```bash
payload=$(jq -n '{
  fields: {
    description: {
      type: "doc",
      version: 1,
      content: [
        {type: "heading", attrs: {level: 3}, content: [{type: "text", text: "Goal"}]},
        {type: "paragraph", content: [{type: "text", text: "Make staging and production consistent."}]},
        {type: "heading", attrs: {level: 3}, content: [{type: "text", text: "Scope"}]},
        {type: "bulletList", content: [
          {type: "listItem", content: [{type: "paragraph", content: [{type: "text", text: "Add production deploy path."}]}]}
        ]}
      ]
    }
  }
}')
curl -sS -X PUT "${JIRA_BASE_URL}/rest/api/3/issue/<KEY>" \
  -u "${JIRA_USER_EMAIL}:${JIRA_API_TOKEN}" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d "$payload" \
  -w "\nHTTP %{http_code}\n"
```

### Other
```bash
jira me                                      # Current user
jira open ISSUE-KEY                          # Open in browser
jira project list                            # List projects
jira board list                              # List boards
```

## When to Load Full References

Load `references/commands.md` for:
- Multi-line issue creation with templates
- Advanced filtering (labels, priority, date ranges, pagination)
- Sprint management (add to sprint, close sprint)
- Issue linking
- Complex JQL queries

Load `references/jql.md` for:
- JQL syntax, operators, functions
- Relative dates, ordering
- Complex query examples

Load `references/follow-up.md` for:
- Evidence-based completion or release updates
- Structured comments with JSON/code blocks or native mentions
- Reporter mentions
- Requests expressed as board columns rather than workflow statuses

Load `references/inline-images.md` for:
- Rendering remote or locally uploaded images inside comments
- Choosing filename markup or ADF `mediaSingle`
- Verifying that the stored comment contains the image

**Skip references** for simple view/list/assign operations - use quick reference above.

## Workflow: Write Operations

```
1. Load instance rules    → ~/.config/vd/jira-rules/<instance>.jira-rules.md
2. Fetch current state    → issue, active sprint, parent, transitions
3. Show proposed change   → Include every rule-derived field
4. Get user approval      → AskUserQuestion (Claude Code; plain-text question elsewhere)
5. Execute command        → Run jira CLI or REST API
6. Verify result          → Re-read every changed field
```

## Attachments

### Inline local image

For screenshots or diagrams that users must read inline, use a REST v3 ADF `mediaSingle` node by default. Set `layout` to `align-start`, cap the display width at 1200 px, and preserve the source aspect ratio. The CLI `--image` path renders a centered 200 px thumbnail, so reserve it for quick attachment evidence where inline readability is not important.

```bash
jira issue comment add ISSUE-KEY "Quick evidence" --image /path/to/flow.png
```

### Inline images in comments

- **Public URL:** Pass Markdown image syntax in the comment body.
- **Readable local image:** Upload the attachment, resolve its Media Services UUID, then create a REST v3 ADF comment with left-aligned media sized from the source image. This is the default.
- **Quick local thumbnail:** Pass one or more `--image` paths when a small preview is acceptable.
- **Existing small image:** Update the comment ADF in place instead of uploading a duplicate attachment.

Never put the numeric attachment ID in an ADF `media` node; it causes `ATTACHMENT_VALIDATION_ERROR`. Never call Jira's private Media API. See [`references/inline-images.md`](references/inline-images.md) for creation, repair, and verification commands.

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

- Upstream/Homebrew `jira-cli` 1.7.0 does not support `--image`; confirm PATH resolves the `vanducng/jira-cli` build
- The fork's `--image` output is a centered 200 px ADF thumbnail; use the structured ADF workflow for readable screenshots and diagrams
- `jira project list` may fail with shell escaping errors - use `jira issue list` or REST API instead
- `jira me` and `jira issue create/view` work reliably
- `jira issue create` can still hang despite `--no-input` when combining a large `-b"$(cat file)"` body with `-a`/`-P` flags in one call (observed: hung the full 10min timeout). Wrap in `timeout 60 jira issue create ...`; if it times out, create the issue via REST API (`POST /rest/api/3/issue`) instead
- Config location: `$HOME/.config/.jira/.config.yml`

## Error Handling

- Auth errors → run `jira init` to reconfigure
- "transition not available" → check available transitions with `jira issue view`
- Field validation → check project issue types with `jira project list`
- `ATTACHMENT_VALIDATION_ERROR` → use v2 filename markup or resolve the Media Services UUID per `references/inline-images.md`
- `jira project list` shell errors → use REST API or skip, project is ELT by default
