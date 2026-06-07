# Ship Workflow — Detailed Steps

## Step 1: Pre-flight

1. `git branch --show-current`. If on a bare target branch (`main` / `master` / `staging` / `uat` / `dev` / `develop` / `development` / `beta`): trigger **on-target recovery** (do NOT abort). Note: `release/x.y.z` is a *valid feature branch for staging mode*, no recovery needed there.

   **On-target recovery flow** (Hard Rule 1):
   - **`--auto`:** auto-create a feature branch and continue silently. No prompt.
     ```bash
     # Infer slug — staged-diff filenames first, then latest commit subject, else timestamp
     SLUG=$(
       git diff --cached --name-only | head -1 | sed 's|.*/||; s|\.[^.]*$||; s|[^a-zA-Z0-9]|-|g; s|--*|-|g; s|^-||; s|-$||' \
       || git log -1 --pretty=%s | sed 's/^[a-z]*[(:][^)]*)*: *//; s|[^a-zA-Z0-9]|-|g; s|--*|-|g; s|^-||; s|-$||' | cut -c1-50 \
       || date +"auto-%Y%m%d-%H%M"
     )
     # Pick prefix by mode: official → feat/, staging → release/, beta → dev/
     case "$MODE" in
       official) PREFIX="feat" ;;
       staging)  PREFIX="release" ;;
       beta)     PREFIX="dev" ;;
     esac
     git checkout -b "$PREFIX/$SLUG"
     ```
     Print one line: `↪ Auto-created branch: <PREFIX>/<SLUG> (from <target>) — continuing.`
   - **Interactive:** `AskUserQuestion` with three options:
     - *Create feature branch, then ship* (Recommended) — same auto-branch logic
     - *Direct push to target* — skip Steps 5/12/13/15/16 (no review/PR/CI), commit + push straight to target. Requires explicit pick.
     - *Abort* — stop the pipeline.
   - **Never** offer direct-push in `--auto`. The flow is binary: branch + continue, or stop on safety violation.
2. Resolve ship mode:
   - `official` → target = default branch (main/master)
   - `staging` → target = staging/uat/release branch
   - `beta` → target = dev/development/beta branch
   - No argument → infer from branch name:
     - `feature/* feat/* hotfix/* bugfix/* fix/*` → official
     - `release/* uat/* staging/*` → staging
     - `dev/* develop/* beta/* experiment/* exp/*` → beta
     - Unclear → `AskUserQuestion`: "Official (main)" / "Staging (release)" / "Beta (dev)"
3. Detect target branch — see `auto-detect.md`.
4. `git status` (no `-uall`). Uncommitted changes are always included in the ship.
5. `git diff <target>...HEAD --stat` and `git log <target>..HEAD --oneline` to summarize what's shipping.
6. If `--dry-run`: print every step's intent, change nothing, stop here.

### Step 1b: Ticket branch guard

If the user request, active task, branch name, or commits reference a ticket
key, preserve that key through branch and PR naming.

Detect common tracker keys:

```bash
CURRENT_BRANCH=$(git branch --show-current)
TICKET=$(
  printf '%s\n' "$USER_REQUEST" "$CURRENT_BRANCH" "$(git log --format=%s -20)" \
    | grep -Eio '[A-Z][A-Z0-9]+-[0-9]+' \
    | head -1 \
    | tr '[:lower:]' '[:upper:]'
)
```

If `TICKET` is non-empty and `CURRENT_BRANCH` does not start with it, rename the
branch before Step 11/12:

```bash
git branch -m "$TICKET"
```

If the old branch was already pushed, push the ticket branch and delete the old
remote only after the replacement PR exists:

```bash
git push -u origin "$TICKET"
git push origin --delete "$CURRENT_BRANCH"
```

Do not create a PR from a generic branch when a ticket is known. The PR title in
Step 12 must use the same ticket key: `TICKET: <past-tense summary>`.

## Step 2: Link issues

1. Search related open issues (keywords from branch + commits):
   ```bash
   BRANCH=$(git branch --show-current)
   KEYWORDS=$(echo "$BRANCH" | sed 's/[^a-zA-Z0-9]/ /g' | tr '[:upper:]' '[:lower:]')
   gh issue list --state open --limit 10 --search "$KEYWORDS"
   ```
