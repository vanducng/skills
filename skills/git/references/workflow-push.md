# Push Workflow

Default: execute via `git-manager` subagent. `--inline` keeps it in main context.

## Pre-push checklist

1. **All changes committed** — `git status` clean
2. **Tests green** — per `~/.claude/rules/development-rules.md`: don't push failing tests just to land
3. **Secrets scanned** — see `safety-protocols.md` (also runs at commit time)

## Tool 1 — Verify state

```bash
git status && \
HEAD=$(git rev-parse --abbrev-ref HEAD) && \
git log origin/$HEAD..HEAD --oneline 2>/dev/null || echo "NO_UPSTREAM"
```

**If uncommitted changes:** warn user, suggest commit first.
**If `NO_UPSTREAM`:** use `git push -u origin HEAD`.

## Tool 2 — Push

```bash
git push origin HEAD
```

On success, report commit hashes pushed:
```bash
git log origin/$HEAD~..origin/$HEAD --oneline
```

## Error handling

| Error | Cause | Action |
|---|---|---|
| `rejected — non-fast-forward` | Remote has newer commits | Surface, suggest `git pull --rebase`, resolve conflicts, push again. Do not force-push without user request. |
| `no upstream branch` | First push of this branch | `git push -u origin HEAD` |
| `Authentication failed` | Bad creds | Check `gh auth status` or SSH keys, surface to user |
| `Repository not found` | Wrong remote URL | Show `git remote -v`, ask user |
| `Permission denied` | No write access | Check repo permissions, surface to user |
| Pre-push hook failed | Hook caught something | Surface hook output, abort. **Do not** use `--no-verify`. |

## Force push (DANGER)

**Never** force push to: `main`, `master`, `production`, `prod`, `release/*`.

If user **explicitly** requests force push on a feature branch:
```bash
git push --force-with-lease origin HEAD
```

`--force-with-lease` is safer than `-f` — it refuses if remote moved unexpectedly. Always prefer it.

Warn the user: "Force push rewrites history. Anyone who pulled this branch will need to re-sync."

## Output format

```
✓ pushed: N commits to origin/<branch>
  - <sha> <type(scope): subject>
  - <sha> <type(scope): subject>
```

If `NO_UPSTREAM`:
```
✓ pushed: N commits (new upstream → origin/<branch>)
```
