# Branch Management

## Naming convention

**Format:** `<type>/<descriptive-kebab-name>`

| Type | Purpose | Example |
|---|---|---|
| `feature/` | New features | `feature/oauth-login` |
| `fix/` | Bug fixes | `fix/db-timeout` |
| `refactor/` | Restructure | `refactor/api-cleanup` |
| `perf/` | Performance | `perf/queue-batching` |
| `docs/` | Documentation | `docs/api-reference` |
| `test/` | Test work | `test/integration-suite` |
| `chore/` | Maintenance | `chore/deps-update` |
| `hotfix/` | Production fixes | `hotfix/payment-crash` |
| `release/` | Release branches | `release/1.2.0` |

Rules:
- Lowercase, kebab-case after the `/`
- Descriptive, not date-stamped (`feature/checkout-v2`, not `feature/2026-05-checkout`)
- ≤ 50 chars total when possible — long names get truncated in tools

## Lifecycle

### Create

```bash
git checkout main
git pull origin main
git checkout -b feature/<descriptive-name>
```

### During development

```bash
# Commit regularly
git add <files>
git commit -m "feat(scope): description"

# Stay current with main (rebase, not merge, for feature branches)
git fetch origin
git rebase origin/main

# If rebase produces conflicts: resolve, git add, git rebase --continue
```

### Before merge

```bash
# Push final state
git push origin feature/<name>

# Or after a rebase (only feature branches — never main/master)
git push --force-with-lease origin feature/<name>
```

### After merge

```bash
# Delete local
git branch -d feature/<name>

# Delete remote (or let GitHub do it when merging the PR)
git push origin --delete feature/<name>

# Prune stale tracking refs
git fetch --prune
```

### Reusing a branch after a squash-merge

A branch that was **squash-merged** but kept for more work is a trap. The squash lands a *new* commit on the base that shares no identity with the branch's commits, so a follow-up PR's three-dot diff (computed from the merge-base) **re-lists every already-merged file** — bloating the diff and re-triggering any `paths:`-filtered CI (e.g. a schema/ERD preview firing on files you never touched).

Confirm it's a pure squash artifact (content identical to base), then collapse the branch onto the base with a **soft reset** — conflict-free, unlike `git rebase origin/<base>` which replays the old commits and conflicts on the already-final state:

```bash
git diff origin/<base> origin/<branch> -- <already-merged-path>   # empty ⇒ identical, safe to drop
git fetch origin
git reset --soft origin/<base>     # branch tip → base, working tree + index kept
git status                          # identical files vanish from the diff; only new work staged
git commit -m "feat(scope): ..."
git push --force-with-lease origin <branch>   # feature branch only; updates the open PR in place
```

The already-merged files drop out automatically (no diff vs base), so the PR diff is just the new work and the path-filtered CI stops firing.

## Branch strategies

### Trunk-based (preferred for solo / small teams)

```
main (always deployable)
  └─ feature/* (short-lived, < 1 week)
```

PRs merge straight to `main`. Releases are tags. CI deploys from `main`.

### Git Flow (when releases are coordinated)

```
main (production tags)
develop (integration)
  ├─ feature/*
  ├─ bugfix/*
  ├─ release/*
  └─ hotfix/*
```

Use when releases need cutting branches and stabilization windows.

### Stacked PRs (advanced)

```
main
  └─ feature/part-1
       └─ feature/part-2
            └─ feature/part-3
```

Each PR targets the previous. Useful for large features that need incremental review. Requires discipline — rebase the stack when the base moves.

## Quick command reference

| Task | Command |
|---|---|
| List local branches | `git branch` |
| List all (incl. remote) | `git branch -a` |
| Current branch | `git rev-parse --abbrev-ref HEAD` |
| Switch | `git checkout <branch>` or `git switch <branch>` |
| Create + switch | `git checkout -b <branch>` or `git switch -c <branch>` |
| Delete local (merged) | `git branch -d <branch>` |
| Delete local (force) | `git branch -D <branch>` (confirm first) |
| Delete remote | `git push origin --delete <branch>` |
| Rename current | `git branch -m <new-name>` |
| Prune stale tracking | `git fetch --prune` |
| Show upstream | `git rev-parse --abbrev-ref @{u}` |

## Hard rules

- **Never** delete a branch you haven't pushed if it has unique commits — they'll be lost unless you have the SHA.
- **Never** rebase a branch others are working on without coordinating.
- **Never** create a branch from a dirty `main` — pull first.
- **Always** prefer `--force-with-lease` over `-f` when force-pushing (protects against overwriting remote commits you haven't seen).