2. Pick up issue refs already in commit messages:
   ```bash
   git log <target>..HEAD --oneline | grep -oE '#[0-9]+' | sort -u
   ```
3. **Found:** record issue numbers for Step 12.
4. **None found, official or staging mode:** offer (`AskUserQuestion`) to create a tracking issue. If yes:
   ```bash
   gh issue create --title "<type>: <summary>" --body "$(cat <<'EOF'
   ## Problem Statement
   <infer from diff + commits>

   ## Proposal
   <implementation summary>

   ## Plan
   - [x] Implementation complete
   - [x] Tests passing
   - [ ] Review approved
   - [ ] Merged to <target>
   EOF
   )"
   ```
5. **Beta mode, none found:** skip silently — beta ships don't need issue traceability.

## Step 3: Merge target

```bash
git fetch origin <target> && git merge origin/<target> --no-edit
```

- Already up to date → continue silently.
- Auto-resolvable conflicts (lockfiles, version files): try to resolve.
- Complex conflicts: **STOP**, show them, hand back to user.

## Step 4: Tests

**Skip if** `--skip-tests`.

1. Auto-detect test command (see `auto-detect.md`).
2. Delegate to `tester` subagent — pass detected command. Don't inline run.
3. Read pass/fail from agent result.
   - Any failure → **STOP**, show failures.
   - All pass → log counts, continue.
   - No runner detected → `AskUserQuestion`: skip / provide command.

## Step 5: Pre-landing review

**Skip if** `--skip-review`.

1. `git diff origin/<target>` → diff payload.
2. Delegate to `code-reviewer` subagent. Two-pass model:
   - **Critical:** security holes, injection, race conditions, auth bypass, data loss, broken contract.
   - **Informational:** dead code, magic numbers, missing test coverage, style.
3. Output: `Review: X critical, Y informational`.
4. **For each critical issue:** `AskUserQuestion`:
   - file:line + recommended fix
   - Options: A) Fix now (recommended) — B) Acknowledge and ship — C) False positive
5. If user picks Fix → apply fix, commit fixed files, **re-run Step 4** before continuing.
6. Informational findings → include in PR body, don't block.

## Step 6: Version bump

1. Detect version source (see `auto-detect.md`).
2. None found → skip silently.
3. Bump level:
   - Default (official): patch (`X.Y.Z+1`).
   - Staging mode: rc suffix (`X.Y.Z-rc.N`).
   - Beta mode: prerelease suffix (`X.Y.Z-beta.N`).
   - If diff looks like a major feature or breaking change (new top-level command, removed exported symbol, schema migration) → `AskUserQuestion`: minor or patch.
4. Write the new version into the detected file.

## Step 7: Changelog

1. Look for `CHANGELOG.md`, `CHANGES.md`, `HISTORY.md`. None found → skip silently.
2. Generate entry from `git log <target>..HEAD --oneline` + `git diff <target>...HEAD`.
3. Categorize by conventional-commit prefix:
   - `feat:` → Added
   - `refactor:` / `perf:` → Changed
   - `fix:` → Fixed
   - removals → Removed
4. Insert after header, dated today: `## [X.Y.Z] - YYYY-MM-DD`.
5. **Never ask the user to describe changes.** Infer from diff + commits.

## Step 8: Journal (background)

**Skip if** `--skip-journal` OR mode is `staging`.

