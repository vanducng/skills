---
name: gws
description: "Manage Google Workspace from the CLI: Gmail, Drive, Calendar, Sheets, Docs, Tasks, Chat, and Workspace Admin for vanducng.dev via the official `gws` command. Use when the user mentions gmail, drive, calendar, sheets, docs, workspace, gws, vanducng.dev, email, files, events, or Workspace users/groups."
license: MIT
argument-hint: "[service] [resource] [method] [flags] | auth | gmail | drive | calendar | sheets | admin"
metadata:
  author: vanducng
  version: "1.0.0"
  upstream: "https://github.com/googleworkspace/cli"
---

# gws

Google Workspace operations through the official `gws` CLI from `googleworkspace/cli`. This is the local safety wrapper and workflow guide; use the CLI for execution and load references only for multi-step recipes.

## Defaults

- **Primary account:** `me@vanducng.dev`
- **Primary domain:** `vanducng.dev`
- **Timezone:** `Asia/Ho_Chi_Minh`
- **CLI:** `gws`
- **Response shape:** JSON; pipe to `jq` for inspection and summaries

## When To Use

Use this skill when the user asks to:

- Read, search, send, reply to, label, or archive Gmail
- List, upload, download, share, move, or inspect Drive files
- Read agenda, create events, update events, or manage Calendar calendars
- Create, read, or append Google Sheets data
- Create or inspect Google Docs
- Manage Workspace users, groups, memberships, aliases, domains, or audit logs for `vanducng.dev`
- Run a raw Workspace API call through `gws`

Do not use this for Drive backup/sync work where `rclone` is a better fit, IMAP mailbox backups where `mbsync` or `gyb` is better, or high-volume Workspace provisioning where `GAM7` is more mature.

## Preflight

Before any Workspace operation:

```bash
command -v gws
gws --version
gws auth list
```

If `gws` is missing:

```bash
brew install googleworkspace-cli
# or
npm install -g @googleworkspace/cli
```

For first-time auth:

```bash
gws auth setup
gws auth login --account me@vanducng.dev
gws auth default --account me@vanducng.dev
```

For admin operations, verify scopes before writing:

```bash
gws auth login --account me@vanducng.dev -s admin.directory,admin.reports
```

Explain any new scopes before asking the user to re-authenticate.

## Account Rules

- Admin or `vanducng.dev` requests: always pass `--account me@vanducng.dev`.
- Read-only personal requests: use the default account if only one account is configured.
- Mutating personal requests: if multiple accounts are configured and the user did not name one, ask which account to use.
- Cross-account writes: echo the exact `--account` before executing.

Resolution without `--account` is:

1. `GWS_ACCOUNT`
2. `gws auth default`
3. CLI error

Prefer explicit `--account` on every mutating command.

## Safety Protocol

1. **Read before write:** run `list` or `get` first and summarize the target.
2. **Confirm destructive operations:** never delete, suspend, transfer ownership, reset passwords, remove group members, or bulk-mutate without explicit user approval.
3. **Verify after write:** re-run `get` or `list` and report the changed state.
4. **No mass mail:** block sends above 10 recipients unless the user explicitly reconfirms the batch.
5. **Admin caution:** double-check `primaryEmail`, `groupKey`, and `customer` before any Admin SDK write.
6. **Prefer reversible actions:** suspend before delete, archive before delete, share with reader before writer.
7. **Do not print secrets:** temporary passwords or OAuth values must not be echoed in chat or committed.

## Command Pattern

Raw API call:

```bash
gws <service> <resource> <method> --account <email> --params '{...}' --json '{...}'
```

Helper recipe:

```bash
gws <service> +<verb> --account <email> [flags]
```

Environment-pinned:

```bash
GWS_ACCOUNT=me@vanducng.dev gws <service> <resource> <method> --params '{...}'
```

## Quick Reference

### Gmail

