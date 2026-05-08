---
name: ship
description: "Ship a feature branch end-to-end: merge target → test → review → version/changelog → commit → push → PR. Use when ready to land a branch on main/master (official) or dev/beta (beta). Stops only on test failures, critical review issues, or major version bumps."
license: MIT
argument-hint: "[official|staging|beta] [--release] [--skip-tests] [--skip-review] [--skip-journal] [--skip-docs] [--dry-run]"
metadata:
  author: vanducng
  version: "1.0.0"
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
| (none) | Auto-detect mode from branch name (`feature/*` → official, `release/*` / `uat/*` → staging, `dev/*` → beta) |
| `--skip-tests` | Skip test step (use only when tests already passed in this session) |
| `--skip-review` | Skip pre-landing review |
| `--skip-journal` | Skip journal entry |
| `--skip-docs` | Skip docs update |
| `--dry-run` | Print what would happen at each step, change nothing |

## Hard rules

1. **Never ship from the target branch.** If on main/master/dev: abort.
2. **Never force push.** Plain `git push` only. If rejected → `git pull --rebase`, retry once, then stop.
3. **Never skip failing tests.** A red test stops the pipeline. Fix it (kick back to `vd:cook`) or pass `--skip-tests` deliberately.
4. **Never bypass critical review issues silently.** Each critical finding gets an `AskUserQuestion`: fix now / acknowledge / false-positive.
5. **Auto-decide everything else.** Patch-version bumps, changelog content, commit message, PR body — infer from diff and commits. Do not pause to ask.
6. **Skip silently when a step doesn't apply.** No version file → skip version bump. No CHANGELOG → skip changelog. No test runner detected → ask once, then skip.
7. **No secrets in commits.** Scan staged diff for API keys / tokens / passwords before commit. If found: stop, warn, suggest `.gitignore`.

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
12. PR            → gh pr create with linked issues, review summary
13. Release       → `--release` only: detect auto-release tool; tag + push if manual
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
- Step 13 runs only with `--release`. If auto-release tooling detected, it's a no-op (CI handles tagging).

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
- Journal: skipped (staging)
- Docs:    skipped (staging)
```

## Workflow position

**Typically follows:** `vd:cook` (cook implements, ship lands)
**Often pairs with:** `code-reviewer` agent (review before ship), `tester` agent (final test run)
