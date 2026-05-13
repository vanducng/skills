# Merge Workflow

Default: execute via `git-manager` subagent. `--inline` keeps it in main context.

## Variables

- `TO_BRANCH` — target (default `main`)
- `FROM_BRANCH` — source (default current branch)

## Why `origin/<from>`, not local

Merging `origin/<from>` ensures you merge only committed + pushed changes — not local WIP. If a teammate is collaborating on the source branch, their commits matter; yours-not-yet-pushed don't.

## Step 1 — Sync target

```bash
git fetch origin
git checkout "$TO_BRANCH"
git pull origin "$TO_BRANCH"
```

If target has uncommitted changes → abort, ask user to commit or stash first.

## Step 2 — Pre-merge conflict probe

```bash
git merge --no-commit --no-ff "origin/$FROM_BRANCH" && git merge --abort
```

Surface conflict files before the real merge — gives user a chance to back out.

## Step 3 — Merge from remote

```bash
git merge "origin/$FROM_BRANCH" --no-ff -m "merge: $FROM_BRANCH into $TO_BRANCH"
```

`--no-ff` preserves merge history (useful for traceability). Drop only if the project explicitly uses fast-forward-only merges.

## Step 4 — Resolve conflicts (if any)

1. Resolve files manually — Edit tool, not auto-merge tools
2. `git add <resolved-files>`
3. `git commit` (uses the merge message git already drafted)
4. If you can't resolve cleanly → `git merge --abort`, surface to user

## Step 5 — Push

```bash
git push origin "$TO_BRANCH"
```

If `$TO_BRANCH` is protected (main/master/production) and push is rejected, do not force-push. Surface the rejection to user.

## Output format

```
✓ merged: origin/<from> → <to>
  commits merged: N
  conflicts: <count> resolved | none
✓ pushed: origin/<to>
```

## Error handling

| Error | Action |
|---|---|
| Merge conflicts | Resolve manually, commit, continue. If unclear → abort and ask user. |
| Branch not found | Verify `git branch -a`, ensure `$FROM` pushed to remote |
| Push rejected | `git pull --rebase origin $TO`, retry. Never force-push to protected branch. |
| Uncommitted changes on $TO | Abort, ask user to commit/stash |
| Hooks failed during merge commit | Surface, abort. **Do not** `--no-verify`. |

## Hard rules

- **Always** `git fetch origin` first — stale refs cause silent wrong merges.
- **Always** merge `origin/<from>`, never local `<from>`.
- **Never** force-push to a protected branch after a merge that went sideways. Revert with a new merge commit instead.
- **Never** auto-resolve conflicts using `git checkout --theirs` / `--ours` without explicit user direction.
