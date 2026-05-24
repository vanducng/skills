---
name: worktree
description: "Create, inspect, and clean isolated git worktrees for parallel feature development. Use for feature isolation, parallel-agent workflows, worktree health audits, stale cleanup, and monorepo or submodule setups. Runtime-agnostic: works in Claude Code, Codex CLI, and plain shell."
license: MIT
argument-hint: "[feature-description] | [project] [feature] | status | list | prune | remove <name>"
metadata:
  author: vanducng
  version: "1.0.0"
---

# Worktree

Spin up an isolated git worktree so a new feature, bugfix, or parallel agent run lives on its own branch and its own filesystem path — without disturbing your main checkout. Pairs naturally with `/vd:cook` and `/vd:fix` (implement in the worktree) and `/vd:ship` (land it).

## What this skill is — and isn't

| Skill | Question it answers | Output |
|---|---|---|
| **`/vd:worktree`** | Where does this feature/branch live on disk? | New worktree directory + branch ready for work |
| `/vd:git` | How do I stage/commit/push *this branch*? | Conventional commits on the current branch |
| `/vd:ship` | Is this branch ready to land? | Tests → review → version → PR |
| `/vd:scout` / `/vd:plan` | What am I going to build? | Reports + phase files |

Use `/vd:worktree` only for the **filesystem + branch primitive** — creating, listing, inspecting, removing. Everything downstream (planning, coding, testing, PR) belongs to the other skills.

## Runtime compatibility

The underlying script auto-detects which agent runtime invoked it and tunes the "Next steps" hint accordingly:

| Detection signal | Next-step CLI shown |
|---|---|
| `CLAUDECODE=1` or `AI_AGENT=claude-*` | `claude` |
| `CODEX_HOME` / `CODEX_SANDBOX` / `OPENAI_CODEX` | `codex` |
| `WORKTREE_AGENT_CMD=<your-cli>` (override) | `<your-cli>` |
| none of the above | `claude  # or: codex` |

JSON output (`--json`) is identical across runtimes — agents should prefer it for parsing.

## Workflow

### Step 1 — Repo info

```bash
node $HOME/skills/skills/worktree/scripts/worktree.cjs info --json
```

Parse: `repoType`, `baseBranch`, `projects`, `worktreeRoot`, `worktreeRootSource`, `dirtyState`, `dirtyDetails`.

### Step 2 — Decide branch name

**Use `--no-prefix` (skip Step 3) when the caller supplies an exact branch name** — e.g., it contains uppercase letters, an issue-tracker key, or slashes used as a convention:
- `ND-1377-cleanup-docs` → `--no-prefix` → branch `ND-1377-cleanup-docs`
- `kai/feat/604-startup-option` → `--no-prefix` → branch `kai/feat/604-startup-option`

**Otherwise detect prefix from the description:**

| Keywords | Prefix |
|---|---|
| fix, bug, error, issue | `fix` |
| refactor, restructure, rewrite | `refactor` |
| docs, documentation, readme | `docs` |
| test, spec, coverage | `test` |
| chore, cleanup, deps | `chore` |
| perf, performance, optimize | `perf` |
| anything else | `feat` |

### Step 3 — Slugify

Skip if `--no-prefix`. Otherwise: kebab-case, max 50 chars.
- `"add authentication system"` → `add-auth`
- `"fix login bug"` → `login-bug`

### Step 4 — Monorepo selection

If `repoType === "monorepo"` and the project wasn't passed in, ask the user which one:

```javascript
AskUserQuestion({
  questions: [{
    header: "Project",
    question: "Which project for the worktree?",
    options: projects.map(p => ({ label: p.name, description: p.path })),
    multiSelect: false
  }]
})
```

### Step 5 — Execute

**Standalone:**
```bash
node $HOME/skills/skills/worktree/scripts/worktree.cjs create "<SLUG>" --prefix <TYPE>
```

**Monorepo:**
```bash
node $HOME/skills/skills/worktree/scripts/worktree.cjs create "<PROJECT>" "<SLUG>" --prefix <TYPE>
```

**Flags:**

| Flag | Purpose |
|---|---|
| `--prefix <type>` | Branch type: `feat\|fix\|refactor\|docs\|test\|chore\|perf` |
| `--base <branch>` | Override auto-detected base (default: `dev → develop → main → master`) |
| `--no-prefix` | Preserve original case + slashes (Jira keys, `user/type/feature`) |
| `--checkout-submodules` | Run `git submodule update --init --checkout --recursive` after create |
| `--post-create-hook <x>` | Explicit hook script path or shell command (overrides auto-detect) |
| `--no-post-create-hook` | Disable hook auto-detection |
| `--worktree-root <path>` | Override default location |
| `--json` | Machine-readable output |
| `--dry-run` | Preview without touching disk |
| `--env <files>` | Comma-separated `.env` files to copy (legacy; templates auto-copy by default) |

### Step 6 — Install deps (post-create hook OR background install)

**Preferred: drop a `post-create` hook into the repo** so the install is repeatable for every worktree the team creates. The script auto-detects (in order):

