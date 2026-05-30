# Pull Request Workflow

Default: execute via `git-manager` subagent. `--inline` keeps it in main context.

## Variables

- `TO_BRANCH` — target (default `main`)
- `FROM_BRANCH` — source (default current branch via `git rev-parse --abbrev-ref HEAD`)

## CRITICAL: use remote diff

PRs are based on remote branches. Local diff includes unpushed WIP and produces wrong content.

- ✅ `git diff origin/$TO...origin/$FROM`
- ❌ `git diff $TO...HEAD`
- ❌ `git diff --cached`

## Tool 1 — Sync + analyze

```bash
git fetch origin && \
git push -u origin HEAD 2>/dev/null || true && \
TO=${TO_BRANCH:-main} && \
FROM=$(git rev-parse --abbrev-ref HEAD) && \
echo "=== PR: $FROM → $TO ===" && \
echo "=== COMMITS ===" && \
git log origin/$TO...origin/$FROM --oneline && \
echo "=== STAT ===" && \
git diff origin/$TO...origin/$FROM --stat && \
echo "=== FILES ===" && \
git diff origin/$TO...origin/$FROM --name-only
```

**If "branch not on remote":** push first (`git push -u origin HEAD`), retry.
**If empty diff:** warn "no changes between $FROM and $TO — nothing to PR" and abort.

## Tool 1b — Ticket branch guard

Before creating or editing a PR, detect issue keys from the user request,
branch name, commit subjects, and PR body context:

```bash
TICKET=$(printf '%s\n' "$USER_REQUEST" "$FROM" "$(git log origin/$TO...origin/$FROM --format=%s)" \
  | grep -Eio '[A-Z][A-Z0-9]+-[0-9]+' | head -1 | tr '[:lower:]' '[:upper:]')
```

If `TICKET` is non-empty and `FROM` does not start with that key, **rename the
branch before PR creation**:

```bash
git branch -m "$TICKET"
git push -u origin "$TICKET"
```

If the old branch was already pushed and has no open PR that should remain,
delete it after the replacement PR exists:

```bash
git push origin --delete "$FROM"
```

Do not open a PR from a non-ticket branch when the work is clearly tied to a
ticket. This avoids later PR replacement churn and keeps branch naming, PR title,
and Jira/Linear traceability aligned.

## Tool 2 — Generate content

**Title + body rules** live in `pr-template.md` — the canonical PR convention shared with `/vd:ship`. Load it for:
- Past-tense (v-ed) title rules + ticket-prefix detection
- Repo-template-wins detection (`.github/pull_request_template.md`)
- Fallback Why / What / Risks + verification stripe body shape
- Per-bullet fill rules and worked examples
- `gh pr create --fill` post-edit rule

This file owns the *process* (sync remote, diff, create PR). `pr-template.md` owns the *content shape*.

## Tool 3 — Create PR

```bash
gh pr create --base "$TO" --head "$FROM" \
  --title "<v-ed title>" \
  --body "$(cat <<'EOF'
- **Why:** ...
- **What:** ...
- **Risks:** none.

_Tests: ✓ N · Docs: – N/A · Breaking: –_
EOF
)"
```

**Existing PR for this branch:** use `gh pr edit`, don't re-create.
**Draft mode** when WIP: add `--draft`.
**Auto-merge** only on explicit user request: `gh pr merge --auto --squash` after creation.

## Tool 4 — Report

```
✓ PR created: <url>
  title: <title>
  base: <to> ← head: <from>
  commits: N | files: M | +X / -Y
```

## Error handling

| Error | Action |
|---|---|
| Branch not on remote | `git push -u origin HEAD`, retry |
| Empty diff | Warn, abort |
| Push rejected | `git pull --rebase`, resolve, retry |
| `gh: not authenticated` | Surface `gh auth status`, ask user |
| Existing open PR for this branch | Show URL, ask user: update vs create new |

## Hard rules

- **Always sync `origin/$TO` into the branch first** if user is shipping. (`/vd:ship` does this; for ad-hoc PRs, suggest it if `origin/$TO` is ahead.)
- **Never** create a PR with a draft title like "WIP" unless `--draft` is also set.
- **Never** include AI attribution in title or body.
