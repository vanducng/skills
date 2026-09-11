---
name: ship
description: "Ship a feature branch end-to-end: merge target → test → review → version/changelog → commit → push → PR, then drive CI green and hand off the PR. Use after `vd:cook` when the branch is implemented and tested, ready to land on main/master (official), staging/uat (staging), or dev/beta (beta). Merge is opt-in - a bare ship stops at a green PR; it merges only with --auto or --merge. Stops on test failures, critical review issues, or major version bumps."
license: MIT
argument-hint: "[official|staging|beta] [--auto] [--merge] [--release] [--skip-tests] [--skip-review] [--skip-pr-comments] [--skip-journal] [--skip-docs] [--dry-run]"
metadata:
  author: vanducng
  version: "1.4.0"
---

# Ship

Ship **prepares** a branch to land: merge target, test, review, version, PR, then drives CI to green and clears review comments - and by default **hands the PR back to you unmerged**. It does not implement features or redesign on the fly; failures kick back to `vd:cook`.

## Arguments

| Flag | Effect |
|------|--------|
| `official` | Target default branch (main/master). Full pipeline incl. docs + journal |
| `staging` | Target staging/uat/release branch. Skip journal + docs |
| `beta` | Target dev/development/beta branch. Skip docs update |
| `--release` | Cut a GitHub release at the end. Tag style follows mode (stable for official, rc/beta prerelease otherwise). Auto-release tool detected (`goreleaser`, `release-please`, `semantic-release`, `changesets`) → Step 14 skips the manual tag and lets CI cut it |
| `--auto` | Fully autonomous - answer every prompt with the recommended default, watch CI, then queue an auto-merge on green (implies merge). Still stops on critical review issues, secret leaks, test failures, merge conflicts, **and red CI** |
| `--merge` | Merge once all gates pass (green CI + 0 unresolved comments), without full `--auto` autonomy. Use to land a branch you're shepherding interactively. Without `--auto` or `--merge`, ship never merges. |
| (none) | Auto-detect mode from branch name (`feature/*` → official, `release/*` / `uat/*` → staging, `dev/*` → beta). **Does not merge** - stops at a green PR (Hard rule 0) |
| `--skip-tests` | Skip test step (use only when tests already passed in this session) |
| `--skip-review` | Skip pre-landing review (local AI review only - does NOT skip PR-comment handling) |
| `--skip-pr-comments` | Skip Step 13 and Step 15b PR-comment gates. Use only when explicitly requested; default ship always fetches PR feedback before merge. |
| `--skip-journal` | Skip journal entry |
| `--skip-docs` | Skip docs update |
| `--dry-run` | Print what would happen at each step, change nothing |

## Hard rules

> **Runtime note.** `AskUserQuestion` and the named subagents (`tester`, `code-reviewer`, `journal-writer`, `docs-manager`) are Claude Code mechanics - on Codex or any runtime without them, ask the same question in plain text and run that step's work inline (sequentially) instead of delegating. Applies throughout this skill and `references/ship-workflow.md`.

0. **Merge is opt-in - a bare ship never merges.** A plain `vd:ship` / "ship to main as pr" **stops after the PR is green and comments are clear**; it does **not** merge. Merge only when `--auto` is set, `--merge` is set, or the user explicitly says "merge" / "land it" / "merge anyway" in *this* request. "Ship to main as a PR" is a request to *open and green* the PR, not to merge it. Do not treat CI-green + zero comments as license to merge - that gate makes merge *safe*, not *requested*.

1. **Never ship from the target branch without a feature branch.** If on `main` / `master` / `dev` / `staging` / `uat` with changes to ship:
   - **`--auto`:** auto-create `feat/<slug>` from current HEAD silently, move pending changes there, continue the pipeline. No prompt (slug inference in Step 1). The resulting branch still goes through review/PR/CI like any other.
   - **Interactive:** prompt the user with three choices - *create feature branch* (recommended), *direct push to target* (skips review/PR/CI; requires explicit confirm), *abort*.
   - **Never** do a direct push to the target branch in `--auto`. Direct push is interactive-only and requires the user to pick it themselves.
