---
name: gws
description: "Manage Google Workspace from the CLI: Gmail, Drive, Calendar, Sheets, Docs, Slides, Tasks, Chat, and audit reports via the official `gws` command, with multi-account support through per-account config dirs. Use when the user mentions gmail, drive, calendar, sheets, docs, workspace, gws, email, files, events, or names a configured account alias."
license: MIT
argument-hint: "[account-alias] [service] [resource] [method] [flags] | auth | gmail | drive | calendar | sheets"
metadata:
  author: vanducng
  version: "2.0.0"
  upstream: "https://github.com/googleworkspace/cli"
---

# gws

Google Workspace operations through the official `gws` CLI. This is the local safety wrapper and workflow guide; use the CLI for execution and load references only for multi-step recipes.

## Multi-Account Model

Upstream removed native multi-account support in v0.7.0 (`--account`, `gws auth list`, `GOOGLE_WORKSPACE_CLI_ACCOUNT` no longer exist - do not use them). Accounts are isolated by config directory instead:

- Account registry: `~/.config/vd/gws-accounts/<alias>.gws-account.md` - one file per account declaring email, domain, timezone, and its config dir. See `references/account.gws-account.example.md`.
- Credentials: one dir per account under `~/.config/vd/gws/<alias>/`, selected via `GOOGLE_WORKSPACE_CLI_CONFIG_DIR`.
- The default `~/.config/gws` holds no credentials by design: a bare `gws` call fails with exit code 2 instead of silently using an ambiguous account.

Every command is prefixed with the account's config dir:

```bash
GOOGLE_WORKSPACE_CLI_CONFIG_DIR="$HOME/.config/vd/gws/<alias>" gws <service> ...
```

### Account resolution

1. List configured aliases: `ls ~/.config/vd/gws-accounts/` and read the file for the chosen alias.
2. If the user named an account (alias or email), use it.
3. For reads where context makes the account obvious (work domain vs personal), pick it and state which account you used.
4. For writes, or when ambiguous: ask which account, or echo the chosen account and get confirmation.
5. Before any mutating operation, verify the live identity matches the intended account:

```bash
GOOGLE_WORKSPACE_CLI_CONFIG_DIR="$HOME/.config/vd/gws/<alias>" \
  gws gmail users getProfile --params '{"userId":"me"}' | jq -r '.emailAddress'
```

