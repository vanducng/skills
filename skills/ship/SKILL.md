---
name: ship
description: "Ship a feature branch end-to-end: merge target → test → review → version/changelog → commit → push → PR. Use when ready to land a branch on main/master (official) or dev/beta (beta). Stops only on test failures, critical review issues, or major version bumps."
license: MIT
argument-hint: "[official|staging|beta] [--auto] [--release] [--skip-tests] [--skip-review] [--skip-pr-comments] [--skip-journal] [--skip-docs] [--dry-run]"
metadata:
  author: vanducng
  version: "1.4.0"
---

# Ship

## What this skill is — and isn't

| Skill | Question it answers | Output |
|---|---|---|
| `vd:cook` | "Execute the plan." | Code, tests, plan status |
| **`vd:ship`** | **"The branch is ready — land it."** | **Merged target, version bump, PR URL** |

Ship **lands** a branch. It does not implement features and does not redesign on the fly. If tests fail or review surfaces a real bug, **stop** and kick back to `vd:cook` — don't paper over issues to keep the pipeline moving.

## Ship modes

| Mode | Target branch (auto-detected) | Use for |
|------|-------------------------------|---------|
| `official` | `main` / `master` | Production code merge |
| `staging` | `staging` / `uat` / `release/x.y.z` | Pre-prod, QA validation |
| `beta` | `dev` / `development` / `beta` | Active dev / preview |

Add `--release` to any mode to also cut a GitHub release. Tag style adapts to the mode:

| Mode + `--release` | Tag | GitHub release |
|--------------------|-----|----------------|
| `official --release` | `vX.Y.Z` | Stable (latest) |
| `staging --release` | `vX.Y.Z-rc.N` | Prerelease |
| `beta --release` | `vX.Y.Z-beta.N` | Prerelease |

If an auto-release tool is detected (`goreleaser`, `release-please`, `semantic-release`, `changesets`), Step 13 skips the manual tag and lets CI cut it. Otherwise, the user is asked for the bump level.

## Arguments

| Flag | Effect |
|------|--------|
| `official` | Target default branch (main/master). Full pipeline incl. docs + journal |
| `staging` | Target staging/uat/release branch. Skip journal + docs |
| `beta` | Target dev/development/beta branch. Skip docs update |
| `--release` | Cut a GitHub release at the end. Tag style follows mode (stable for official, rc/beta prerelease otherwise). Auto-release tool detected → skip manual tag |
| `--auto` | Fully autonomous — answer every prompt with the recommended default, watch CI, then queue an auto-merge on green. Still stops on critical review issues, secret leaks, test failures, merge conflicts, **and red CI** |
| (none) | Auto-detect mode from branch name (`feature/*` → official, `release/*` / `uat/*` → staging, `dev/*` → beta) |
| `--skip-tests` | Skip test step (use only when tests already passed in this session) |
| `--skip-review` | Skip pre-landing review (local AI review only — does NOT skip PR-comment handling) |
| `--skip-pr-comments` | Skip Step 13 and Step 15b PR-comment gates. Use only when explicitly requested; default ship always fetches PR feedback before merge. |
| `--skip-journal` | Skip journal entry |
| `--skip-docs` | Skip docs update |
| `--dry-run` | Print what would happen at each step, change nothing |

## Hard rules

1. **Never ship from the target branch without a feature branch.** If on `main` / `master` / `dev` / `staging` / `uat` with changes to ship:
   - **`--auto`:** auto-create `feat/<slug>` from current HEAD silently, move pending changes there, continue the pipeline. No prompt. The slug is inferred from (in order of preference) the staged-diff filenames, the latest commit subject, or `auto-{YYYYMMDD-HHMM}` as last resort. The resulting branch still goes through review/PR/CI like any other.
   - **Interactive:** prompt the user with three choices — *create feature branch* (recommended), *direct push to target* (skips review/PR/CI; requires explicit confirm), *abort*.
   - **Never** do a direct push to the target branch in `--auto`. Direct push is interactive-only and requires the user to pick it themselves.
