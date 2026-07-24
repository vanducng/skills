# GitHub CLI Guide

Quick reference for the `gh` commands used by this skill. Full docs: `gh help <command>`.

## Authentication

```bash
gh auth login         # Interactive login
gh auth status        # Check current state
gh auth refresh       # Refresh token scopes
gh auth logout        # Logout
```

## Pull Requests

### Create

PR titles are **past tense (v-ed)** - describe what the PR did. Commit messages stay imperative; only the title flips. See `workflow-pr.md` for full rules.

```bash
# Basic
gh pr create --base main --head feature-branch \
  --title "feat(auth): added OAuth" \
  --body "Summary"

# With HEREDOC body (preferred for multi-line)
gh pr create --base main \
  --title "feat(auth): added OAuth" \
  --body "$(cat <<'EOF'
- **Why:** Replace home-rolled session middleware with OAuth2. Closes #42.
- **What:** added OAuth2 provider; refresh-token rotation; rate-limited /login.
- **Risks:** Breaking - sessions invalidated on deploy.

**Tests:** ✓ 127
**Docs:** ✓
**Breaking:** ⚠ see CHANGELOG
EOF
)"

# Draft
gh pr create --draft --title "WIP: new feature"

# Reviewers + labels
gh pr create --reviewer user1,user2 --label "needs-review,priority:high"

# Auto-fill (uses commit messages - imperative!)
gh pr create --fill
# After --fill, re-edit the title to past tense (v-ed) so it matches our convention:
gh pr edit --title "feat(auth): added OAuth"
```

### View / inspect

```bash
gh pr list                       # PRs in current repo
gh pr list --state open --author "@me"
gh pr view 123                   # PR details
gh pr view 123 --web             # Open in browser
gh pr view 123 --json title,body,commits,reviews
gh pr checkout 123               # Check out PR branch locally
gh pr diff 123                   # View diff
gh pr status                     # Your PRs + reviews requested
```

### Comments

```bash
gh pr comment 123 --body "LGTM!"
gh api repos/{owner}/{repo}/pulls/123/comments    # all review comments (line-level)
gh api repos/{owner}/{repo}/issues/123/comments   # issue-style comments
```

### Merge

```bash
gh pr merge 123                  # Default (uses repo merge setting)
gh pr merge 123 --squash         # Squash and merge
gh pr merge 123 --rebase         # Rebase and merge
gh pr merge 123 --merge          # Merge commit
gh pr merge --auto --squash      # Auto-merge once checks pass
gh pr merge 123 --delete-branch  # Cleanup after merge
```

## Issues

```bash
gh issue list                                  # List issues
gh issue list --search "label:bug timeout"     # Search
gh issue view 42                               # View
gh issue create --title "Bug: X" --body "..."  # Create
gh issue develop 42 -c                         # Create + check out branch from issue
gh issue close 42 --comment "Fixed in #43"
```

## Repository

```bash
gh repo view                       # Current repo info
gh repo view <owner>/<repo>        # Specific repo
gh repo clone <owner>/<repo>
gh repo create <name> --public     # Create new repo
gh browse                          # Open repo in browser
gh browse path/to/file:42          # Open file at line
```

## Workflow runs (Actions)

```bash
gh run list                         # Recent runs
gh run list --workflow=ci.yml       # Filter by workflow
gh run view <run-id>                # Details
gh run view <run-id> --log          # Full log
gh run view <run-id> --log-failed   # Only failed steps
gh run watch                        # Watch most recent run live
gh run rerun <run-id>               # Rerun failed run
gh run rerun <run-id> --failed      # Only failed jobs
gh workflow list                    # List workflows
gh workflow run <workflow.yml>      # Manually trigger
```

## Releases

```bash
gh release list
gh release view v1.2.0
gh release create v1.2.0 --notes "..." --target main
gh release create v1.2.0 --generate-notes      # Auto-generated changelog
gh release upload v1.2.0 dist/binary           # Attach assets
```

## JSON output (for scripting)

```bash
gh pr list --json number,title,author,headRefName
gh pr view 123 --json commits,reviews,checksState
gh issue list --json number,title --jq '.[].title'
gh run list --json conclusion,name --jq '.[] | select(.conclusion=="failure")'
```

## Common one-liners

```bash
# Create PR with auto-merge
gh pr create --fill && gh pr merge --auto --squash

# Last failed run, view log
gh run list --json databaseId,conclusion --jq '.[] | select(.conclusion=="failure") | .databaseId' | head -1 | xargs gh run view --log-failed

# Open current branch's PR in browser
gh pr view --web

# Check if branch has open PR
gh pr list --head "$(git rev-parse --abbrev-ref HEAD)" --json number --jq '.[0].number'

# Find your assigned reviews
gh pr status --json url,title -q '.currentBranch,.createdBy,.needsReview'
```

## Tips

- Use `--web` to open in browser when the JSON output isn't enough.
- `gh api` is the escape hatch for anything the high-level commands don't cover - full GitHub REST API.
- For long output, pipe through `less` or extract with `--jq`.
- `gh repo set-default` to set the default repo for the current directory if `gh` keeps prompting.
