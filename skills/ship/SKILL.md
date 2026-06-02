---
name: ship
description: "Ship a feature branch end-to-end: merge target → test → review → version/changelog → commit → push → PR. Use when ready to land a branch on main/master (official) or dev/beta (beta). Stops only on test failures, critical review issues, or major version bumps."
license: MIT
argument-hint: "[official|staging|beta] [--auto] [--release] [--skip-tests] [--skip-review] [--skip-pr-comments] [--skip-journal] [--skip-docs] [--dry-run]"
metadata:
  author: vanducng
  version: "1.2.0"
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
| `--skip-pr-comments` | Skip Step 13 (don't fetch / address GH PR review comments) |
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
4b. **Never silently ignore unresolved PR review comments.** After the PR exists, fetch unresolved review threads + `CHANGES_REQUESTED` reviews. Each unresolved comment gets a prompt: fix now / reply / mark resolved / skip. Same blocking model as critical review issues.
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
13. PR comments   → fetch unresolved review threads + CHANGES_REQUESTED reviews; fix / reply / resolve each (re-run Step 4 after any fix)
14. Release       → `--release` only: detect auto-release tool; tag + push if manual
15. CI watch      → wait for PR checks; on failure prompt user (every mode)
16. Auto-merge    → `--auto` only: `gh pr merge --auto` once Step 15 is green
```

**Detailed steps:** see `references/ship-workflow.md`
**Auto-detection logic:** see `references/auto-detect.md`
**PR body template:** see `references/pr-template.md`

## Token efficiency

- Steps 4–5 (tests, review): delegate to subagents — don't inline output in main context.
- Steps 8–9 (journal, docs): run in background — don't block the pipeline on them.
- Step 2 (issues): one `gh issue list` call, parse locally — don't loop API calls.
- Skip steps via flags when work already done in this session.
- Staging mode auto-skips journal (Step 8) and docs (Step 9).
- Beta mode auto-skips docs (Step 9).
- Step 13 (PR comments) runs only when the PR exists *and* has unresolved review threads or `CHANGES_REQUESTED` reviews. Fresh PR with no comments → skip silently. One GraphQL call, no polling. Skipped entirely with `--skip-pr-comments`.
- Step 14 runs only with `--release`. If auto-release tooling detected, it's a no-op (CI handles tagging).
- Step 15 (CI watch) always runs after PR creation. CI failure prompts the user even in `--auto`.
- Step 16 runs only with `--auto`, only after Step 15 reports green (or user explicitly opted to merge anyway). Uses `gh pr merge --auto`, which respects branch protection — queues the merge; never bypasses.

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
✓ PR comments: 0 unresolved
- Journal: skipped (staging)
- Docs:    skipped (staging)
```

## Workflow position

**Typically follows:** `vd:cook` (cook implements, ship lands)
**Often pairs with:** `code-reviewer` agent (review before ship), `tester` agent (final test run)
