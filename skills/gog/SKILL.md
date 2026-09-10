---
name: gog
description: "Manage Google Workspace from the CLI via `gog`: Gmail, Drive, Calendar, Sheets, Docs, Chat, Tasks, and Admin. Invoke with --account cnb|dpl|abs and --user person|sa. Use when the user mentions gmail, drive, calendar, sheets, docs, workspace, gws, gog, email, files, events, or a configured account."
license: MIT
argument-hint: "--account cnb|dpl|abs --user person|sa gmail|drive|calendar|sheets|docs|auth"
metadata:
  author: vanducng
  version: "1.1.0"
  upstream: "https://github.com/openclaw/gogcli"
---

# gog

Google Workspace through `gog`. This skill is the local account map and safety
wrapper. Discover flags from the binary (`gog schema`, `gog <svc> --help`).

Every invocation:

```bash
export GOG_HOME="${GOG_HOME:-$HOME/.config/vd/gog}"
# source "$GOG_HOME/env" if present
```

Never run a bare `gog` without `GOG_HOME`. Tokens then land in `~/.config/gogcli`
and this skill cannot see them.

## Flags (prompt / skill args)

```
vd:gog --account <cnb|dpl|abs> --user <person|sa> <gmail|drive|calendar|sheets|docs|auth> ...
```

| Flag | Values | Default |
|---|---|---|
| `--account` | `cnb`, `dpl`, `abs` | none; required on writes, ask if missing |
| `--user` | `person` (human mailbox, refresh token), `sa` (service account key) | `person` |

Resolve to a `gog` CLI identity:

| --account | --user | Registry file | `gog --account` |
|---|---|---|---|
| `cnb` | `person` | `cnb.user.md` | `cnb` |
| `cnb` | `sa` | `cnb.sa.md` | `cnb-sa` |
| `dpl` | `person` | `dpl.user.md` | `dpl` |
| `dpl` | `sa` | `dpl.sa.md` | `dpl-sa` |
| `abs` | `person` | `abs.user.md` | `abs` |
| `abs` | `sa` | `abs.sa.md` | `abs-sa` |

Read `$HOME/.config/vd/gog-accounts/<account>.<user|sa>.md` before the first call.
If that file is missing, stop and say so. Do not invent an email.

`--user person` is the Gmail/Calendar/Sheets-as-you path. `--user sa` is only
for Drive/Sheets already shared with that key. Never send mail as `--user sa`.

## Person-user auth (max lifetime)

`--user person` must use a **refresh token**, not a one-hour access token.
Google will not issue a longer access token.

Hard rules for person users:

1. Never `--access-token`, `GOG_ACCESS_TOKEN`, or `GOG_AUTH_MODE=adc`.
2. Before work: `gog --account <alias> auth list --check --json --no-input` must
   show `auth: oauth` and `valid: true`.
3. Login always requests a refresh token:

```bash
export GOG_HOME="$HOME/.config/vd/gog"
gog --client <client> auth add <email> \
  --services gmail,calendar,drive,docs,sheets,tasks,people,chat \
  --force-consent
```

`--force-consent` is required so Google returns a refresh token. Use the window
`gog` opens. Do not paste a wrapped URL from the terminal (`response_type` errors).

4. The OAuth app must **not** be in Testing. Testing refresh tokens die in 7 days.
   Consent screen → **In production** (Internal Workspace app, or External published
   without verification). If login is demanded weekly, stop and publish; do not
   keep re-authing.
5. Re-auth the same way when `invalid_grant` / `invalid_rapt` appears. Identity
   must match the registry email (`gog --account <resolved> me --json`).

`--user sa` does not use this path. The key does not expire on a 7-day clock;
do not impersonate a person unless Domain-Wide Delegation is on.

Named OAuth clients: `cnb` + `person` → `gog --client cnb`; `dpl` + `person` → default.

```bash
# vd:gog --account cnb --user person ...
gog --account cnb me --json --no-input
```

## Preflight

```bash
export GOG_HOME="$HOME/.config/vd/gog"
command -v gog && gog --version    # expect >= 0.39.1
ls "$HOME/.config/vd/gog-accounts/"*.md
gog --account <resolved> auth list --check --json --no-input
```

Missing binary: `brew tap openclaw/tap && brew install gogcli`.

## Safety

1. `--readonly` on reads. `--gmail-no-send` unless sending is the task.
2. `--dry-run` before supported writes. Destructive commands need `--force` only
   when the user asked for that mutation.
3. No mass mail (>10 recipients) without a second confirmation.
4. Archive over delete; reader over writer shares.
5. Do not print OAuth client secrets, refresh tokens, or SA JSON.

## Commands

```bash
gog --readonly --account <a> --gmail-no-send gmail search 'is:unread newer_than:1d' --max 10 --json --wrap-untrusted
gog --account <a> gmail send --to someone@example.com --subject "Hi" --body "..."
gog --account <a> gmail reply <messageId> --body-file reply.txt

gog --readonly --account <a> calendar events --today --json --wrap-untrusted
gog --readonly --account <a> drive ls --max 20 --json
gog --account <a> drive upload ./file --parent <folderId> --json

gog --readonly --account <a> sheets get <sid> 'Sheet1!A1:F60' --render FORMULA --json
gog --account <a> sheets insert <sid> <tab> ROWS <start> --count N
gog --account <a> sheets copy-paste <sid> <src> <dst> --type FORMAT
gog --account <a> sheets update <sid> 'Tab!A11:F49' --values-json @file.json

gog schema gmail search --json
gog api call sheets v4 spreadsheets.batchUpdate --help
```

Long tail: `gog api call <api> <version> <method>` and `gog <service> raw`.
Admin Directory: `gog admin` needs a Workspace SA with domain-wide delegation,
not person-user OAuth.

## Workflow

Reads: resolve alias → `--readonly` list/get → summarize, naming the account.

Writes: read current state → `gog --account <a> me` → show account + id + mutation
→ approval for destructive work → execute → verify with get/list.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Token missing after a successful browser login | `gog` ran without `GOG_HOME` | Always export `GOG_HOME=$HOME/.config/vd/gog` |
| Re-auth every 7 days | OAuth consent screen in Testing | Publish to In production, then `auth add --force-consent` once |
| `authorized as A, expected B` | Wrong Google account in the chooser | Retry; pick the alias email |
| `access_not_configured` / admin must review | Workspace blocks the OAuth client | Internal app in that org, or admin allowlists the client ID |
| `response_type` missing | Truncated auth URL | Use the window `gog` opens; do not paste a wrapped URL |
| Gmail empty on `--user sa` | SA has no mailbox | Use `--user person`; DWD is a separate admin step |
| `invalid_grant` / `invalid_rapt` | Refresh token revoked or expired | Person-user re-add with `--force-consent` |

## References

- `references/recipes.md`
- `references/account.gog-account.example.md`
- CLI: https://github.com/openclaw/gogcli