2. **Never force push.** Plain `git push` only. If rejected → `git pull --rebase`, retry once, then stop.
3. **Never skip failing tests.** A red test stops the pipeline. Fix it (kick back to `vd:cook`) or pass `--skip-tests` deliberately.
4. **Never bypass critical review issues silently.** Each critical finding gets an `AskUserQuestion`: fix now / acknowledge / false-positive.
4b. **Never silently ignore PR feedback - always reply inline, valid or not.** Fetch review threads, `CHANGES_REQUESTED` reviews, substantive `COMMENTED` reviews from humans/bots, and top-level PR comments. Triage each item for validity/actionability before changing code, validating every suggestion against codebase contracts, types, config schemas, tests, and local rules. Then **every** finding-bearing comment gets an inline reply before its thread is resolved - no exceptions, including bot comments and ones you disagree with:
   - **Valid** → apply the best root-cause fix (not necessarily the literal suggestion), reply inline **naming the exact fix commit SHA** (e.g. "Fixed in `a1b2c3d`.") and what changed. Re-run Step 4 verification after the fix.
   - **Invalid / false-positive / won't-fix** → reply inline with the concrete rationale (why it's wrong, or why it's out of scope + where it's tracked). Do not resolve with an empty/one-word reply.
   - **Deferred / out-of-scope** (valid but intentionally not in this PR) → reply inline saying so and link the follow-up (ticket/PR/issue), then resolve.
   Resolve each thread only after its inline reply exists; repair any already-resolved thread that lacks one.
5. **Auto-decide everything else.** Patch-version bumps, changelog content, commit message, PR body - infer from diff and commits. Do not pause to ask.
6. **Skip silently when a step doesn't apply.** No version file → skip version bump. No CHANGELOG → skip changelog. No test runner detected → ask once, then skip.
7. **No secrets in commits.** Scan staged diff for API keys / tokens / passwords before commit. If found: stop, warn, suggest `.gitignore`.
7b. **Portability scan on shareable content.** When the staged diff touches reusable/publishable content (`skills/**`, `hooks/**`, `agents/**`, docs, examples, fixtures), grep the diff before commit for:
   - **Absolute home paths** - `/Users/<name>/`, `/home/<name>/`. Replace with `$HOME`, `~`, or a placeholder (`<repo-root>`, `<org>/<repo>`). A path is only allowed literal when it's a real fixed system path (`/etc/hosts`, `/usr/local/bin`).
   - **Private identifiers** - employer/org names, internal repo or host names, customer names, connection names, ticket contents, personal emails. Replace with `<org>/<repo>`, `<connection>`, `<internal-host>`. Discover the real values at runtime from the repo/env instead of hardcoding.
   - **Stale model ids** - model names pinned in prose/examples that no longer match what the tool actually uses. Verify against the source of truth (`~/.codex/config.toml`, the CLI binary's own default, provider docs) before changing one; a doc that correctly records an older default the tool still writes is **not** stale.
   Findings block the commit the same way Rule 7 does. Fix, or state out loud why the literal is required.
8. **`--auto` has a safety floor.** Even in auto mode, stop on: critical review issues, **unresolved PR review comments**, secret-scan hits, test failures, merge conflicts, push rejections, ambiguous mode (no branch-name match). Auto suppresses *judgement-call* prompts (issue creation, version bump level, no-test-runner, journal/docs skip) **and recoverable preflight conditions** (on-target-branch → auto-create feature branch per Rule 1). Auto NEVER suppresses safety violations or direct-push-to-target.
9. **Ticket branch/title invariant.** If the work is tied to Jira, Linear,
   Shortcut, GitHub issue, or another tracker key, the branch must start with
   the ticket key before Step 12 creates/updates the PR, and the PR title must
   be `KEY-123: <past-tense description>`. If the current branch is a generic
   slug (`feat/foo`, `2ndphone`, etc.), rename it before push/PR; do not open a
   PR and fix the name later.
10. **PR template invariant.** Step 12 must load `references/pr-template.md`
   and the canonical `../git/references/pr-template.md` (sibling git skill) before any
   `gh pr create` or `gh pr edit`. If the repo has a PR template, fill that
   template only. Otherwise use the canonical fallback body. Do not invent
   `Summary` / `Validation` / ad hoc PR bodies. Run a `vd:unslop` pass over
   title and body before posting - no AI tells, no em dashes.
11. **CI green is a merge precondition.** Step 15 watches CI in every mode. Never
   merge - or report the ship as done - while checks are **failing or still
   pending**. The only ways past a non-green state are an explicit user
   *"Merge anyway"*, or `--auto`'s `gh pr merge --auto` (which queues and merges
   **only when CI turns green**). When falling back to an immediate merge (repo
   auto-merge disabled), re-confirm CI state is `SUCCESS` **first** - GitHub's
   `mergeable` field reports merge *conflicts*, not CI status, so it is not a
   substitute for a green-CI check.
   - **Read the named check list, never the watcher exit code.** `gh pr checks --watch`
     exits **0 even when non-required checks fail** (only branch-protection-required
     checks gate its exit) - treating that 0 as "green" merges a red PR. Always parse
     the per-check states (`gh pr checks <n>` → look for any `fail`) before merging.
     A path-filtered `skipping` is fine; a `fail` is not, required or not. (This exact
     trap merged a PR whose whole test matrix was red.)
   - **A red check must be *addressed*, not just reported.** On any `fail`, open the failing
     job's log (`gh run view --log-failed` / the job URL), diagnose the root cause, fix it
     (kick back to `vd:cook`/`vd:fix` if non-trivial), commit + push, and let Step 15 re-watch
     the new run. Never leave a ship "done" with red CI. The only non-fix exits are an explicit
     user *"Merge anyway"* or a deliberate `--skip-tests`/documented flake - both stated out loud.
   - **CI green ≠ comments addressed.** A passing code-review-bot check (e.g.
     `review/code-review`) means the bot *ran*, not that its findings are resolved. Bot
     reviewers post inline comments minutes after the PR opens - as a CI job, or via their
     own webhook independent of CI - so they land *after* Step 13 already looked and found
     nothing. So **Step 15b re-runs Step 13's fetch before merge or handoff, whatever
     state CI is in**, and blocks on any thread that is
     `isResolved==false && isOutdated==false` and actionable (human or bot). **0 unresolved
     actionable threads is a merge precondition, alongside green CI** - a safety floor
     `--auto` does not suppress.
