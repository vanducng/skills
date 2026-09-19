---
name: onepassword
description: "Operate 1Password CLI (`op`) for desktop-app or service-account auth, vault/item discovery, secret references (`op://…`), `op read` / `op run` / `op inject`, TOTP, and shell-plugin auth - without printing secrets into chat. Use when the user mentions 1Password, `op`, secret references, `op://`, biometric CLI unlock, or loading env/config from 1Password. Prefer `vd:gopass` only for the local gopass store."
license: MIT
argument-hint: "[whoami | read <ref> | run -- <cmd> | inject | item | vault | signin]"
metadata:
  author: vanducng
  version: "1.0.0"
  upstream: "https://developer.1password.com/docs/cli/"
---

# 1Password CLI (`op`)

Provision secrets from 1Password at runtime via the official CLI. Prefer **secret references** and subprocess injection over copying plaintext into the shell or chat.

Authoritative docs: [Get started](https://developer.1password.com/docs/cli/get-started/), [Secret references](https://developer.1password.com/docs/cli/secret-references/), [CLI reference](https://developer.1password.com/docs/cli/reference/).

## Scope

| Need | Owner |
| --- | --- |
| 1Password vaults / `op://` references / `op run` | `vd:onepassword` |
| Local gopass + GPG store | `vd:gopass` |
| Generic "get me a secret" with no store named | Ask which store; default to whichever the user already uses in this repo |

## Prerequisites

1. `op` on `PATH` (`brew install 1password-cli` on macOS; see official get-started for Windows/Linux).
2. Auth mode (detect in order):
   - **Service account:** `OP_SERVICE_ACCOUNT_TOKEN` is set (CI / headless).
   - **Desktop app integration:** 1Password app unlocked with Developer → Integrate with 1Password CLI (Touch ID / Windows Hello / system auth).
   - **Interactive `op signin`:** only when neither of the above works; session tokens are shell-local.

Verify before any secret read:

```bash
op --version
op whoami
```

If `whoami` fails with desktop-app connection errors: unlock the app, confirm CLI integration, retry. Do not invent install flags - follow the get-started page for this OS.

Multiple accounts: `--account <shorthand|url|id>` or `OP_ACCOUNT`.

## Secret references

```text
op://<vault>/<item>/[section/]<field>
```

Resolve with `op read`, `op run`, or `op inject` - never paste the plaintext into repo files.

Discover a reference without printing the secret value itself when possible:

```bash
op item get "<item>" --format json --fields password | jq -r .reference
op item get "<item>" --format json | jq -r '.fields[]? | select(.reference) | "\(.label): \(.reference)"'
```

## Core workflows

### Find and read

```bash
op vault list
op item list --vault "<vault>"
op item get "<item>" --vault "<vault>"          # metadata; avoid dumping all fields in chat
op read "op://<vault>/<item>/password"          # stdout - do not restate in chat
op read -n "op://<vault>/<item>/password"       # no trailing newline (for pipes)
op read "op://<vault>/<item>/one-time password?attribute=otp"
```

Capture into a consumer without echoing:

```bash
export API_KEY="$(op read -n "op://Work/My App/credential")"
```

### Run a process with secrets (`op run`)

Preferred for apps and scripts. Put references in the environment or an env file, then wrap the command:

```bash
export DB_USER="op://app-dev/db/username"
export DB_PASSWORD="op://app-dev/db/password"
op run -- <command>

op run --env-file="./.env" -- <command>
```

Stdout/stderr that would print secrets is masked by default. Use `--no-masking` only when the user explicitly needs the raw value on screen.

Shell expansion hazard: `$VAR` expands before `op run` unless the expanding command runs in a subshell after substitution:

```bash
MY_VAR=op://vault/item/field op run --no-masking -- sh -c 'echo "$MY_VAR"'
```

### Inject into config templates (`op inject`)

Templates with `op://` refs can live in git. Resolve at runtime:

```bash
op inject -i config.yml.tpl -o config.yml
```

Delete or gitignore resolved output files that contain plaintext.

### Write / rotate (explicit user ask only)

```bash
op item create --category=login --title="<title>" --vault="<vault>" \
  --url="<url>" "username=<user>" "password=<prompt interactively>"
op item edit "<item>" "password[password]=<new>"   # prefer interactive / generated flows
op item delete "<item>"
```

Do not pass secrets as argv in chat-visible command lines when an interactive or file-based flow exists.

## Shell plugins

`op plugin` can authenticate third-party CLIs via 1Password. Follow [shell plugins](https://developer.1password.com/docs/cli/shell-plugins/) when the user asks to wire a specific CLI; do not enable plugins globally without confirmation.

## Safety rules

- **Never** paste decrypted secrets into chat, commits, tickets, or logs. Confirm by vault/item/field or reference URI only.
- Prefer `op run` / `op inject` over writing plaintext `.env` files. If the user requires a resolved file, confirm it is gitignored first.
- Prefer service accounts with least-privilege vault access for automation.
- Do not wrap desktop-app-integrated `op` in nested multiplexers that break the app IPC (common failure: isolated sessions that cannot reach the desktop helper).
- Never commit `OP_SERVICE_ACCOUNT_TOKEN` or session tokens.

## Failure modes

| Symptom | Fix |
| --- | --- |
| `not currently signed in` / no session token | Unlock app + CLI integration, or `op signin`, or set `OP_SERVICE_ACCOUNT_TOKEN` |
| `couldn't connect to the 1Password desktop app` | Start/unlock app; Developer → Integrate with 1Password CLI; retry in the same user session |
| `op://` resolve errors | Check vault/item/field names; `op item get` + `jq .reference` |
| Secret printed as `<concealed by 1Password>` | Expected under `op run`; add `--no-masking` only if the user needs raw output |
| Wrong account | `op account list`; pass `--account` or `OP_ACCOUNT` |

## References

- https://developer.1password.com/docs/cli/get-started/
- https://developer.1password.com/docs/cli/secret-references/
- https://developer.1password.com/docs/cli/secret-reference-syntax/
- https://developer.1password.com/docs/cli/reference/commands/read/
- https://developer.1password.com/docs/cli/reference/commands/run/
- https://developer.1password.com/docs/cli/reference/commands/inject/
