# Git Safety Protocols

## Secret detection

### Scan command (used at commit time)

```bash
git diff --cached | grep -iE "(AKIA[0-9A-Z]{16}|api[_-]?key|token|password|secret|credential|private[_-]?key|-----BEGIN|mongodb://|postgres://|mysql://|redis://|client_secret|oauth_token)"
```

### Patterns

| Category | Pattern | Example |
|---|---|---|
| AWS access key | `AKIA[0-9A-Z]{16}` | `AKIAIOSFODNN7EXAMPLE` |
| API keys | `api[_-]?key`, `apiKey` | `API_KEY=abc123` |
| Tokens | `token`, `auth_token`, `jwt` | `AUTH_TOKEN=xyz` |
| Passwords | `password`, `passwd`, `pwd` | `DB_PASSWORD=secret` |
| Private keys | `-----BEGIN .* PRIVATE KEY-----` | PEM files |
| DB URLs | `mongodb://`, `postgres://`, `mysql://`, `redis://` | Connection strings |
| OAuth | `client_secret`, `oauth_token` | `CLIENT_SECRET=abc` |

### Files to refuse

- `.env`, `.env.local`, `.env.production` (always — only `.env.example` may be staged)
- `*.key`, `*.pem`, `*.p12`, `*.pfx`
- `credentials.json`, `secrets.json`, `secrets.yaml`, `private.toml`
- Anything in `secrets/`, `.secrets/`, `vault/`

### Action on detection

1. **Block the commit immediately** — do not proceed to `git commit`
2. Show matching lines with context:
   ```bash
   git diff --cached | grep -B2 -A2 -iE "<pattern>"
   ```
3. Surface the file(s) and offending lines to the user
4. Offer remediation:
   - Add to `.gitignore` → `git reset HEAD <file>` to unstage
   - Move value to env var or secret manager (`gopass`, AWS SSM, GCP Secret Manager)
   - If false positive (e.g. example value in test fixture) → user can override explicitly

**Do not** auto-unstage. The user decides what to do with each match.

## Branch protection

### Never force-push to

- `main`, `master`
- `production`, `prod`, `live`
- `release/*`
- `develop`, `dev`, `staging` (project-dependent — when in doubt, ask)

If user explicitly requests force-push on a feature branch, use `--force-with-lease` (refuses if remote moved unexpectedly):
```bash
git push --force-with-lease origin HEAD
```

### Pre-merge conflict probe

```bash
git merge --no-commit --no-ff "origin/$FROM" && git merge --abort
```

Surfaces conflict files before the real merge — escape hatch for the user.

### Remote-first compare

For PR/diff analysis, always compare via `origin/`:
- ✅ `git diff origin/main...origin/feature` — true PR diff
- ❌ `git diff main...HEAD` — includes uncommitted local WIP

## Error recovery

### Undo last commit (unpushed)

```bash
git reset --soft HEAD~1   # Keep changes staged
git reset HEAD~1          # Keep changes unstaged (default)
git reset --hard HEAD~1   # DISCARD changes — confirm first
```

### Abort merge / rebase

```bash
git merge --abort
git rebase --abort
git cherry-pick --abort
```

### Discard local changes

```bash
git checkout -- <file>   # Single file — irreversible
git restore <file>       # Same, newer syntax
git reset --hard HEAD    # All files — DANGER, confirm first
git clean -fd            # Delete untracked files — DANGER, confirm first
```

### Recover after force-push (if pre-push happened recently)

```bash
git reflog                  # Find the lost SHA
git reset --hard <sha>      # Restore to that point
```

## Hard rules

- **Confirm before any destructive operation**: `--hard`, `clean -fd`, `--force`, `--force-with-lease`, branch delete, `rm -rf .git`.
- **Never** use `--no-verify` / `--no-gpg-sign` unless user explicitly asked. Hook failures mean fix the underlying issue.
- **Never** commit secrets even temporarily "just to test" — once in history, they're public until rewritten.
- **Never** rewrite published history without coordinating with collaborators.
