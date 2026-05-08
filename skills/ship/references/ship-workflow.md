# Ship Workflow — Detailed Steps

## Step 1: Pre-flight

1. `git branch --show-current`. If on a bare target branch (`main` / `master` / `staging` / `uat` / `dev` / `develop` / `development` / `beta`): **ABORT** — "Ship from a feature branch." Note: `release/x.y.z` is a *valid feature branch for staging mode*, do not abort on it.
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
2. Resolve title and body (rules in `pr-template.md`):
   - Title: branch contains `[A-Z]+-[0-9]+` → `TICKET: <summary>`. Otherwise → `type(scope): <summary>`.
   - Body: prefer `.github/pull_request_template.md` if present, else fallback template.
3. Create / update PR:
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
4. Link issues from Step 2 (`Closes #N` / `Relates to #M`) inside the body.
5. **Output the PR URL** — final user-facing line (unless `--release` is set, in which case Step 13 runs after).

## Step 13: Release (conditional)

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
