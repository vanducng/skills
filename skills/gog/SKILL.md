---
name: gog
description: "Manage Google Workspace from the CLI via `gog`: Gmail, Drive, Calendar, Sheets, Docs, Chat, Tasks, and Admin. Invoke with --account <name> (any account in the local registry) and --user person|sa. Use when the user mentions gmail, drive, calendar, sheets, docs, workspace, gog, email, files, events, or a configured account."
license: MIT
argument-hint: "--account <name> --user person|sa gmail|drive|calendar|sheets|docs|auth"
metadata:
  author: vanducng
  version: "1.1.1"
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
vd:gog --account <name> --user <person|sa> <gmail|drive|calendar|sheets|docs|auth> ...
```

| Flag | Values | Default |
|---|---|---|
| `--account` | any name in `$HOME/.config/vd/gog-accounts/` | none; required on writes, ask if missing |
| `--user` | `person` (human mailbox, refresh token), `sa` (service account key) | `person` |

Discover the configured accounts, never assume them:

```bash
ls "$HOME/.config/vd/gog-accounts/"*.md   # <account>.user.md / <account>.sa.md
```

Resolve to a `gog` CLI identity: `--user person` → `gog --account <account>`,
`--user sa` → `gog --account <account>-sa`.

Read `$HOME/.config/vd/gog-accounts/<account>.<user|sa>.md` before the first call.
If that file is missing, stop and say so. Do not invent an email.

`--user person` is the Gmail/Calendar/Sheets-as-you path. `--user sa` is only
for Drive/Sheets already shared with that key. Never send mail as `--user sa`.

## Person-user auth (max lifetime)

`--user person` must use a **refresh token**, not a one-hour access token.
`gog` has no flag for token lifetime in days. Google sets the limits.

| Token | Lifetime | Who controls it |
|---|---|---|
| Access token | ~1 hour | Google. `gog` refreshes it automatically. Cannot be extended. |
| `auth add --timeout` | Login wait only (manual default 5m) | Local. How long the CLI waits for the browser, not how long the token lasts. |
| Refresh token, OAuth app in **Testing** | 7 days | Google Cloud consent screen. |
| Refresh token, OAuth app **In production** | No calendar expiry | Google's maximum. Can still die if unused 6 months, revoked, password change, or Workspace session policy. |

Maximum person-user lifetime is a refresh token from an **In production** OAuth app. Do not use `--access-token` to try to last longer.

Hard rules for person users:

1. Never `--access-token`, `GOG_ACCESS_TOKEN`, or `GOG_AUTH_MODE=adc`.
2. Before work: `gog --account <alias> --client <client> auth list --check --json --no-input` must show `auth: oauth` and `valid: true`.
3. After `auth add`, map the registry alias so `--account <alias>` resolves:
   `gog --client <client> auth alias set <alias> <email>`.
4. Login always requests a refresh token:

```bash
export GOG_HOME="$HOME/.config/vd/gog"
gog --client <client> auth add <email> \
  --services gmail,calendar,drive,docs,sheets,tasks,people,chat \
  --force-consent
```

`--force-consent` is required so Google returns a refresh token. Use the window
`gog` opens. Do not paste a wrapped URL from the terminal (`response_type` errors).
`--timeout` only bounds that browser wait.

5. The OAuth app must **not** be in Testing. Testing refresh tokens die in 7 days.
   Consent screen → **In production** (Internal Workspace app, or External published
   without verification). If login is demanded weekly, stop and publish; do not
   keep re-authing.
6. `invalid_rapt` is Workspace session control, not a 7-day Testing expiry. Re-auth
   interactively. Unattended jobs should use `--user sa`, not a person refresh token.
7. Identity must match the registry email (`gog --account <alias> --client <client> me --json`).

`--user sa` does not use this path. The key does not expire on a 7-day clock;
do not impersonate a person unless Domain-Wide Delegation is on.

Named OAuth clients: a registry entry may pin one (`gog --client <name>`); otherwise the default client applies.

```bash
# vd:gog --account acme --user person ...
gog --account acme --client acme me --json --no-input
```

## Preflight

```bash
export GOG_HOME="$HOME/.config/vd/gog"
command -v gog && gog --version    # expect >= 0.39.1
ls "$HOME/.config/vd/gog-accounts/"*.md
gog --account <resolved> --client <client> auth list --check --json --no-input
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

Discover flags from the binary - never guess them:

```bash
gog schema <svc> <cmd> --json      # exact flag/argument schema for a command
gog <svc> --help
gog api call sheets v4 spreadsheets.batchUpdate --help
```

Long tail: `gog api call <api> <version> <method>` and `gog <service> raw`.
Worked examples (inbox triage, agenda, send, sheet append, archive):
`references/recipes.md`. Admin Directory: `gog admin` needs a Workspace SA
with domain-wide delegation, not person-user OAuth.

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
| `invalid_grant` / `invalid_rapt` | Testing expiry, revocation, or Workspace session control | Person-user re-add with `--force-consent`. `invalid_rapt` is org session policy, not a CLI day-count |
| `No auth for drive <alias>` | Alias missing or token stored under the email | `gog --client <client> auth alias set <alias> <email>` |
| `people/me` 403 after a Drive-only login | Login used a service subset | Expected. Recheck with `drive ls` or re-add with the full `--services` list |

## References

- `references/recipes.md`
- `references/account.gog-account.example.md`
- CLI: https://github.com/openclaw/gogcli