Silent wrong-account operation is the known failure mode of this CLI (upstream issue #439); the identity check is mandatory before sends, deletes, shares, and permission changes.

## Preflight

```bash
command -v gws && gws --version
ls ~/.config/vd/gws-accounts/
GOOGLE_WORKSPACE_CLI_CONFIG_DIR="$HOME/.config/vd/gws/<alias>" gws auth status
```

`auth status` must show `token_valid: true` (or at least `has_refresh_token: true`). If `gws` is missing: `brew install googleworkspace-cli`.

### Adding an account

```bash
mkdir -p ~/.config/vd/gws/<alias>
cp <existing-alias-dir>/client_secret.json ~/.config/vd/gws/<alias>/   # OAuth client is shared
GOOGLE_WORKSPACE_CLI_CONFIG_DIR="$HOME/.config/vd/gws/<alias>" gws auth login
```

The login opens a browser; the user picks the Google account there (the user must run this themselves - suggest the `! <command>` prompt prefix). Then create `~/.config/vd/gws-accounts/<alias>.gws-account.md` from the example and verify with the `getProfile` identity check. Scope selection: `--readonly`, or `-s gmail,drive,calendar` to limit services; explain any new scopes before asking the user to re-authenticate.

Service accounts are not a login-free alternative: gws cannot impersonate a user (no `--subject`; upstream #632/#776), so a service account sees no Gmail and an empty Drive. Refresh tokens make login a one-time event per account - if re-auth is demanded weekly, the GCP project's OAuth consent screen is likely in Testing status (publish it), or the Workspace org enforces a session-length policy.

## Safety Protocol

1. **Read before write:** run `list`/`get` first and summarize the target.
2. **Verify identity before mutating** (see account resolution above).
3. **Confirm destructive operations:** never delete, transfer ownership, remove permissions, or bulk-mutate without explicit user approval.
4. **Verify after write:** re-run `get`/`list` and report the changed state.
5. **No mass mail:** block sends above 10 recipients unless the user explicitly reconfirms.
6. **Prefer reversible actions:** archive over delete, reader over writer shares.
7. **Do not print secrets:** never echo OAuth values or tokens; `gws auth export` output must not appear in chat.

## Command Pattern

```bash
GWS="GOOGLE_WORKSPACE_CLI_CONFIG_DIR=$HOME/.config/vd/gws/<alias>"   # conceptual; write the env inline per command

# Raw API call
gws <service> <resource> [sub-resource] <method> --params '{...}' --json '{...}'

# Helper verbs (per-service, discover with: gws <service> --help)
gws gmail +send|+triage|+reply|+reply-all|+forward|+read
gws calendar +agenda|+insert
gws drive +upload
gws sheets +append|+read

# Schema discovery
gws schema <service>.<resource>.<method>
```

Response shape is JSON; pipe to `jq`. Use `--page-all` for pagination, `--dry-run` to validate locally.

## Quick Reference

All commands below need the `GOOGLE_WORKSPACE_CLI_CONFIG_DIR` prefix; omitted for brevity.

### Gmail (note: resource path is `users messages`, `userId` required)

```bash
gws gmail users messages list --params '{"userId":"me","maxResults":10,"q":"is:unread"}'
gws gmail users messages get --params '{"userId":"me","id":"<MSG_ID>","format":"metadata","metadataHeaders":["From","Subject","Date"]}'
gws gmail +triage
gws gmail +send --to alice@example.com --subject "Hi" --body "..."
gws gmail +reply --help   # threading handled automatically
```

### Drive

```bash
gws drive files list --params '{"pageSize":20,"q":"trashed=false"}'
gws drive files get --params '{"fileId":"<ID>"}'
gws drive +upload --help
gws drive files get --params '{"fileId":"<ID>","alt":"media"}' --output ./file.pdf
gws drive permissions create --params '{"fileId":"<ID>"}' --json '{"role":"reader","type":"user","emailAddress":"x@y.com"}'
```

### Calendar

```bash
gws calendar +agenda
gws calendar calendarList list
gws calendar events insert --params '{"calendarId":"primary"}' --json '{"summary":"Team Sync","start":{"dateTime":"2026-05-28T14:00:00+07:00"},"end":{"dateTime":"2026-05-28T15:00:00+07:00"}}'
```

### Sheets / Docs

```bash
gws sheets spreadsheets create --json '{"properties":{"title":"Q2 Budget"}}'
gws sheets spreadsheets values get --params '{"spreadsheetId":"<ID>","range":"Sheet1!A:Z"}'
gws sheets +append --help
gws docs documents create --json '{"title":"Notes"}'
gws docs documents get --params '{"documentId":"<ID>"}'
```

### Audit reports (admin-reports)

```bash
gws reports activities list --params '{"userKey":"all","applicationName":"login","maxResults":50}'
```

**Not available:** Admin SDK Directory (users/groups/domains management) is not exposed by gws 0.22.5. For Workspace user/group administration use the Admin console or GAM7; do not fabricate `gws admin ...` commands.

## Workflow

Reads: confirm account → narrowest list/get → summarize relevant JSON fields, stating which account served the data.

Writes: read current state → identity check → show account + object id + proposed mutation → approval for destructive/high-impact → execute → verify with get/list.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Exit code 2 / `auth_method: none` | No credentials in the selected config dir | Wrong alias, or run the login for that dir |
| `invalid_rapt` / `invalid_grant` | Refresh token expired (consent screen in Testing, or org session policy) | Re-login for that dir; publish the OAuth app to stop weekly expiry |
| `403 insufficientPermissions` | Scope not granted | Re-login with the needed `-s` services |
| `accessNotConfigured` | API disabled in the GCP project | Enable it in Google Cloud Console |
| Unknown service `admin` | Directory API not in gws | Use Admin console or GAM7 |
| `unrecognized subcommand`/`--account` errors | Command from removed multi-account era | Use `GOOGLE_WORKSPACE_CLI_CONFIG_DIR` per this skill |
| Wrong account answered | Config dir mismatch | Run the `getProfile` identity check; fix the alias mapping |

## References

- `references/recipes.md` - multi-step Gmail, Drive, Calendar, and Sheets workflows
- `references/account.gws-account.example.md` - template for a new account registry file
- Official CLI: https://github.com/googleworkspace/cli
