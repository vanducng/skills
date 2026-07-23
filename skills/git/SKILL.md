---
name: git
description: "Granular git operations with conventional commits — stage, commit, push, PR, merge. Auto-splits commits by type/scope, blocks on secrets, delegates verbose work to git-manager subagent. Use when you want explicit control; for full ship-it pipeline use vd:ship."
license: MIT
argument-hint: "cm|cp|pr|merge [args] [--inline]"
metadata:
  author: vanducng
  version: "1.0.1"
---

# Git

Low-level git toolkit for the moments when you don't want the full `vd:ship` pipeline — just a clean commit, a quick push, a PR, or a merge. Keeps verbose git output out of main context by delegating to the `git-manager` subagent.

## What this skill is — and isn't

| Skill | Question it answers | Scope |
|---|---|---|
| **`vd:git`** | **"Run one git operation cleanly."** | One verb: commit, push, PR, or merge |
| `vd:ship` | "Land the branch." | Full pipeline: merge target → test → review → version → commit → push → PR → journal |
| `vd:journal` | "What just happened?" | Personal entry in the injected Journals path |

Use `vd:git` when you're mid-work and want to checkpoint, hand off a PR, or merge an upstream branch without invoking the whole ship pipeline. Use `vd:ship` when the branch is done and you want everything.

## Subcommands

| Verb | Reference | Purpose |
|---|---|---|
| `cm` | `references/workflow-commit.md` | Stage + analyze + (split or single) + commit |
| `cp` | `references/workflow-commit.md` + `references/workflow-push.md` | Same as `cm`, then push |
| `pr` | `references/workflow-pr.md` | Create a Pull Request from remote diff |
| `merge` | `references/workflow-merge.md` | Merge `<from>` into `<to>` using `origin/<from>` |

