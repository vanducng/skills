---
name: gopass
description: "Retrieve credentials (API keys, tokens, passwords) from the local gopass password store. Use when a task needs a secret that the user has stored in gopass - instead of asking the user to paste it, search the store and read the value with `gopass find` / `gopass show -o`. Also covers inserting, generating, listing, searching, syncing, and TOTP."
license: MIT
metadata:
  author: vanducng
  version: "1.0.0"
  upstream: "https://github.com/gopasspw/gopass"
---

# gopass

Local password store wrapped around GPG. Secrets live as encrypted files in a git repo and decrypt on demand. The user has it installed and initialized - commands "just work" on this machine.

## When to use

- Task needs an API key / token / password and the user mentions it's "in gopass" or "in the password store"
- Before asking the user to paste a secret, check if the store has it (`gopass find <keyword>`)
- Setting up env vars for a script that needs credentials
- Adding a new secret the user wants stored

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

### Capture a secret into a script env var

Always use `-o` (password only) to avoid leaking the key:value metadata, and prefer command substitution over writing to disk:

```bash
export OPENAI_API_KEY="$(gopass show -o personal/ai/openai)"
```

For a one-shot subprocess with multiple secrets, `gopass env` injects them without exposing values to the parent shell:

```bash
gopass env personal/ai -- python my_script.py
```

### Find before asking

When unsure of the exact path, search first:

```bash
gopass find openai      # → personal/ai/openai
gopass find github      # → personal/github/access-token
```

If nothing matches, then ask the user.

### Extract a structured field

```bash
gopass show work/some-service username     # just the username field
gopass show work/some-service               # everything (password + fields)
```

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
| sync conflict | concurrent edits | `cd "$(gopass config path)" && git status` then resolve |

## Discovery

```bash
gopass ls                         # see what's available
gopass config                     # store path, recipients, settings
gopass recipients                 # GPG keys that can decrypt
gopass doctor                     # health check
```

## References

- Official command docs: https://github.com/gopasspw/gopass/blob/master/docs/commands/
- If the user's store has a `Makefile` at the store root, it may expose shortcuts (`make show PATH=...`, `make copy PATH=...`, `make search QUERY=...`) for interactive use - prefer raw `gopass` for scripting.