```bash
gws gmail messages list --account me@vanducng.dev --params '{"maxResults":10,"q":"is:unread"}'
gws gmail messages get --account me@vanducng.dev --params '{"id":"<MSG_ID>","format":"metadata","metadataHeaders":["From","Subject","Date"]}'
gws gmail +send --account me@vanducng.dev --to alice@example.com --subject "Hi" --body "..."
gws gmail +reply --account me@vanducng.dev --thread-id <THREAD_ID> --body "..."
```

### Drive

```bash
gws drive files list --account me@vanducng.dev --params '{"pageSize":20,"q":"trashed=false"}'
gws drive files get --account me@vanducng.dev --params '{"fileId":"<ID>"}'
gws drive +upload --account me@vanducng.dev --local ./report.pdf --parent <FOLDER_ID>
gws drive +download --account me@vanducng.dev --file-id <ID> --out ./report.pdf
gws drive permissions create --account me@vanducng.dev --params '{"fileId":"<ID>"}' --json '{"role":"reader","type":"user","emailAddress":"x@y.com"}'
```

### Calendar

```bash
gws calendar calendars list --account me@vanducng.dev
gws calendar +agenda --account me@vanducng.dev --timezone Asia/Ho_Chi_Minh
gws calendar events insert --account me@vanducng.dev --params '{"calendarId":"primary"}' --json '{"summary":"Team Sync","start":{"dateTime":"2026-05-28T14:00:00+07:00"},"end":{"dateTime":"2026-05-28T15:00:00+07:00"}}'
```

### Sheets

```bash
gws sheets spreadsheets create --account me@vanducng.dev --json '{"properties":{"title":"Q2 Budget"}}'
gws sheets spreadsheets values get --account me@vanducng.dev --params '{"spreadsheetId":"<ID>","range":"Sheet1!A:Z"}'
gws sheets +append --account me@vanducng.dev --spreadsheet-id <ID> --range "Sheet1!A:Z" --values '[["a","b","c"]]'
```

### Docs

```bash
gws docs documents create --account me@vanducng.dev --json '{"title":"Notes"}'
gws docs documents get --account me@vanducng.dev --params '{"documentId":"<ID>"}'
```

### Admin

```bash
gws admin users list --account me@vanducng.dev --params '{"domain":"vanducng.dev","maxResults":50}'
gws admin users get --account me@vanducng.dev --params '{"userKey":"user@vanducng.dev"}'
gws admin groups list --account me@vanducng.dev --params '{"domain":"vanducng.dev"}'
gws admin members list --account me@vanducng.dev --params '{"groupKey":"team@vanducng.dev"}'
```

## Workflow

For reads:

```text
1. Confirm account and command scope
2. Run the narrowest list/get command
3. Summarize relevant JSON fields
```

For writes:

```text
1. Read current state
2. Show account, object id, and proposed mutation
3. Get approval for destructive or high-impact writes
4. Execute with explicit --account
5. Verify with get/list
```

For admin writes:

```text
1. Verify target user/group exists
2. Verify admin scopes are available
3. Prefer reversible operation
4. Ask for explicit confirmation
5. Execute and verify
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `403 insufficientPermissions` | Scope not granted | Re-login with the needed `-s` scope |
| `401 invalid_grant` | Token expired or revoked | `gws auth logout --account <email>` then `gws auth login --account <email>` |
| `accessNotConfigured` | API disabled in GCP project | Enable the API in Google Cloud Console |
| Admin call returns 403 | Missing admin scopes or non-admin account | Re-auth `me@vanducng.dev` with admin scopes |
| `command not found: gws` | CLI not installed or not on PATH | Install with Homebrew/npm and check `/opt/homebrew/bin` |
| Wrong account used | Default account mismatch | Run `gws auth list`; pass explicit `--account` or `GWS_ACCOUNT=...` |
| `account not found` | Account not logged in | `gws auth login --account <email>` |

## References

- `references/recipes.md` for common Gmail, Drive, Calendar, and Sheets workflows
- `references/admin-vanducng-dev.md` for Workspace Admin runbooks
- Official CLI: https://github.com/googleworkspace/cli
- CLI skills documentation: https://github.com/googleworkspace/cli/blob/main/docs/skills.md