2. **Never force push.** Plain `git push` only. If rejected → `git pull --rebase`, retry once, then stop.
3. **Never skip failing tests.** A red test stops the pipeline. Fix it (kick back to `vd:cook`) or pass `--skip-tests` deliberately.
4. **Never bypass critical review issues silently.** Each critical finding gets an `AskUserQuestion`: fix now / acknowledge / false-positive.
4b. **Never silently ignore PR feedback.** After the PR exists, always fetch unresolved review threads, `CHANGES_REQUESTED` reviews, `COMMENTED` reviews from humans/bots, and top-level PR comments before merge. Triage each item for validity/actionability before changing code. Validate every suggestion against codebase contracts, types, config schemas, tests, and local rules; if the comment is valid but the suggested patch is not the best fix, apply the better root-cause fix and explain that in the PR reply. Reply to and resolve handled threads, re-run verification after fixes, then re-fetch until there are zero unresolved actionable comments. Same blocking model as critical review issues.
5. **Auto-decide everything else.** Patch-version bumps, changelog content, commit message, PR body — infer from diff and commits. Do not pause to ask.
6. **Skip silently when a step doesn't apply.** No version file → skip version bump. No CHANGELOG → skip changelog. No test runner detected → ask once, then skip.
7. **No secrets in commits.** Scan staged diff for API keys / tokens / passwords before commit. If found: stop, warn, suggest `.gitignore`.
8. **`--auto` has a safety floor.** Even in auto mode, stop on: critical review issues, **unresolved PR review comments**, secret-scan hits, test failures, merge conflicts, push rejections, ambiguous mode (no branch-name match). Auto suppresses *judgement-call* prompts (issue creation, version bump level, no-test-runner, journal/docs skip) **and recoverable preflight conditions** (on-target-branch → auto-create feature branch per Rule 1). Auto NEVER suppresses safety violations or direct-push-to-target.
9. **Ticket branch/title invariant.** If the work is tied to Jira, Linear,
   Shortcut, GitHub issue, or another tracker key, the branch must start with
   the ticket key before Step 12 creates/updates the PR, and the PR title must
   be `KEY-123: <past-tense description>`. If the current branch is a generic
   slug (`feat/foo`, `2ndphone`, etc.), rename it before push/PR; do not open a
   PR and fix the name later.
10. **PR template invariant.** Step 12 must load `references/pr-template.md`
   and the canonical `~/skills/skills/git/references/pr-template.md` before any
   `gh pr create` or `gh pr edit`. If the repo has a PR template, fill that
   template only. Otherwise use the canonical fallback body. Do not invent
   `Summary` / `Validation` / ad hoc PR bodies.
11. **CI green is a merge precondition.** Step 15 watches CI in every mode. Never
   merge — or report the ship as done — while checks are **failing or still
   pending**. The only ways past a non-green state are an explicit user
   *"Merge anyway"*, or `--auto`'s `gh pr merge --auto` (which queues and merges
   **only when CI turns green**). When falling back to an immediate merge (repo
   auto-merge disabled), re-confirm CI state is `SUCCESS` **first** — GitHub's
   `mergeable` field reports merge *conflicts*, not CI status, so it is not a
   substitute for a green-CI check.
   - **Read the named check list, never the watcher exit code.** `gh pr checks --watch`
     exits **0 even when non-required checks fail** (only branch-protection-required
     checks gate its exit) — treating that 0 as "green" merges a red PR. Always parse
     the per-check states (`gh pr checks <n>` → look for any `fail`) before merging.
     A path-filtered `skipping` is fine; a `fail` is not, required or not. (This exact
     trap merged a PR whose whole test matrix was red.)
   - **CI green ≠ comments addressed.** A passing code-review-bot check (e.g.
     `review/code-review`) means the bot *ran*, not that its findings are resolved. Bot
     reviewers post inline comments **as a CI job**, so they land *during* Step 15 —
     after Step 13 already looked and found nothing. So **re-run Step 13's review-thread
     fetch after CI is green and before merge** (Step 15b), and block on any thread that is
     `isResolved==false && isOutdated==false` and actionable (human or bot). Triage,
     fix the valid ones (re-run Step 4 after fixes), reply + resolve each, then merge.
     **0 unresolved actionable threads is a merge precondition, alongside green CI** — a
     safety floor `--auto` does not suppress. (This exact trap merged goclaw #304 with 9
     unresolved bot comments, real bugs included.)
12. **Ship acts on the *current* repo (cwd).** Before any `git`/`gh` step, confirm
   the branch you mean to land lives in the cwd repo. When landing a sibling repo's
   branch while a different repo is the working dir (e.g. shipping a skills repo mid-task
   in a product repo), do **not** invoke the pipeline blindly — it targets cwd and can
   push/PR the wrong repo. Scope every command with `git -C <repo>` / `gh -R <owner/repo>`,
   or `cd` there first.
13. **Auto-release repos** (release-please / semantic-release / changesets): do **not**
   hand-edit `CHANGELOG.md` or the version file — the conventional-commit message drives
   them and CI cuts the version. Detect the tooling (Step 14) and skip the manual bump.
14. **Only `feat`/`fix`/breaking cut a release** under release-please. A branch whose
   commits are all non-releasing types (`refactor`, `docs`, `chore`, `perf`, `test`,
   `style`, `ci`, `build`) lands on main but **no version is cut** — these can't be made
   release-triggering by config. So when a *substantive* change ships under one of those
   types and should be released, either: (a) title the headline commit `feat:`/`fix:`, or
   (b) force it after merge with an empty commit `git commit --allow-empty -m "chore: release X.Y.Z" -m "Release-As: X.Y.Z"` pushed to the release branch. In `--auto`, if the
   whole branch is non-releasing and substantive, surface this and offer the `Release-As` force.