Parse `$ARGUMENTS` first word (runtimes without argument substitution: use the text following the skill name in the user's message):
- `cm` / `cp` / `pr` / `merge` → load the matching reference
- empty / unclear → `AskUserQuestion` with the four options (AskUserQuestion in Claude Code; plain-text question elsewhere). Don't auto-run `cp` — it pushes.

## Argument shapes

| Form | Meaning |
|---|---|
| `vd:git cm` | Stage all, analyze, commit (split if needed). No push. |
| `vd:git cp` | Same as `cm` + push. |
| `vd:git pr [to] [from]` | `to` defaults to `main`, `from` defaults to current branch. |
| `vd:git merge [to] [from]` | Same defaults. Always merges `origin/<from>`, never local. |

## Flags

| Flag | Effect |
|---|---|
| `--inline` | Skip `git-manager` subagent — run commands from main context. Use for tiny ops or when subagent is unavailable. |

Default for all verbs except `cm` (single-commit case) is subagent delegation — keeps verbose git output out of the main thread.

## Hard safety rules

1. **Block on secrets.** Every staged diff scanned before commit. Match → STOP, show files, suggest `.gitignore`. See `references/safety-protocols.md`.
2. **No `--no-verify`, no `--no-gpg-sign`** unless user asks explicitly. Hooks failing means investigate, not bypass.
3. **No force-push to protected branches.** `main`, `master`, `production`, `prod`, `release/*` — never. Feature branches require explicit user request.
4. **Remote-first for compare ops.** `git diff origin/main...origin/feature` — never `git diff main...HEAD` (includes local WIP).
5. **No AI attribution in commit messages, PR bodies, or PR comments.** No "Generated with Claude", no `Co-Authored-By: Claude`, no `https://claude.ai/code/session_...` session links, no emojis unless asked.
6. **Never amend a published commit.** New commit on top instead.
7. **PR feedback is evidence-based.** For `pr`, fetch unresolved review threads and substantive review/top-level comments when a PR already exists or after creating/updating one. Validate comments against codebase contracts, types, config schemas, tests, and repo rules before changing code. If a suggestion is directionally valid but the literal patch is not the best fix, apply the better root-cause fix and explain that in the reply. Never resolve a review thread before posting an inline rationale on that thread.

## Conventional commit format

```
type(scope): description
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `build`, `ci`.

- ≤ 72 chars, imperative ("add" not "added"), no trailing period
- Focus on **what**, not **how**
- Scope optional but preferred — match the directory or feature, not the file

See `references/commit-standards.md` for the full table + good/bad examples.

## PR title format

PR titles flip to **past tense (v-ed)** — they narrate what the branch did, not what to do. Same conventional-commit shape, different verb form. Matches `vd:ship`.

- ✅ `feat(auth): added OAuth2 provider`
- ✅ `PRJ-123: fixed session leak on logout`
- ✅ `chore: [PRJ-123] added user access`
- ❌ `feat(auth): add OAuth2 provider` (imperative — that's for commits)

Ticket-driven work is authoritative:
- If the task references Jira, Linear, Shortcut, GitHub issue, or another ticket
  key (`PRJ-123`), the branch must start with that key before creating/updating
  a PR.
- Prefer branch exactly `PRJ-123` unless the user explicitly provides a longer
  team convention such as `PRJ-123-short-slug`.
- If the current branch does not contain the ticket key, rename it before PR
  creation (`git branch -m PRJ-123 && git push -u origin PRJ-123`), then delete
  the old remote branch if it was pushed accidentally.
- Branch with ticket prefix (`PRJ-123` or `PRJ-123-...`) → PR title
  `PRJ-123: <v-ed description>`. See `references/workflow-pr.md`.
- Repo/user title convention wins over the generic rule. If semantic PR titles
  are enforced, include the ticket after the type:
  `chore: [PRJ-123] <description>`.

## Split decision (commit)

Use split when staged changes mix concerns:
- **Different types** — `feat` + `fix`, code + docs
- **Different scopes** — `auth` + `payments`
- **Mixed surfaces** — config + code, deps + code
- **Many unrelated files** — > 10 files spanning unrelated areas

Single commit when:
- Same type and scope
- ≤ 3 files, ≤ 50 lines changed
- Tightly coupled — refactor of a module + the test, feature impl + its config

`workflow-commit.md` Tool 2 has the awk-based grouping heuristic.

## Pre-commit / pre-push checks

These come from `~/.claude/rules/development-rules.md` and apply to all `vd:git` verbs that write history:

- **Run lint before commit.** Don't bypass on failure — fix the violation.
- **Run tests before push.** Don't skip failing tests just to land the change.
- **No `.env`, credentials, or large binaries.** Stage explicit files when in doubt; `git add -A` is risky in unfamiliar repos.

If lint or tests fail, surface to user and abort the verb — don't auto-fix mid-commit.

## Output format

Compact, machine-readable line:
```
✓ staged: N files (+X/-Y lines)
✓ security: passed
✓ commit: <sha> type(scope): <description>
✓ pushed: yes | no | n/a
```

For multi-commit splits, repeat the `commit:` line per group.

## Token efficiency

- **Delegate verbose ops** — `cp`, `pr`, `merge` produce lots of git output; the subagent eats it and returns a structured summary.
- **`cm` of small staged set can stay inline** — subagent round-trip costs more than the commit.
- **Never paste full diffs** into the main thread. `--stat` and `--name-only` are usually enough; pull file-scoped diffs only when message-drafting needs them.

## Workflow position

**Replaces:** Manual `git add` / `git commit` / `git push` sequences when you want consistency.

**Composes with:** `vd:scout` (find files before commit), `vd:fix` (fix → cm), `vd:cook` (mid-plan commits).

**Not a substitute for `vd:ship`** — `vd:ship` is the right call when the branch is done. `vd:git` is for the checkpoints on the way there.

## References

| File | Purpose |
|---|---|
| `references/workflow-commit.md` | Stage + analyze + split-or-single + commit |
| `references/workflow-push.md` | Push with upstream handling |
| `references/workflow-pr.md` | PR creation process from remote diff |
| `references/pr-template.md` | **Canonical** PR title + body conventions (shared with `vd:ship`) |
| `references/workflow-merge.md` | Merge `origin/<from>` into `<to>` |
| `references/commit-standards.md` | Conventional commit format, types, examples |
| `references/safety-protocols.md` | Secret detection, branch protection, recovery |
| `references/branch-management.md` | Naming, lifecycle, strategies |
| `references/gh-cli-guide.md` | `gh` CLI commands cheat sheet |
