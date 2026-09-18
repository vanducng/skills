---
name: gopass
description: "Manage credentials in a local gopass store: find and retrieve secrets without exposing them, insert or generate values, rotate and remove entries, sync and diagnose the store, handle TOTP, and connect stored credentials to shell environment variables such as ~/.envrc. Use whenever a task needs a secret or asks to add, update, list, copy, export, or troubleshoot gopass credentials."
license: MIT
metadata:
  author: vanducng
  version: "1.1.0"
  upstream: "https://github.com/gopasspw/gopass"
---

# gopass

Local password store wrapped around GPG. Secrets live as encrypted files in a git repo and decrypt on demand. The user has it installed and initialized - commands "just work" on this machine.

## Core commands

### Read

```bash
gopass ls                         # tree view of all secrets
gopass find <keyword>             # search names (fast, no decrypt)
gopass grep <string>              # search inside decrypted content (slow)
gopass show <path>                # full content (password + key:value lines)
gopass show -o <path>             # password ONLY - use this to capture into vars
gopass -c <path>                  # copy password to clipboard, clears in 45s
```

Multi-line secrets store the password on line 1 and structured `key: value` pairs below. `gopass show <path> <key>` extracts a single field.

### Write

```bash
gopass insert <path>              # paste a value (prompts stdin)
echo -n "value" | gopass insert -f <path>   # non-interactive insert
gopass generate <path> [length]   # random password, default 24 chars
gopass edit <path>                # open in $EDITOR
gopass rm <path>                  # delete
gopass mv <old> <new>             # rename / move
```

### Sync

```bash
gopass sync                       # pull + push against the remote git
gopass --nosync <cmd>             # skip auto-sync for one command
```

### TOTP / OTP

```bash
gopass otp <path>                 # current TOTP code
gopass otp -c <path>              # copy TOTP to clipboard
```

## Patterns Claude should use

Always use `-o` (password only) to capture a secret, and prefer command substitution over writing to disk:

```bash
export OPENAI_API_KEY="$(gopass show -o personal/ai/openai)"
```

For a one-shot subprocess with multiple secrets, `gopass env` injects them without exposing values to the parent shell:

```bash
gopass env personal/ai -- python my_script.py
```

Before asking the user to paste or type a secret, `gopass find <keyword>` to discover the exact path; only ask if nothing matches. `gopass show <path> <key>` pulls one structured field (see Read above).

## Common workflows

### Add a credential

Ask for only:

1. Environment variable name if the credential must be loaded by the shell, for example `SERVICE_API_KEY`.
2. Gopass path, for example `personal/service/api-key`.
3. The value through the interactive hidden prompt. Never ask the user to paste it into chat or pass it as a command argument.

```bash
gopass insert personal/service/api-key
gopass sync
```

### Rotate an existing credential

Discover the exact path first, then overwrite interactively and sync:

```bash
gopass find service
gopass insert -f personal/service/api-key
gopass sync
```

### Connect a credential to `~/.envrc`

Prefer a repository helper over editing encrypted bundles manually. If the password-store repository provides `scripts/gopass-env` or matching Make targets, use:

```bash
make env-put NAME=SERVICE_API_KEY SECRET=personal/service/api-key
make env-link NAME=SERVICE_API_KEY SECRET=personal/service/api-key
make env-remove NAME=SERVICE_API_KEY
make env-list
```

- `env-put` prompts for a value, stores it, and adds or updates the export.
- `env-link` exports an existing entry.
- `env-remove` removes only the export and keeps the secret.
- `env-list` prints names only, never values.

After changes, tell the user to reload direnv or source `~/.envrc`. If no helper exists, add a direct runtime lookup without embedding the value:

```bash
export SERVICE_API_KEY="$(gopass --nosync show -o personal/service/api-key)"
```

### Delete a credential

Confirm whether the user wants to remove only its shell export, only the stored secret, or both. Then use `gopass rm <path>` only for the explicitly requested secret deletion.

## Safety rules

- **Never echo / print / log a decrypted secret to terminal output the user is recording.** Pipe directly into the consumer (env var, config file write, stdin of a tool).
- **Never write secrets to files outside the store** unless the user explicitly asks (e.g. populating a `.env`). When you do, confirm the file is gitignored first.
- **Never commit a secret to a repo.** Even after generating one - the value goes in gopass, the consumer reads it at runtime.
- **Don't cache / restate / summarize** the secret value back to the user in chat. Confirm by name only ("retrieved `personal/ai/openai`").
- If `gpg` errors with "Decryption failed" or "Inappropriate ioctl for device", run `gpgconf --kill gpg-agent && gpg-agent --daemon` and retry. Don't keep retrying blindly.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `entry is not in the password store` | wrong path | `gopass find <keyword>` to discover the real path |
| `Decryption failed` | gpg-agent stuck | `gpgconf --kill gpg-agent && gpg-agent --daemon` |
| `Inappropriate ioctl for device` | no TTY for passphrase | run from an interactive terminal, not a pipe |
| `no secret key` | gpg key missing on this machine | escalate - only the user can import it |
| sync conflict | concurrent edits | `cd "$(gopass config mounts.path)" && git status` then resolve |
| anything else off | store health / settings drift | `gopass doctor`; `gopass config` prints store settings incl. the path (`mounts.path`) |

## References

- Official command docs: https://github.com/gopasspw/gopass/blob/master/docs/commands/
- If the user's store has a `Makefile` at the store root, it may expose shortcuts (`make show PATH=...`, `make copy PATH=...`, `make search QUERY=...`) for interactive use - prefer raw `gopass` for scripting.
