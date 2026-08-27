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

# Multi-line body: --body-file, never --body "$(cat <<'EOF' …)"
# Nested command-sub + heredoc dies in agent bash wrappers:
#   /bin/bash: bad substitution: no closing ')'
# --body-file - reads the heredoc on stdin (no temp file). A pre-written
# file works the same: gh pr create --body-file "$BODY"
gh pr create --base main \
  --title "feat(auth): added OAuth" \
  --body-file - <<'EOF'
- **Why:** Replace home-rolled session middleware with OAuth2. Closes #42.
- **What:** added OAuth2 provider; refresh-token rotation; rate-limited /login.
- **Risks:** Breaking - sessions invalidated on deploy.

**Tests:** ✓ 127
**Docs:** ✓
**Breaking:** ⚠ see CHANGELOG
EOF

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

### Attach screenshots (before/after evidence)

Optional - use when captures already exist and an image is genuinely clearer than a sentence.
Never hold up a PR to produce one.

`gh` has no first-party way to attach a local image so it renders inline. **On a private
repo most workarounds silently produce broken images** - GitHub's camo proxy cannot
authenticate to private content, so `raw.githubusercontent.com` URLs, release assets, and
gists all render as broken icons. Only `user-attachments` URLs work.

Upload via the endpoint the browser's drag-drop uses; it accepts a normal bearer token:

```bash
gh_upload_image() {  # usage: gh_upload_image <file> [owner/repo]
  local file="$1" repo="${2:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"
  local rid; rid=$(gh api "repos/$repo" --jq '.id')   # numeric id, NOT owner/repo
  local type; case "$file" in
    *.png) type=image/png;; *.gif) type=image/gif;;
    *.jpg|*.jpeg) type=image/jpeg;; *) type=application/octet-stream;; esac
  curl -sS -X POST \
    "https://uploads.github.com/user-attachments/assets?name=$(basename "$file")&content_type=$type&repository_id=$rid" \
    -H "Authorization: Bearer $(gh auth token)" \
    -H "Accept: application/json" \
    --data-binary @"$file" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['url'])"
}
```

Returns `https://github.com/user-attachments/assets/<uuid>` (HTTP 201). GitHub rewrites it on
render to a signed, expiring `private-user-images.githubusercontent.com/...?jwt=...` URL scoped
to the viewer, so the image inherits repo visibility.

Embed side by side with HTML, not `![]()` - markdown image syntax has no width control:

```bash
BEFORE=$(gh_upload_image before.png)
AFTER=$(gh_upload_image after.png)
gh pr view 123 --json body --jq '.body' > /tmp/body.md
BEFORE="$BEFORE" AFTER="$AFTER" python3 - <<'PY'
import os, pathlib
p = pathlib.Path("/tmp/body.md"); t = p.read_text()
table = ('<table>\n<tr><th>Before</th><th>After</th></tr>\n'
         f'<tr><td><img src="{os.environ["BEFORE"]}" width="480"></td>'
         f'<td><img src="{os.environ["AFTER"]}" width="480"></td></tr>\n</table>\n')
assert "<!-- SCREENSHOTS -->" in t, "no marker in PR body"
p.write_text(t.replace("<!-- SCREENSHOTS -->", table, 1))
PY
gh pr edit 123 --body-file /tmp/body.md
```

Leave a `<!-- SCREENSHOTS -->` marker when drafting the body - invisible when rendered, and it
gives the upload step a deterministic insertion point.

**Verify** - a broken embed looks fine in the raw body, so check the rendered result:

```bash
# On a private repo the asset must 404 unauthenticated. A 200 means it leaked publicly.
curl -s -o /dev/null -w "%{http_code}\n" "$BEFORE"                                                 # expect 404
curl -s -o /dev/null -w "%{http_code}\n" -L -H "Authorization: Bearer $(gh auth token)" "$BEFORE"   # expect 200
```

Open the PR and check `naturalWidth` - a broken image reports `0`:

```js
[...document.querySelectorAll('img')].filter(i => i.naturalWidth > 200)
  .map(i => ({ w: i.naturalWidth, h: i.naturalHeight }))
```

Caveats:

- **Undocumented endpoint.** No published size/rate limits or deprecation policy. Check for
  HTTP 201 and a `url` key; never assume success in unattended automation.
- `repository_id` must be the numeric id - passing `owner/repo` fails.
- Verified with a user token via `gh auth token`; untested with `GITHUB_TOKEN` in Actions.
- Cropping: `sips -c H W` crops from the **center**. For top-left use
  `python3 -c "from PIL import Image; Image.open('in.png').crop((0,0,W,H)).save('out.png')"`.

### Checks (`gh pr checks`)

`gh pr checks` is a snapshot, not a waiter. Additional exit code **8** means
checks are still **pending**. That is retry, not failure.

| Exit | Meaning | Next step |
|---|---|---|
| 0 | All listed checks passed | Safe to merge *if* the user asked and review threads are clear |
| 8 | At least one check is still pending | Poll / `--watch`. Do **not** treat as failed |
| 1 | A check failed, or `gh` errored | Read the table; fix or stop. Do not retry HTTP 503s |

