---
name: jira
description: "Manage Jira issues via CLI. View, create, update, transition, assign, comment, sprint ops. Use when user mentions issue keys (PROJ-123), tickets, sprints, or keywords like jira/ticket/backlog."
license: MIT
argument-hint: "[--project ALIAS] [--type bug|task] [ISSUE-KEY|request]"
metadata:
  version: "1.1.0"
---

# Jira Integration (CLI Backend)

Uses `jira` CLI (ankitpokhrel/jira-cli). Backend confirmed available at `/opt/homebrew/bin/jira`.

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

## Authentication (MANDATORY — run FIRST)

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

## Instance Rules (MANDATORY — load before writes)

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

1. **Read before write** — always fetch current state before modifications
2. **Show before execute** — display proposed changes, get approval for writes
3. **Verify after execute** — confirm the operation succeeded
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

**CRITICAL — Underscore escaping bug:** The `jira` CLI escapes `_` to `\_` in descriptions, breaking code blocks. After creating/editing an issue with code snippets or underscored identifiers, ALWAYS update the description via REST API:
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
jira issue comment add ISSUE-KEY -b"Comment" # Add comment
jira sprint add SPRINT-ID ISSUE-KEY          # Add to active/known sprint
jira issue link ISSUE-1 ISSUE-2 Relates      # Link issues
```

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

**Skip references** for simple view/list/assign operations — use quick reference above.

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

### Upload attachment
Use REST API **v2** (v3 returns permission errors for attachments):
```bash
curl -s -X POST "${JIRA_BASE_URL}/rest/api/2/issue/<KEY>/attachments" \
  -u "${JIRA_USER_EMAIL}:${JIRA_API_TOKEN}" \
  -H "X-Atlassian-Token: no-check" \
  -F "file=@/path/to/file.png;filename=descriptive-name.png"
```

### Inline images in description — NOT POSSIBLE via API
Jira Cloud ADF `media` nodes require internal media service UUIDs (not attachment numeric IDs). These UUIDs are only generated through Jira's internal media service and are **not exposed via the public REST API**. Workarounds tried and failed:
- Wiki markup `!filename!` → renders as literal text (ADF doesn't support wiki markup)
- ADF `mediaSingle`/`media` with attachment ID → `ATTACHMENT_VALIDATION_ERROR`
- ADF `media` with collection pattern → same error

**Best approach:** Upload as attachment + reference in description text: "See screenshot in attachments."

## REST API Version Notes

| Endpoint | Use API Version | Notes |
|----------|----------------|-------|
| Description update (ADF) | **v3** | v2 returns "value must be a string" |
| Attachment upload | **v2** | v3 returns "Issue does not exist" |
| Attachment metadata | v2 or v3 | Both work |
| Issue GET (view) | **v3** | May return 404 even when issue exists — see Known API Issues |
| Issue PUT (update) | **v3** | Works reliably with basic auth |
| JQL search | **v3** `/search/jql` | Old `/search` endpoint returns 410 (deprecated) |

## Known API Issues

- **GET `/rest/api/3/issue/KEY` returns 404 but PUT works (204):** Jira Cloud permission quirk. If GET fails, verify issue exists via JQL search (`/rest/api/3/search/jql?jql=key=KEY`), then proceed directly with PUT.
- **`/rest/api/3/search` deprecated (410):** Must use `/rest/api/3/search/jql` endpoint instead.
- **`/rest/api/2/myself` returns 401:** May be deprecated on some instances. Skip identity verification — if JQL search works, auth is valid.
- **`JIRA_BASE_URL` is unset:** Export the base URL from the selected local rules file.

## Known CLI Issues

- `jira project list` may fail with shell escaping errors — use `jira issue list` or REST API instead
- `jira me` and `jira issue create/view` work reliably
- Config location: `/Users/vanducng/.config/.jira/.config.yml`

## Error Handling

- Auth errors → run `jira init` to reconfigure
- "transition not available" → check available transitions with `jira issue view`
- Field validation → check project issue types with `jira project list`
- `ATTACHMENT_VALIDATION_ERROR` → don't try to embed images inline in ADF, use attachment reference instead
- `jira project list` shell errors → use REST API or skip, project is ELT by default