Spawn `journal-writer` subagent in **background**:
- Topic: shipped changes (commit summaries + diff stats)
- Include: what shipped, key decisions, gotchas hit during the ship
- Output path: `./docs/journals/` (or wherever the project's journal-writer agent puts them)

Do not wait — continue immediately.

## Step 9: Docs (background)

**Skip if** `--skip-docs` OR mode is `beta` OR mode is `staging`.

Spawn `docs-manager` subagent in **background**:
- Analyzes diff since last release
- Updates relevant files in `./docs/`

Do not wait — continue immediately.

## Step 10: Commit

1. Stage explicitly — never `git add -A` / `git add .`:
   - Files modified in earlier steps (version file from Step 6, changelog from Step 7, fix patches from Step 5).
   - Already-tracked files showing in `git status --short` that the user wants in this ship (review the list first; ask if any look unrelated like `.env.local`, dumps, scratch dirs).
2. **Secret scan** the staged diff (API keys, tokens, AWS creds, private keys, password literals). If hits: **STOP**, warn, suggest `.gitignore`.
3. Compose conventional commit:
   - `type(scope): description` — type inferred from changes (feat/fix/refactor/perf/chore/docs/test).
   - Scope inferred from top-level changed dir (e.g. `auth`, `api`, `ui`).
4. Commit (heredoc to keep formatting clean):
   ```bash
   git commit -m "$(cat <<'EOF'
   type(scope): description

   Brief body when version + changelog were touched in this commit.
   EOF
   )"
   ```

## Step 11: Push

```bash
git push -u origin "$(git branch --show-current)"
```

- Never `--force` / `--force-with-lease` from this skill.
- Rejected push → suggest `git pull --rebase`, retry once. Still rejected → stop and surface to user.

## Step 12: PR

1. Check `gh` is installed:
   ```bash
   command -v gh >/dev/null || echo MISSING
   ```
   Missing → output "Install GitHub CLI (`gh`) to auto-create PRs" and stop after push.
2. Load the PR template rules before resolving title/body:
   - Ship integration: `~/skills/skills/ship/references/pr-template.md`
   - Canonical template: `~/skills/skills/git/references/pr-template.md`
3. Resolve title and body from those loaded rules:
   - Title: branch contains `[A-Z]+-[0-9]+` → `TICKET: <past-tense summary>`. Otherwise → `type(scope): <past-tense summary>`.
   - Body: prefer `.github/pull_request_template.md` if present and fill it without adding, removing, or renaming sections. Otherwise fill the canonical fallback (3 labelled bullets — Why / What / Risks — plus an italic verification stripe). Never use ad hoc `Summary`, `Changes`, `Validation`, or mixed template bodies.
4. Create / update PR:
   ```bash
   gh pr create --base <target> --title "<title>" --body "$(cat <<'EOF'
   <body>
   EOF
   )"
   # PR already exists for this branch:
   gh pr edit --title "<title>" --body "$(cat <<'EOF'
   <body>
   EOF
   )"
   ```
5. Inline issue refs from Step 2 in the template's context/why area (`Closes #N` / `Relates to #M`) — no separate Linked-Issues section.
6. Re-read the created/updated PR body and verify it matches the selected repo template or canonical fallback before continuing.
7. **Output the PR URL** — final user-facing line (unless Steps 13–16 run after).

## Step 13: PR review comments

**Skip if** `--skip-pr-comments`.

Handles GitHub-side feedback that landed on the PR: unresolved review threads
(line comments), reviews left in `CHANGES_REQUESTED` state, substantive
`COMMENTED` reviews from humans/bots, and top-level PR comments. Fresh PR with
zero comments → skip silently.

1. Fetch review threads, reviews, and top-level PR comments in one GraphQL call:
   ```bash
   OWNER_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
   OWNER=${OWNER_REPO%/*}; REPO=${OWNER_REPO#*/}
   gh api graphql -f query='
     query($owner:String!,$repo:String!,$pr:Int!){
       repository(owner:$owner,name:$repo){
         pullRequest(number:$pr){
           reviewDecision
           comments(first:50){nodes{author{login} body url createdAt}}
           reviews(last:50){nodes{state author{login} body url submittedAt}}
           reviewThreads(first:50){nodes{
             id isResolved isOutdated
             comments(first:10){nodes{
               id path line body author{login} url
             }}
           }}
         }
       }
     }' -F owner="$OWNER" -F repo="$REPO" -F pr="$PR_NUMBER" \
     > /tmp/ship-pr-comments.json
   ```
2. Parse with `jq`:
   - Unresolved threads: `.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved==false and .isOutdated==false)`
   - `CHANGES_REQUESTED` reviews: `.data.repository.pullRequest.reviews.nodes[] | select(.state=="CHANGES_REQUESTED")`
   - Substantive `COMMENTED` reviews: `.data.repository.pullRequest.reviews.nodes[] | select(.state=="COMMENTED" and (.body|length)>0)`
   - Top-level comments: `.data.repository.pullRequest.comments.nodes[]`
3. Triage each item before taking action:
   - **Actionable:** specific bug, failing scenario, data-loss/security risk, broken contract, or concrete improvement with clear benefit.
   - **Informational:** summary, style preference, non-blocking suggestion, bot deprecation notice, or FYI.
   - **Noise/false positive:** incorrect claim, already handled, stale/outdated, or unrelated.
   Do not blindly apply bot suggestions. Verify against the code and tests first.
   For each substantive suggestion, answer these before editing:
   - **Is the risk real under the codebase contract?** Check source of truth: config schema, type definitions, route docs, tests, env loading, database constraints, feature flags, and repo rules.
   - **Is the suggested patch the right fix?** Prefer the smallest root-cause fix that matches local patterns. It is valid to reject a literal suggestion when a better fix exists (for example, fail fast in config validation instead of silently defaulting a bad runtime value).
   - **What evidence proves it?** Add or update tests when the behavior can regress; rerun the narrowest relevant checks plus any ship-level checks required by the repo.
4. **Nothing actionable/unresolved** → output `PR comments: 0 actionable`, continue.
5. **For each actionable unresolved thread**, run `AskUserQuestion`:
   - Show: `path:line` · author · comment body (truncate to 300 chars, link to full URL)
   - Options:
     - **A) Fix now** (recommended for actionable comments) — apply the verified fix (not necessarily the literal suggestion), stage, **re-run Step 4 (tests)**, then on green: commit + push (`type(scope): address review feedback`), reply to thread with the commit SHA plus the codebase rationale, then resolve the thread via `resolveReviewThread` GraphQL mutation.
     - **B) Reply only** — collect a 1-2 sentence rationale grounded in codebase evidence, post via `gh api`, and leave thread unresolved unless the comment is clearly false/stale.
     - **C) Mark resolved** — call `resolveReviewThread` mutation; no code change.
     - **D) Skip** — leave as-is, continue.