## Pipeline

```
1.  Pre-flight    → branch check, mode detect, status, diff/log summary
2.  Link issues   → find related GH issues; optionally create one if none
3.  Merge target  → fetch + merge origin/<target>
4.  Tests         → delegate to tester subagent
5.  Review        → delegate to code-reviewer subagent (two-pass)
6.  Version bump  → auto-detect version file, patch by default
7.  Changelog     → auto-generate from commits + diff
8.  Journal       → journal-writer subagent (background)
9.  Docs          → docs-manager subagent (background, official only)
10. Commit        → conventional commit, secret scan
11. Push          → git push -u origin <branch>
12. PR            → gh pr create/edit using repo template or canonical fallback
13. PR comments   → fetch review threads + human/bot reviews + top-level comments; triage, then fix/reply/resolve valid feedback (re-run Step 4 after any fix); after fixing, **re-trigger each bot's re-review** (`@codex review` / `@coderabbitai review` / `/gemini review`; re-run local `ocr`/`miucr`) and loop until zero unresolved actionable threads — see `references/bot-reviewers.md`
14. Release       → `--release` only: detect auto-release tool; tag + push if manual
15. CI watch      → wait for PR checks; on failure prompt user (every mode)
15b. Re-check comments → after CI green, RE-RUN Step 13: code-review bots post inline comments as a CI job, so they appear only now. Block merge on any unresolved actionable thread (Rule 11). Not suppressed by `--auto`.
16. Auto-merge    → `--auto` only: `gh pr merge --auto` once Step 15 green AND 15b clear
```

> **Ordering matters.** Step 13 runs once at PR creation (catches pre-existing human reviews), but a code-review **bot** reviews *as CI* — its comments land during Step 15, after Step 13. **Step 15b re-fetches** so bot findings can't slip to merge. Without it, a green `review/code-review` check reads as "approved" when it only means "the bot finished."

**Detailed steps:** see `references/ship-workflow.md`
**Auto-detection logic:** see `references/auto-detect.md`
**PR body template:** see `references/pr-template.md`
**Bot reviewers (inline reply + per-bot re-review triggers):** see `references/bot-reviewers.md`

## Token efficiency

- Steps 4–5 (tests, review): delegate to subagents — don't inline output in main context.
- Steps 8–9 (journal, docs): run in background — don't block the pipeline on them.
- Step 2 (issues): one `gh issue list` call, parse locally — don't loop API calls.
- Skip steps via flags when work already done in this session.
- Staging mode auto-skips journal (Step 8) and docs (Step 9).
- Beta mode auto-skips docs (Step 9).
- Step 13 (PR comments) always performs one GraphQL fetch after the PR exists. If there are no unresolved review threads, `CHANGES_REQUESTED` reviews, substantive `COMMENTED` reviews from humans/bots, or top-level PR comments, report `PR comments: 0 actionable` and continue. Skipped entirely only with `--skip-pr-comments`.
- Step 14 runs only with `--release`. If auto-release tooling detected, it's a no-op (CI handles tagging).
- Step 15 (CI watch) always runs after PR creation. CI failure prompts the user even in `--auto`.
- Step 15b (re-check comments) always runs after CI green when any check is a code-review bot (e.g. `review/code-review`) — those post inline comments as a CI job, so they only exist post-CI. Re-runs Step 13's fetch; one GraphQL call. Blocks merge on unresolved actionable threads even in `--auto` (not suppressible — safety floor, Rule 11).
- Step 16 runs only with `--auto`, only after Step 15 reports green **and** Step 15b is clear (or user explicitly opted to merge anyway). Uses `gh pr merge --auto`, which respects branch protection — queues the merge; never bypasses.

## Output

```
✓ Pre-flight: release/1.4.0, 5 commits, +200/-50 (mode: staging, target: staging)
✓ Issues: linked #42
✓ Merged: origin/main (already up to date)
✓ Tests: 42 passed, 0 failed
✓ Review: 0 critical, 2 informational
✓ Version: 1.3.4 → 1.4.0-rc.1
✓ Changelog: updated
✓ Committed: chore(release): 1.4.0-rc.1
✓ Pushed: origin/release/1.4.0
✓ PR: https://github.com/org/repo/pull/123 → staging
✓ PR comments: 0 actionable
- Journal: skipped (staging)
- Docs:    skipped (staging)
```

## Workflow position

**Typically follows:** `vd:cook` (cook implements, ship lands)
**Often pairs with:** `code-reviewer` agent (review before ship), `tester` agent (final test run)