12. **Ship acts on the *current* repo (cwd).** The pipeline targets cwd and can
   push/PR the wrong repo when the branch lives in a sibling repo. Confirm before any
   `git`/`gh` step, and scope every command with `git -C <repo>` / `gh -R <owner/repo>`
   or `cd` there first.
13. **Auto-release repos** (release-please / semantic-release / changesets): do **not**
   hand-edit `CHANGELOG.md` or the version file - the conventional-commit message drives
   them and CI cuts the version. Detect the tooling (Step 14) and skip the manual bump.
14. **Only `feat`/`fix`/breaking cut a release** under release-please. A branch whose
   commits are all non-releasing types (`refactor`, `docs`, `chore`, `perf`, `test`,
   `style`, `ci`, `build`) lands on main but **no version is cut** - these can't be made
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
10. Commit        → conventional commit, secret scan + portability scan (Rules 7 / 7b)
11. Push          → git push -u origin <branch>
12. PR            → gh pr create/edit using repo template or canonical fallback
13. PR comments   → fetch review threads + human/bot reviews + top-level comments; triage, fix/reply/resolve (re-run Step 4 after any fix); repair silently-resolved threads; re-trigger bot re-reviews and loop until 0 unresolved - see `references/bot-reviewers.md`
14. Release       → `--release` only: detect auto-release tool; tag + push if manual
15. CI watch      → wait for PR checks; on failure prompt user (every mode)
15b. Re-check comments → RE-RUN Step 13 before any handoff or merge, **whatever CI did** (green, red, still pending, never triggered). Review bots post inline comments on their own schedule - typically 1-5 min after the PR opens - so Step 13's fetch almost always precedes them. Block merge on any unresolved actionable thread (Rule 11). Not suppressed by `--auto`.
16. Merge         → **only** with `--auto`/`--merge` (or an explicit "merge anyway"): `gh pr merge` once Step 15 green AND 15b clear. **A bare ship stops at Step 15b and hands off the PR URL - no merge** (Hard rule 0).
```

**Detailed steps:** see `references/ship-workflow.md`
**Auto-detection logic:** see `references/auto-detect.md`
**PR body template:** see `references/pr-template.md`
**Bot reviewers (inline reply + per-bot re-review triggers):** see `references/bot-reviewers.md`

## Token efficiency

- Steps 4-5 (tests, review): delegate to subagents; Steps 8-9 (journal, docs): background - never inline their output or block on them. Skip steps via flags when the work already passed this session.
- Step 13 (PR comments): **do not fetch once at t+0 and call it clear** - review bots post asynchronously, typically 1-5 min after the PR opens, so an immediate fetch reliably returns zero and reads as "no feedback". Poll until either actionable threads appear or the configured review bots have reported (a bot's summary/top-level comment, or its check reaching a terminal state), with a sensible cap (~5 min). Only then may you report `PR comments: 0 actionable` and continue.

## Output

Bare ship (no `--auto`/`--merge`) - ends at a green PR, unmerged:

```
✓ Pre-flight: PROJ-123-example-feature, 1 commit, +50/-3 (mode: official, target: main)
✓ Tests: 419 passed, 0 failed
✓ Review: 0 critical
✓ Pushed: origin/PROJ-123-example-feature
✓ PR: https://github.com/org/repo/pull/117 → main
✓ CI: green
✓ PR comments: 0 actionable
▸ Merge: left to you - bare ship does not merge. Re-run with --merge (or `gh pr merge`) to land it.
```

With `--auto` / `--merge` - same pipeline, and the final line becomes:

```
✓ Merged: #123 (squash, branch deleted)
```
