---
name: jira
description: "Manage Jira issues via CLI. View, create, update, transition, assign, comment, sprint ops. Use when user mentions issue keys (PROJ-123), tickets, sprints, or keywords like jira/ticket/backlog."
license: MIT
argument-hint: "[ISSUE-KEY|search query|command]"
metadata:
  version: "1.0.0"
---

# Jira Integration (CLI Backend)

Uses `jira` CLI (ankitpokhrel/jira-cli). Backend confirmed available at `/opt/homebrew/bin/jira`.

## Defaults

- **Default board:** ELT Board
- **Token source:** `~/.envrc` — source it before any jira command

## Authentication (MANDATORY — run FIRST)

Tokens are stored in `~/.envrc`. **Before any Jira operation**, ask the user which project and export the correct token:

| Project | Token env var | Email env var | Atlassian instance |
|---------|--------------|---------------|--------------------|
| CNB | `JIRA_CNB_API_TOKEN` | `JIRA_CNB_USER_EMAIL` | teamcnb.atlassian.net |
| ABS | `JIRA_ABS_API_TOKEN` | `JIRA_ABS_USER_EMAIL` | abspectrum.atlassian.net |

**Workflow:**
1. Infer project from issue key prefix (ELT → CNB). Only ask if ambiguous.
2. Source `~/.envrc` and export the chosen token + email + base URL. **IMPORTANT: Always hardcode base URL, do NOT rely on `$JIRA_BASE_URL` env var (it's unset).**
```bash
# For CNB:
source ~/.envrc && export JIRA_API_TOKEN="${JIRA_CNB_API_TOKEN}" && export JIRA_USER_EMAIL="${JIRA_CNB_USER_EMAIL}" && export JIRA_BASE_URL="https://teamcnb.atlassian.net"
# For ABS:
source ~/.envrc && export JIRA_API_TOKEN="${JIRA_ABS_API_TOKEN}" && export JIRA_USER_EMAIL="${JIRA_ABS_USER_EMAIL}" && export JIRA_BASE_URL="https://abspectrum.atlassian.net"
```
3. Prepend `source ~/.envrc && export JIRA_API_TOKEN=...` to ALL subsequent jira CLI and curl commands in the session.

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

**CRITICAL — Underscore escaping bug:** The `jira` CLI escapes `_` to `\_` in descriptions, breaking code blocks. After creating/editing an issue with code snippets or underscored identifiers, ALWAYS update the description via REST API:
```bash
curl -s -X PUT "${JIRA_BASE_URL}/rest/api/3/issue/<KEY>" \
  -u "${JIRA_USER_EMAIL}:${JIRA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @/tmp/jira_update.json
```
Use Atlassian Document Format (ADF) with `codeBlock` node for code. See memory file `jira-workflow.md` for full ADF template.

### Modify
```bash
jira issue move ISSUE-KEY "In Progress"      # Transition
jira issue assign ISSUE-KEY $(jira me)       # Assign to self
jira issue comment add ISSUE-KEY -b"Comment" # Add comment
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
1. Fetch current state    → jira issue view ISSUE-KEY
2. Show proposed change   → Display to user
3. Get user approval      → AskUserQuestion
4. Execute command        → Run jira CLI
5. Verify result          → jira issue view ISSUE-KEY
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
- **`JIRA_BASE_URL` env var is NOT set in `~/.envrc`:** Always hardcode the URL (`https://teamcnb.atlassian.net` for CNB, `https://abspectrum.atlassian.net` for ABS).

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
