# Pull Request Workflow

Default: execute via `git-manager` subagent. `--inline` keeps it in main context.

## Variables

- `TO_BRANCH` - target (default `main`)
- `FROM_BRANCH` - source (default current branch via `git rev-parse --abbrev-ref HEAD`)

## CRITICAL: use remote diff

PRs are based on remote branches. Local diff includes unpushed WIP and produces wrong content.

- ✅ `git diff origin/$TO...origin/$FROM`
- ❌ `git diff $TO...HEAD`
- ❌ `git diff --cached`

## Tool 1 - Sync + analyze

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
**If empty diff:** warn "no changes between $FROM and $TO - nothing to PR" and abort.

## Tool 1b - Ticket branch guard

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

## Tool 2 - Generate content

**Title + body rules** live in `pr-template.md` - the canonical PR convention shared with `vd:ship`. Load it for:
- Past-tense (v-ed) title rules + ticket-prefix detection
- Repo-template-wins detection (`.github/pull_request_template.md`)
- Fallback Why / What / Risks + verification block body shape
- Per-bullet fill rules and worked examples
- `gh pr create --fill` post-edit rule

This file owns the *process* (sync remote, diff, create PR). `pr-template.md` owns the *content shape*.

## Tool 3 - Create PR

Pass the body as a file. Nested `--body "$(cat <<'EOF' …)"` dies in agent bash
wrappers with `bad substitution: no closing ')'`. `--body-file` (or `--body-file -`
reading a heredoc on stdin) is the safe path. See `gh-cli-guide.md`.

```bash
gh pr create --base "$TO" --head "$FROM" \
  --title "<v-ed title>" \
  --body-file - <<'EOF'
- **Why:** ...
- **What:** ...
- **Risks:** none.

**Tests:** ✓ N
**Docs:** – N/A
**Breaking:** –
EOF
```

**Existing PR for this branch:** `gh pr edit --body-file`, don't re-create.
**Draft mode** when WIP: add `--draft`.
**Landing:** only on explicit user request. Never `gh pr checks N && gh pr merge N`
— `gh pr checks` exits **8** while a check is pending, so the merge never runs.
Wait with `scripts/wait-for-checks.sh` then merge, or queue `gh pr merge --auto`.
Unresolved review threads stay blocked by `hooks/pr-merge-guard.py`. Full CI
watch + comment gates: `vd:ship` Steps 15–16.

## Tool 4 - PR feedback pass

Run a feedback loop after creating/updating the PR, especially when editing an
existing PR or when bot review comments have already appeared. This is the
small `vd:ship` Step 13 loop: fetch, triage, fix valid comments, repair resolved
threads missing inline rationale, re-run the bot if available, then fetch again
until there are no actionable unresolved items.

**Mandate - reply inline to every finding-bearing comment, valid or not:**
- **Valid** → fix it, then reply inline **naming the exact fix commit SHA** (e.g. "Fixed in `a1b2c3d`.") and what changed.
- **Invalid / false positive** → reply inline with the concrete rationale (why it's wrong / stale / already handled).
- **Deferred (valid, out of scope for this PR)** → reply inline saying so and link the follow-up ticket/PR, then resolve.
- **CI failures** → diagnose from the failing job log, fix, commit + push, and re-check; never leave the PR red without an explicit user override.
No finding-bearing comment (human or bot) is left without an inline reply. A pure summary/FYI with no point raised needs none.

Fetch review threads, review bodies, and top-level comments:

```bash
OWNER_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
OWNER=${OWNER_REPO%/*}; REPO=${OWNER_REPO#*/}
PR_NUMBER=$(gh pr view --json number -q .number)
gh api graphql -f query='
  query($owner:String!,$repo:String!,$pr:Int!){
    repository(owner:$owner,name:$repo){
      pullRequest(number:$pr){
        comments(first:50){nodes{author{login} body url createdAt}}
        reviews(last:50){nodes{state author{login} body url submittedAt}}
        reviewThreads(first:50){nodes{
          id isResolved isOutdated
          comments(first:10){nodes{id databaseId path line body author{login} url}}
        }}
      }
    }
  }' -F owner="$OWNER" -F repo="$REPO" -F pr="$PR_NUMBER" \
  > /tmp/git-pr-feedback.json
```

Triage before editing:

- **Actionable:** a concrete bug, broken contract, security/data-loss risk, flaky test, or useful improvement with a clear benefit.
- **Informational:** summaries, style preference, bot lifecycle notices, general praise, or FYI.
- **Noise/false positive:** stale, already handled, incorrect, or unrelated.

For every substantive suggestion, validate it against codebase evidence first:

- Source of truth: config/schema validation, type definitions, route/API docs,
  tests, env-loading behavior, database constraints, feature flags, and repo
  rules.
- Prefer the smallest root-cause fix that follows local patterns. Do not apply
  bot suggestions blindly.
- If the comment is valid but the suggested patch is not the right fix, apply
  the better fix and explain why.

When replying to handled threads, use a concise rationale:

```text
Handled in <short-sha> by <specific change>. <Why this matches the codebase contract / why a different root-cause fix was chosen>.
```

Generic examples:

- `Handled in <short-sha> by validating <CONFIG_KEY> at load time, keeping bad configuration fail-fast instead of silently defaulting.`
- `Handled in <short-sha> by replacing a fixed sleep with a polling helper for the async assertion.`
- `Not applying as suggested: <schema/type/test> already guarantees <condition>. Added <test/comment> to make the contract explicit.`

After a valid fix:

1. Commit on top; never amend a published commit.
2. Push normally.
3. Reply to the thread with the short SHA + rationale.
4. Resolve only threads that were fixed or proven false/stale, and only after the inline reply succeeds.
5. For already-resolved threads with no explanatory inline reply, post the retrospective rationale before treating them as clear.
6. Re-run the narrow relevant checks.
7. If the repo has OpenCodeReview (`code-review.yml`), comment `/ocr`, wait for
   the `issue_comment` run, then fetch threads again.
8. Repeat this feedback loop until `reviewThreads` has zero
   `isResolved == false && isOutdated == false` actionable threads and zero
   resolved threads missing explanatory replies. For full CI watching and merge
   gating use `vd:ship`.

## Tool 5 - Report

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
| `bad substitution: no closing ')'` | Rewrite with `--body-file` / `--body-file -`; do not retry the `$(cat <<` form |
| `gh pr checks` exit 8 | Pending, not failure. Poll (`wait-for-checks.sh`) or queue `gh pr merge --auto` |

## Hard rules

- **Always sync `origin/$TO` into the branch first** if user is shipping. (`vd:ship` does this; for ad-hoc PRs, suggest it if `origin/$TO` is ahead.)
- **Never** create a PR with a draft title like "WIP" unless `--draft` is also set.
- **Never** include AI attribution in title, body, or comments - no "Generated with Claude", `Co-Authored-By: Claude`, or `https://claude.ai/code/session_...` session links.