6. **For actionable review bodies or top-level comments not tied to a thread**, prompt once:
   - fix now (commit + push, then reply with commit SHA)
   - reply only with rationale
   - skip as non-blocking
   For bot comments, prefer reply-only for false positives/noise and fix-now for verified bugs.
7. **For `CHANGES_REQUESTED` reviews not tied to a thread**, prompt once: address (commit + push + request re-review via `gh pr edit --add-reviewer @<author>`) / acknowledge in PR comment / skip.
8. After all loops, refetch state. If everything is resolved, replied to, or skipped: continue to Step 14. Output: `PR comments: N addressed, M replied, K skipped`.
9. If any fixes were committed and pushed in this step, Step 15 (CI watch) will pick up the new commit's checks automatically.

### Reply style for reviewed comments

When replying to a handled thread, write a short reasoned note, not just "fixed":

```text
Handled in <short-sha> by <specific change>. <Why this matches the codebase contract / why a different root-cause fix was chosen>.
```

Good examples:
- `Handled in <short-sha> by validating <CONFIG_KEY> as non-empty at load time instead of falling back silently. This keeps misconfiguration fail-fast and prevents an invalid runtime value.`
- `Handled in <short-sha> with a polling helper, replacing a fixed sleep in the async assertion.`
- `Not applying as suggested: <schema/type/test> already guarantees <condition>. Added <test/comment> to make the contract explicit.`

### `--auto` behavior for Step 13

`--auto` does **not** auto-fix code based on review comments — too risky, the reviewer's intent isn't always machine-parseable. Under `--auto`:
- Unresolved comment with a clearly suggested edit (GitHub "suggestion" block) → first validate it against codebase contracts. If the suggestion is correct and there is no better local-pattern fix, apply it, commit, reply with commit SHA + rationale, and resolve the thread. If the comment is valid but a better root-cause fix exists, apply that instead and explain why in the reply. If validity is uncertain, stop and prompt.
- Anything else → **STOP** and prompt (same as interactive mode). Treat as a critical gate.

## Step 14: Release (conditional)

**Run only if** `--release` flag is set.

1. Detect auto-release tooling (see `auto-detect.md` → "Auto-release tooling"). If detected:
   - **Skip manual tagging.** Output: `Auto-release detected (<tool>). Tag will be created by CI.`
   - Done. The CI workflow / release tool handles tag + GitHub release on merge.
2. If no auto-release tooling:
   - `AskUserQuestion` for bump level: `major` / `minor` / `patch`.
   - Compute new version from last tag (`git describe --tags --abbrev=0`):
     - `official` → `vX.Y.Z` (stable)
     - `staging` → `vX.Y.Z-rc.N` (increment N if rc tag already exists for this version)
     - `beta` → `vX.Y.Z-beta.N` (increment N if beta tag already exists)
   - Tag and push:
     ```bash
     git tag -a "<TAG>" -m "Release <TAG>"
     git push origin "<TAG>"
     ```
   - Create GitHub release:
     ```bash
     gh release create "<TAG>" \
       --title "<TAG>" \
       --notes-from-tag \
       $( [ "<mode>" != "official" ] && echo "--prerelease" )
     ```