```bash
# WRONG - exit 8 aborts the chain, so merge never runs
gh pr checks 123 && gh pr merge 123 --squash

# Wait until terminal, then merge (immediate). Pending = retry.
scripts/wait-for-checks.sh 123
gh pr merge 123 --squash

# First-party waiter (same idea; still parse the table, don't trust watch-exit alone)
timeout 900 gh pr checks 123 --watch --fail-fast || true
gh pr checks 123 --json name,bucket,state

# Queue until GitHub is satisfied (required checks + branch protection).
# Does not need a local wait. pr-merge-guard still blocks unresolved threads.
gh pr merge 123 --auto --squash
```

`wait-for-checks.sh` only retries exit 8. Auth errors, usage errors, and
upstream HTTP failures (including 503) are terminal - surface them.

`--watch` exits 0 when *required* checks pass even if optional checks failed.
Read the named check list (`bucket`/`state`) before an immediate merge; a
path-filtered `skipping` is fine, a `fail` is not. Full-pipeline CI watch is
`vd:ship` Step 15 - use that when landing via ship, not a second watcher.

### Merge

```bash
gh pr merge 123                  # Immediate (uses repo merge setting)
gh pr merge 123 --squash         # Immediate squash
gh pr merge 123 --rebase         # Immediate rebase
gh pr merge 123 --merge          # Immediate merge commit
gh pr merge 123 --auto --squash  # Queue: merge only after required checks pass
gh pr merge 123 --delete-branch  # Cleanup after merge
```

`--auto` is the queue path. An immediate `gh pr merge` without `--auto` does
not wait for pending checks - wait first (`wait-for-checks.sh`) or pass
`--auto`. `hooks/pr-merge-guard.py` still refuses merge while review threads
are unresolved; do not bypass it.

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
gh run list --workflow=ci.yml       # Filter by *filename* (see uniqueness below)
gh run view <run-id>                # Details
gh run view <run-id> --log          # Full log
gh run view <run-id> --log-failed   # Only failed steps
gh run watch                        # Watch most recent run live
gh run rerun <run-id>               # Rerun failed run
gh run rerun <run-id> --failed      # Only failed jobs
gh workflow list                    # List workflows
gh workflow run <workflow.yml>      # Manually trigger
```

JSON fields for `gh run list` / `gh run view` include `attempt`, `databaseId`,
`conclusion`, `status`, `workflowName`. The field is **`attempt`**, not
`runAttempt` - `--json runAttempt` fails.

```bash
# WRONG
gh run view "$RUN" --json runAttempt

# RIGHT
gh run view "$RUN" --json attempt,conclusion,status
```

**Unique workflow.** `--workflow=` matches a name *or* a filename. Two
workflows whose names share a prefix (e.g. two review workflows) produce
`could not resolve to a unique workflow`. Disambiguate with
`gh workflow list`, then pass the **filename** (`code-review.yml`), not a
short name.

**Guard command substitutions** before using the value. An empty
`$RUN=$(gh run list …)` plus `gh run view $RUN` dumps usage, not a run.

```bash
# WRONG - empty RUN still calls `gh run view` (or the assignment is skipped
# in a failed && chain and RUN is unset)
gh run list --limit 1 --json databaseId --jq '.[0].databaseId' \
  | xargs gh run view
RUN=$(gh run list --workflow=review --json databaseId --jq '.[0].databaseId') \
  && gh run view "$RUN"

# RIGHT - assign, test, then use. Prefer filename + current branch.
RUN=$(gh run list --workflow=ci.yml \
  --branch "$(git branch --show-current)" \
  --limit 1 --json databaseId --jq '.[0].databaseId // empty')
if [[ -z "$RUN" ]]; then
  echo "no run id yet - checks may still be queued" >&2
  exit 1
fi
gh run view "$RUN" --json attempt,conclusion,status
```

Do not hide these lookups in long `&&` one-liners. One assignment, one
guard, one use.

**`gh --jq` accepts only an expression.** It does not pass external `jq` flags
such as `--arg` through to jq; `gh` parses them as its own arguments. Pipe JSON
to `jq` when the filter needs shell values.

```bash
# WRONG - gh has no --arg formatting flag
gh run list --json databaseId,headSha --jq --arg sha "$SHA" \
  '.[] | select(.headSha == $sha) | .databaseId'

# RIGHT - external jq receives --arg
gh run list --json databaseId,headSha | \
  jq -r --arg sha "$SHA" '.[] | select(.headSha == $sha) | .databaseId'
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
# Create PR then *queue* merge (GitHub waits for required checks)
gh pr create --fill && gh pr merge --auto --squash

# Wait for this PR's checks, then merge immediately (pending = retry)
scripts/wait-for-checks.sh && gh pr merge --squash

# Last failed run, view log (guard the id - empty $RUN dumps usage)
id=$(gh run list --json databaseId,conclusion \
  --jq '.[] | select(.conclusion=="failure") | .databaseId' | head -1)
[[ -n "$id" ]] && gh run view "$id" --log-failed

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
- Multi-line `gh` bodies: `--body-file` / `--body-file -`. Never `--body "$(cat <<`.
- `gh pr checks` exit 8 is pending. Never chain it with `&& gh pr merge`.
- Do not add retry/backoff for GitHub HTTP 503 / GraphQL outages. Surface and stop.
- Guard every `$VAR=$(gh …)` before passing it to another `gh` command.
