---
name: git
description: "Granular git operations with conventional commits - stage, commit, push, PR, merge. Auto-splits commits by type/scope, blocks on secrets, delegates verbose work to git-manager subagent. GitHub CLI conventions: --body-file for PR bodies, treat gh pr checks exit 8 (pending) as retry not failure, guard run-id assignment before gh run view. Use when you want explicit control; for full ship-it pipeline use vd:ship."
license: MIT
argument-hint: "cm|cp|pr|merge [args] [--inline]"
metadata:
  author: vanducng
  version: "1.1.0"
---

# Git

Low-level git toolkit for the moments when you don't want the full `vd:ship` pipeline - just a clean commit, a quick push, a PR, or a merge. Keeps verbose git output out of main context by delegating to the `git-manager` subagent. Use `vd:git` mid-work to checkpoint, hand off a PR, or merge an upstream branch; use `vd:ship` when the branch is done and you want the full pipeline (test → review → version → PR → journal).

## Subcommands

| Verb | Reference | Purpose |
|---|---|---|
| `cm` | `references/workflow-commit.md` | Stage + analyze + (split or single) + commit |
| `cp` | `references/workflow-commit.md` + `references/workflow-push.md` | Same as `cm`, then push |
| `pr` | `references/workflow-pr.md` | Create a Pull Request from remote diff; `[to] [from]` default to `main` / current branch |
| `merge` | `references/workflow-merge.md` | Merge `origin/<from>` into `<to>` (never the local `<from>`); same argument defaults |
| (conflicts) | `references/conflict-resolution.md` | Load when rebase/merge stops on conflict markers |
| (branches) | `references/branch-management.md` | Branch naming, lifecycle, strategies |
| (gh usage) | `references/gh-cli-guide.md` | `gh` CLI command cheat sheet |

Parse `$ARGUMENTS` first word (runtimes without argument substitution: the text following the skill name in the user's message) and load the matching reference above. Empty / unclear → `AskUserQuestion` with the four options (plain-text question outside Claude Code). Don't auto-run `cp` - it pushes.

## Flags

| Flag | Effect |
|---|---|
| `--inline` | Skip `git-manager` subagent - run commands from main context. Use for tiny ops or when subagent is unavailable. |

Default for all verbs except `cm` (single-commit case) is subagent delegation - keeps verbose git output out of the main thread.

## Hard safety rules

1. **Block on secrets.** Every staged diff scanned before commit. Match → STOP, show files, suggest `.gitignore`. See `references/safety-protocols.md`.
2. **No `--no-verify`, no `--no-gpg-sign`** unless user asks explicitly. Hooks failing means investigate, not bypass.
3. **No force-push to protected branches.** `main`, `master`, `production`, `prod`, `release/*` - never. Feature branches require explicit user request.
4. **Remote-first for compare ops.** `git diff origin/main...origin/feature` - never `git diff main...HEAD` (includes local WIP).
5. **No AI attribution in commit messages, PR bodies, or PR comments.** No "Generated with Claude", no `Co-Authored-By: Claude`, no `https://claude.ai/code/session_...` session links, no emojis unless asked.
6. **Never amend a published commit.** New commit on top instead.
7. **PR feedback is evidence-based.** For `pr`, fetch unresolved review threads and substantive review/top-level comments when a PR already exists or after creating/updating one. Validate comments against codebase contracts, types, config schemas, tests, and repo rules before changing code. If a suggestion is directionally valid but the literal patch is not the best fix, apply the better root-cause fix and explain that in the reply. Never resolve a review thread before posting an inline rationale on that thread.
8. **Pending checks are retry, not failure.** `gh pr checks` exits **8** while CI is still queued. Do not write `gh pr checks N && gh pr merge N` - the merge never runs. Wait with `scripts/wait-for-checks.sh` (or `gh pr checks --watch`) before an immediate merge, or queue `gh pr merge --auto`. Unresolved review threads stay blocked by `hooks/pr-merge-guard.py`. Full-pipeline CI watch is `vd:ship` Step 15 - do not reimplement it here.

## Conventional commit format

```
type(scope): description
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `build`, `ci`.

- ≤ 72 chars, imperative ("add" not "added"), no trailing period
- Focus on **what**, not **how**
- Scope optional but preferred - match the directory or feature, not the file

See `references/commit-standards.md` for the full table + good/bad examples.

## PR title format

PR titles are **past tense (v-ed)**, and the ticket key is authoritative: if the work references a ticket key, the branch must start with it before the PR is created. `references/pr-template.md` (shared with `vd:ship`) is canonical for the full title rules, ticket invariant, and examples.

## Split decision (commit)

Use split when staged changes mix concerns:
- **Different types** - `feat` + `fix`, code + docs
- **Different scopes** - `auth` + `payments`
- **Mixed surfaces** - config + code, deps + code
- **Many unrelated files** - > 10 files spanning unrelated areas

Single commit when:
- Same type and scope
- ≤ 3 files, ≤ 50 lines changed
- Tightly coupled - refactor of a module + the test, feature impl + its config

`workflow-commit.md` Tool 2 has the awk-based grouping heuristic.

## Pre-commit / pre-push checks

Apply to all `vd:git` verbs that write history:

- **Run lint before commit.** Don't bypass on failure - fix the violation.
- **Run tests before push.** Don't skip failing tests just to land the change.
- **No `.env`, credentials, or large binaries.** Stage explicit files when in doubt; `git add -A` is risky in unfamiliar repos.

If lint or tests fail, surface to user and abort the verb - don't auto-fix mid-commit.

## Output format

Compact, machine-readable line:
```
✓ staged: N files (+X/-Y lines)
✓ security: passed
✓ commit: <sha> type(scope): <description>
✓ pushed: yes | no | n/a
```

For multi-commit splits, repeat the `commit:` line per group.

## Workflow position

Composes with `vd:scout` (find files before commit), `vd:fix` (fix → cm), `vd:cook` (mid-plan commits). Not a substitute for `vd:ship` - `vd:git` is for the checkpoints on the way there.