3. Output release URL: `gh release view <TAG> --json url -q .url`.

## Step 15: CI watch

Runs after PR creation in **every** mode. Distinguishes pass / fail / pending so the next step (auto-merge or hand-off) can act correctly.

1. If the repo has no CI configured (no checks attached to the PR), skip silently.
   ```bash
   COUNT=$(gh pr checks "$PR_NUMBER" --json state -q 'length' 2>/dev/null || echo 0)
   [ "$COUNT" -eq 0 ] && echo "no CI checks — skipping" && exit 0
   ```
2. Wait for checks to settle (cap at 15 min so the skill doesn't block forever):
   ```bash
   timeout 900 gh pr checks "$PR_NUMBER" --watch --fail-fast || true
   STATE=$(gh pr checks "$PR_NUMBER" --json state -q '[.[].state] | unique | join(",")')
   ```
3. Branch on `$STATE`:
   - **All `SUCCESS` / `COMPLETED+SUCCESS`** → output `CI: green`, refresh the selected PR template with the latest verification status. For canonical fallback bodies, update the italic stripe (`_Tests: ✓ N · …_`). For repo-template bodies, update the appropriate checklist or notes field without changing section names. Continue to Step 16.
   - **Any `FAILURE` / `CANCELLED` / `TIMED_OUT`** → **STOP**. `AskUserQuestion` (regardless of `--auto`):
     - `Investigate failure` (recommended) — print failing checks via `gh pr checks --json name,state,link -q '.[]|select(.state!="SUCCESS")'`, exit so user can fix
     - `Merge anyway` — proceed to Step 16 noting CI was red
     - `Abort` — leave PR open, exit
   - **Still pending after timeout** → in `--auto` mode rely on `gh pr merge --auto` (Step 16 queues until green); in interactive mode print "CI still running" with the PR URL and exit cleanly.
4. CI failures are **never** silently bypassed by `--auto` — same prompt fires.

## Step 16: Auto-merge (conditional)

**Run only if** `--auto` flag is set AND Step 15 reported green (or user explicitly chose "Merge anyway").

1. Detect the repo's preferred merge strategy and queue / immediate-merge:
   ```bash
   STRATEGY=$(gh repo view --json mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed \
     -q 'if .squashMergeAllowed then "--squash" elif .rebaseMergeAllowed then "--rebase" else "--merge" end')
   gh pr merge "$PR_NUMBER" --auto $STRATEGY --delete-branch
   ```
2. If `gh pr merge --auto` is rejected (auto-merge disabled at repo level):
   - Re-check mergeability: `gh pr view "$PR_NUMBER" --json mergeable -q .mergeable`.
   - `MERGEABLE` → immediate merge: `gh pr merge "$PR_NUMBER" $STRATEGY --delete-branch`.
   - Otherwise → print the PR URL and exit cleanly; user merges manually.
3. Output: `Auto-merge queued: <PR URL>` (or `Merged: <PR URL>` for immediate).

## `--auto` gate behavior

When `--auto` is set, replace each `AskUserQuestion` with the listed default. Critical-issue and ambiguity gates remain blocking.

| Gate | Default under `--auto` | Still blocks? |
|------|------------------------|---------------|
| Mode unclear from branch name | — | **Yes**, stop |
| Issue creation when none found | Skip | No |
| No test runner detected | Skip tests, warn | No |
| Critical review issue | — | **Yes**, stop per issue |
| Unresolved PR review comment | Apply GitHub suggestion blocks; otherwise stop per comment | **Yes** (non-suggestion) |
| Major/minor/patch bump prompt | Patch (or minor if branch starts with `feat/` or commits include `feat:`) | No |
| Auto-release with manual fallback | Patch bump, tag automatically | No |
| Push rejected | — | **Yes**, stop |
| Secret-scan hit | — | **Yes**, stop |
| CI failure on PR | — | **Yes**, prompt (investigate / merge anyway / abort) |
| CI still pending after 15min timeout | Queue via `gh pr merge --auto` | No |