1. `.worktree/hooks/post-create` (executable) — check this in, share with the team
2. `scripts/setup-worktree` (executable)

Example `.worktree/hooks/post-create`:

```bash
#!/usr/bin/env bash
set -euo pipefail
# $PWD is the new worktree; $WORKTREE_PATH is also exported.
if [ -f bun.lock ]; then bun install
elif [ -f pnpm-lock.yaml ]; then pnpm install
elif [ -f package-lock.json ]; then npm install
elif [ -f poetry.lock ]; then poetry install
elif [ -f uv.lock ]; then uv sync
elif [ -f go.mod ]; then go mod download
fi
[ -f .envrc ] && direnv allow . || true
```

Override with `--post-create-hook <path-or-command>` (e.g. `--post-create-hook "make worktree-init"`).
Skip with `--no-post-create-hook`.

**Fallback** — if no hook is present, kick off the right install yourself in the new worktree path (background bash, don't block):

| Lockfile | Install command |
|---|---|
| `bun.lock` / `bun.lockb` | `bun install` |
| `pnpm-lock.yaml` | `pnpm install` |
| `yarn.lock` | `yarn install` |
| `package-lock.json` | `npm install` |
| `poetry.lock` | `poetry install` |
| `uv.lock` | `uv sync` |
| `requirements.txt` | `pip install -r requirements.txt` |
| `Cargo.toml` | `cargo build` |
| `go.mod` | `go mod download` |

## Commands

| Command | Usage | Purpose |
|---|---|---|
| `create` | `create [project] <feature>` | Create worktree + branch |
| `remove` | `remove <name-or-path>` | Remove worktree + branch (safe; blocks on dirty state) |
| `info` | `info` | Repo type, base branch, projects, worktree location |
| `list` | `list` | All existing worktrees (normalized paths) |
| `status` | `status` | Health audit + base-branch divergence per worktree |
| `prune` | `prune [--dry-run]` | Clean stale worktree metadata |

## JSON output fields (high-signal)

| Field | Description |
|---|---|
| `baseBranch` | Branch the worktree is based on |
| `baseBranchSource` | `explicit` (from `--base`) or `auto-detected` |
| `worktreePath` | Absolute path of the new worktree |
| `worktreeRootSource` | How the location was chosen (flag / env / monorepo / sibling) |
| `checkoutSubmodules` | Whether submodules were initialized |
| `currentWorktree` | Current health record (from `status --json`) |
| `worktrees` | All worktree records (from `list --json` or `status --json`) |
| `entries` | Prune output lines (from `prune --json`) |
| `envTemplatesCopied` | Auto-copied `.env*.example` → `.env*` mappings |

## Exit codes (for shell scripting + Codex tool-use loops)

| Code | Meaning | Retry-able? |
|---:|---|---|
| `0` | success | n/a |
| `2` | bad CLI input, not a git repo, unknown command | no |
| `10` | git command failed | maybe (transient) |
| `13` | permission denied | no (fix perms) |
| `17` | worktree or branch already exists | no (use a different name) |
| `28` | disk / mkdir failed | no (free space) |
| `68` | network (fetch) failed | yes |
| `70` | runtime / node version error | no |
| `75` | post-create hook failed | depends on hook |

JSON output (`--json`) embeds the same `exitCode` inside `error` for parsing without `$?`.

## Environment variables

| Variable | Effect |
|---|---|
| `WORKTREE_ROOT` | Override default worktree root directory |
| `WORKTREE_AGENT_CMD` | Override the "Next steps" CLI hint (for runtimes the script can't auto-detect) |
| `WORKTREE_PATH` | Exported into post-create hooks — absolute path of the new worktree |

## Portability — running on any machine

The skill assumes the `vanducng/skills` repo lives at `$HOME/skills`. If you clone it elsewhere, either:

1. Symlink it: `ln -s /path/to/skills $HOME/skills`
2. Or call the script with an absolute path matching your clone: `node /your/path/skills/worktree/scripts/worktree.cjs ...`

The script itself has **no machine-specific assumptions** — it uses only `git`, Node.js ≥18, and the standard library. No `$HOME`-relative writes, no hardcoded users, no platform-specific shell calls.

## Notes

- Default worktree location is **smart**: submodule → topmost superproject's `worktrees/`; monorepo → `worktrees/` inside repo; standalone → sibling `worktrees/`.
- `--base` is useful for long-lived variant branches (e.g. `main-dsl`) that diverge from auto-detected defaults.
- `status` normalizes the main checkout path in submodule repos before reporting health.
- `prune --dry-run` is the safe first pass when auditing stale metadata.
- `.env*.example` templates auto-copy with the `.example` suffix removed — secrets are never copied across worktrees.
- All operations are **idempotent and reversible** except branch deletion via `remove` (which checks for unmerged commits).

## Workflow position

**Typically precedes:** `/vd:cook` (implement in worktree), `/vd:fix` (debug + fix in worktree), `/vd:ship` (land from worktree).
**Setup primitive** — creates the isolated filesystem + branch before any implementation work begins.
