---
name: worktree
description: "Create, inspect, and clean isolated git worktrees for parallel feature development. Standardizes worktrees under a top-level .worktrees/ dir, auto-copies .env files (nested included), assigns each worktree a deterministic port block, trusts mise configs in the new worktree when present, and runs lifecycle hooks for DB seed/teardown. Use for feature isolation, parallel-agent workflows, worktree health audits, stale cleanup, port conflicts, and monorepo or submodule setups. Hands Laravel Herd projects to herd-worktree for site/env/database setup. Runtime-agnostic: works in Claude Code, Codex CLI, and plain shell."
license: MIT
argument-hint: "[feature-description] | [project] [feature] | status | list | ports | clean | repair | remove <name>"
metadata:
  author: vanducng
  version: "2.5.0"
---

# Worktree

Spin up an isolated git worktree so a new feature, bugfix, or parallel agent run lives on its own branch and its own filesystem path - without disturbing your main checkout. Each worktree arrives ready to run: env files copied, a private port block assigned, install commands detected. **By default the agent session moves into the new worktree** so subsequent work happens there - pass `--no-enter` to stay put. Pairs naturally with `vd:cook` and `vd:fix` (implement in the worktree) and `vd:ship` (land it).

## Standard location: `.worktrees/`

All worktrees live at **`<git-root>/.worktrees/<repo>-<feature>/`** - one rule for every repo type: standalone → `<repo>/.worktrees/`, monorepo → `<monorepo-root>/.worktrees/`, submodule → topmost superproject's `.worktrees/`.

`.worktrees/` is a **top-level sibling of the `.workbench/` artifact umbrella**, deliberately not nested under it (full checkouts would pollute artifact globs and bloat the umbrella). The script auto-appends `/.worktrees/` and `.env.worktree` to `.git/info/exclude` when not already ignored, so `git status` stays clean.

**Worktrees + the umbrella (artifacts survive worktree removal).** Artifact paths anchor to the **main** worktree, so work done from any linked worktree writes back to the *main* checkout's `.workbench/`. Under `paths.layout: feature-first`, each worktree's branch resolves its own feature (e.g. `feat/PROJ-3316-…` → `.workbench/features/proj-3316-…/`), so parallel worktrees on different tickets land in separate feature folders under the one shared main umbrella. A linked worktree has no local `.workbench/`.

**Hazard:** `git clean -fdx` in the main checkout can delete in-repo worktrees (single `-f` skips dirs containing `.git`, double `-ff` does not). Run `clean` afterward to tidy stale metadata.

**Overrides:** `--worktree-root <path>` flag → `WORKTREE_ROOT` env → `.worktrees` default. Older worktrees in sibling `worktrees/` or legacy `.work/worktrees/` dirs keep working (`list`/`status`/`remove`/`clean` find them via git); new ones land in `.worktrees/`.

**No nested worktrees.** Running `create` from *inside* a linked worktree resolves back to the main checkout (first entry of `git worktree list`) and lands the new worktree as a sibling at the main root, with a redirect warning. A repo with an old nested worktree: `status` flags it; `repair` (dry-run) → `repair --yes` runs `git worktree move` to the canonical root + `git worktree repair` to fix admin links (`--force` for a dirty worktree).

## Script path

Canonical: `node $HOME/skills/skills/worktree/scripts/worktree.cjs`. If the repo isn't at `$HOME/skills`, use the installed symlink `node $HOME/.claude/skills/worktree/scripts/worktree.cjs`. Pick one at the start of the session and stick with it - don't retry both paths every call.

## Laravel Herd auto-handoff

Before creating a worktree, check whether the current/source repo is a Laravel app served by Herd. Treat it as Laravel when `artisan` exists and `composer.json` requires `laravel/framework`. Treat it as Herd-served when the user says Herd, the `herd` CLI is available and `herd links` includes the repo/site path, or `.env` has an `APP_URL` ending in `.test`.

If both are true, activate `vd:herd-worktree` and let it compose this skill - it owns the Herd link/secure, `APP_URL`, session/Sanctum, database isolation, Vite TLS/CORS, and teardown-hook layer. This skill still owns the generic worktree mechanics underneath it.

## Workflow

### Step 1 - Repo info

```bash
node $HOME/skills/skills/worktree/scripts/worktree.cjs info --json
```

Parse: `repoType`, `baseBranch`, `projects`, `worktreeRoot`, `worktreeRootSource`, `dirtyState`, `dirtyDetails`.

If the base branch must be fresh (release work, long-running repos), run `git fetch origin <base>` first - `create` warns when the local base is behind an already-fetched `origin/<base>`, but it cannot see commits that were never fetched.

### Step 2 - Decide branch name

**Ticket-driven work is authoritative.** If the task is tied to a Jira, Linear, Shortcut, GitHub issue, or similar ticket, extract the issue key first and use it as the branch name before any slug/prefix logic:
- Jira URL `https://<your-org>.atlassian.net/browse/PROJ-3267` → branch `PROJ-3267`
- Text `fix PROJ-3267 transfer phones` → branch `PROJ-3267`
- Bare key `PROJ-3267` → branch `PROJ-3267`

Run the create command with `--no-prefix` for ticket branches:

```bash
node $HOME/skills/skills/worktree/scripts/worktree.cjs create "PROJ-3267" --no-prefix
```

**Use `--no-prefix` (skip Step 3) when the caller supplies an exact branch name** - uppercase letters, an issue-tracker key, or slashes used as a convention:
- `ABC-1377-cleanup-docs` → `--no-prefix` → branch `ABC-1377-cleanup-docs`
- `user/feat/604-startup-option` → `--no-prefix` → branch `user/feat/604-startup-option`

**Attaching to an existing branch:** pass the existing branch name (usually with `--no-prefix`). If the branch exists locally or on origin, `create` attaches the worktree to it instead of creating a new branch - no need to drop to raw `git worktree add`.

**If a ticket is discovered after a non-ticket worktree already exists**, rename the branch before shipping:

```bash
git branch -m PROJ-3267 && git push -u origin PROJ-3267
```

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

### Step 3 - Slugify

Skip if `--no-prefix`. Otherwise: kebab-case, max 50 chars - `"add authentication system"` → `add-auth`, `"fix login bug"` → `login-bug`.

### Step 4 - Monorepo selection

If `repoType === "monorepo"` and the project wasn't passed in, ask the user which one (AskUserQuestion in Claude Code; prose question in Codex / plain shell) - offer the `projects` entries from the `info` output as the options.

### Step 5 - Execute

**Standalone:**
```bash
node $HOME/skills/skills/worktree/scripts/worktree.cjs create "<SLUG>" --prefix <TYPE>
```

**Monorepo:**
```bash
node $HOME/skills/skills/worktree/scripts/worktree.cjs create "<PROJECT>" "<SLUG>" --prefix <TYPE>
```

After every successful non-dry-run create that returns `worktreePath`, if `HERDR_ENV=1`, invoke `vd:herdr rename <project> <intent>` for the current pane. Pass the repository or selected monorepo project and the original feature description or ticket. Outside Herdr, skip the handoff. A rename failure does not invalidate the created worktree.

`create` does the session-setup work automatically:

1. Copies untracked `.env*` files from the source checkout - **including nested ones** (`backend/.env`, `frontend/.env.local`, up to 3 levels). Disable with `--no-copy-env`.
2. Copies `.env*.example` templates for any env name not already copied.
3. Copies `.worktreeinclude` entries (see below).
4. Assigns a deterministic 10-port block and writes `.env.worktree`.
5. Verifies the checkout landed on the requested branch (auto-rescues via `git switch` if git silently attached elsewhere) and warns when the base branch is behind its fetched remote.
6. If a mise config is present (`mise.toml`, `.mise.toml`, `.config/mise.toml`, `mise/config.toml`, `.mise/config.toml`) at the worktree root or one directory down, runs `mise trust` on each new path (mise trusts by path, so a new worktree is untrusted until this). `mise install -y` is returned in `suggestedInstalls` so it runs in the background like other package managers. Missing `mise` binary → `mise trust && mise install -y` in `suggestedInstalls`.
7. Detects lockfiles and returns `suggestedInstalls`.

**Flags:**

| Flag | Purpose |
|---|---|
| `--prefix <type>` | Branch type: `feat\|fix\|refactor\|docs\|test\|chore\|perf` |
| `--base <branch>` | Override auto-detected base (default: `dev → develop → main → master`) |
| `--no-prefix` | Preserve original case + slashes (Jira keys, `user/type/feature`); attaches if branch exists |
| `--no-copy-env` | Skip auto-copy of untracked `.env*` files |
| `--no-enter` | Stay in the current dir; don't switch the session into the new worktree (default: enter). Also via `WORKTREE_NO_ENTER=1` |
| `--checkout-submodules` | Run `git submodule update --init --checkout --recursive` after create |
| `--post-create-hook <x>` | Explicit hook script path or shell command (overrides auto-detect) |
| `--no-post-create-hook` | Disable hook auto-detection |
| `--no-pre-remove-hook` | Skip `.worktree/hooks/pre-remove` teardown on remove |
| `--worktree-root <path>` | Override default `.worktrees/` location |
| `--json` | Machine-readable output |
| `--dry-run` | Preview without touching disk (includes `portBase`) |
| `--env <files>` | Comma-separated root-level `.env` files to copy (legacy; auto-copy covers this) |

Exit codes and the remaining env overrides are printed by `worktree.cjs --help`; `WORKTREE_AGENT_CMD` overrides the "Next steps" CLI hint for runtimes the script can't auto-detect.

### Step 6 - Install deps

Mise configs are already trusted when create reports `mise.ran: true`; the tool install still arrives via `suggestedInstalls` (`mise install -y`). Run the `suggestedInstalls` from the create output in the new worktree (background bash, don't block):

```json
"suggestedInstalls": [
  { "dir": ".", "command": "pnpm install" },
  { "dir": "backend", "command": "uv sync" }
]
```

Each entry runs in `<worktreePath>/<dir>`. This replaces guessing from lockfiles by hand. Repos that need more than installs should check in a post-create hook (below).

### Step 7 - Enter the worktree (default)

Unless `--no-enter` was passed, **move the working session into the new worktree** as soon as `create` returns, so all subsequent edits, commands, and git ops land there. The script can't switch a parent session itself - it reports *how* in the `sessionSwitch` block of the create output (`{ enter, path, runtime, action }`); the agent performs the switch per its runtime:

- **Claude Code** - call the `EnterWorktree` tool with the worktree path:
  ```javascript
  EnterWorktree({ path: "<worktreePath>" })   // switches cwd in-session, no restart
  ```
  Later, leave with `ExitWorktree({ action: "keep" })` (keeps the branch + files) or `{ action: "remove" }` (deletes both). This acceptance of a `.worktrees/`-rooted path (instead of `.claude/worktrees/`) applies only to the **first** `EnterWorktree` call from the session's original launch directory, because the path is already registered in `git worktree list`.

  **Do not call `EnterWorktree` a second time for the same worktree.** If the session appears to have drifted back to the original checkout (long idle gap, context compaction, a fresh sub-turn), that is a cwd-tracking artifact, not a reason to re-enter - a second `EnterWorktree({ path })` while already inside a worktree is restricted to paths under `.claude/worktrees/` and will fail on a `vd:worktree`-created path with `Cannot enter worktree: <repo>/.claude/worktrees does not exist`. Recover by prefixing the next command with `cd "<worktreePath>" && ...` instead of retrying the tool call.
- **Codex** - there is **no in-session cwd switch**. Either relaunch rooted at the worktree (`codex --cd "<worktreePath>"`) or run subsequent commands from it. The `sessionSwitch.action` field gives the exact `codex --cd` command.
- **Plain shell / unknown** - `cd "<worktreePath>"`.

Installs (Step 6) run with explicit `<worktreePath>/<dir>` paths, so entering before or after them is equivalent - kick the installs off in the background and enter immediately. Skip entering when the user said "stay" / "don't switch", you're scripting multiple creates in a loop, or you must keep operating in the main checkout (`--no-enter` / `WORKTREE_NO_ENTER=1`; `sessionSwitch` then reports `enter: false`).

**After entering, keep Bash commands single-purpose.** Once inside a worktree, the harness's isolation guard rejects any command it cannot statically verify stays inside the worktree path - heredocs, `for`/`until` loops, multi-step `&&`/`;` chains, and `Monitor`/watch loops all trip it with "too complex to verify that it stays in bounds." Run one simple command per invocation; for anything more complex, write the script to a temp file and execute that file instead of inlining it.

## Per-worktree isolation kit

### `.env.worktree` - identity + ports

Every worktree gets a generated `.env.worktree` (excluded from git):

```bash
WORKTREE_NAME=app-login-fix        # directory name
WORKTREE_BRANCH=fix/login-fix
WORKTREE_ID=app_login_fix          # safe for Postgres/MySQL db names
WORKTREE_PORT_BASE=23450           # block of 10: 23450-23459
PORT=23450
COMPOSE_PROJECT_NAME=app-login-fix # docker compose isolation for free
```

Port blocks are a deterministic hash of the worktree name into 20000-39990, collision-checked against sibling worktrees - stable across recreations, no registry. Main checkout keeps default ports (3000/8000/5173); only worktrees get offsets.

**Using the ports:**

```bash
set -a; . ./.env.worktree; set +a        # shell / hooks
npm run dev -- --port $PORT               # vite needs explicit --port
PORT=$PORT uvicorn app:app --port $PORT   # or pass through directly
# direnv users: add `dotenv .env.worktree` to .envrc
```

Audit all assignments / debug a port conflict:

```bash
node $HOME/skills/skills/worktree/scripts/worktree.cjs ports --json
```

### `.worktreeinclude` - copy manifest

Same convention Claude Code's native worktrees use: one repo-relative path per line (file or directory, literal paths, `#` comments) copied into each new worktree. For local-only files the env auto-copy doesn't cover:

```
.claude/settings.local.json
.secrets/age-key.txt
config/master.key
```

Unsafe entries (absolute, `..`, globs) are skipped with a warning.

### Hooks - DB seeding and teardown

Check `.worktree/hooks/post-create` (executable) into the repo for setup beyond installs; `.worktree/hooks/pre-remove` for teardown. Both run inside the worktree with `WORKTREE_NAME`, `WORKTREE_BRANCH`, `WORKTREE_ID`, `WORKTREE_PORT_BASE`, `PORT`, `COMPOSE_PROJECT_NAME`, `WORKTREE_PATH`, `WORKTREE_SOURCE` (main checkout path) exported. `scripts/setup-worktree` is also auto-detected for post-create.

**Postgres per-worktree DB** (template DB gives sub-second clones):

```bash
#!/usr/bin/env bash
# .worktree/hooks/post-create
set -euo pipefail
createdb "$WORKTREE_ID" -T app_template 2>/dev/null || createdb "$WORKTREE_ID"
DATABASE_URL="postgres://localhost/$WORKTREE_ID" alembic upgrade head
echo "DATABASE_URL=postgres://localhost/$WORKTREE_ID" >> .env.worktree
```

```bash
#!/usr/bin/env bash
# .worktree/hooks/pre-remove - failure warns, never blocks removal
dropdb "$WORKTREE_ID" 2>/dev/null || true
docker compose -p "$COMPOSE_PROJECT_NAME" down -v 2>/dev/null || true
```

**Docker compose:** `COMPOSE_PROJECT_NAME` already isolates containers/volumes/networks per worktree - `docker compose up` in two worktrees won't collide (map host ports from the block: `"${PORT}:3000"`).

**SQLite:** db files are not auto-copied - add them to `.worktreeinclude`, or copy from `$WORKTREE_SOURCE` in the post-create hook (`cp "$WORKTREE_SOURCE/db.sqlite" ./db.sqlite`).

## Commands

| Command | Usage | Purpose |
|---|---|---|
| `create` | `create [project] <feature>` | Create worktree + branch + env + ports |
| `remove` | `remove <name-or-path>` | Remove **one** worktree: backup env → pre-remove hook → remove + delete branch |
| `clean` | `clean [--merged\|--stale] [--force] [--yes]` | Sweep **all** dead worktrees + prune metadata to free disk |
| `repair` | `repair [--yes] [--force]` | Relocate nested worktrees to the main root + fix admin links |
| `info` | `info` | Repo type, base branch, projects, worktree location |
| `list` | `list` | All existing worktrees (normalized paths) |
| `status` | `status` | Health audit + divergence + disk usage; flags merged/prunable, **nested worktrees**, + reclaimable total |
| `ports` | `ports` | Port block assignment per worktree |

**`remove` vs `clean`:** `remove` takes a name and removes that one; it deletes the local branch when `git branch -d` accepts it (Git may accept a branch merged to its upstream even when it is not merged to the base). If `remove` reports `branchKept`, leave it unless the user explicitly asked to discard it too, then `git branch -D <branch>`. `clean` takes no target - it finds every worktree whose branch is merged into its base or gone from the remote, shows disk sizes (dry-run by default), and removes them on `--yes`; it also prunes stale git metadata. Both rescue untracked `.env*` files to `<trees-root>/.env-backups/<name>/` before deletion. Human approval phrases map to: `clean merged` → `clean --merged --yes`; `clean all` → `clean --yes` (merged + stale; dirty worktrees stay skipped). Always run the matching command without `--yes` first, and never add `--force` unless the user explicitly approves a named dirty worktree.

**Targeted teardown of one named worktree** (when the user points at a specific path `clean` skips because the branch is still active, pushed, or unmerged):

1. Check for live users first; if either command finds a process or open file, skip that worktree and ask the user to close the agent - never kill automatically:
   ```bash
   WT=<worktree-path>
   ps -axo pid=,command= | rg -F "$WT" || true
   lsof -nP +D "$WT" 2>/dev/null | head -50
   ```
2. After a merge helper such as `gh pr merge --delete-branch`, re-check the linked worktree's current branch before `remove` - the helper may leave it on the base branch. If it is on a branch you must keep (`main`, `staging`, `dev`), detach first so `remove` skips branch deletion: `git -C <worktree-path> switch --detach`.
3. **A worktree left on the base branch blocks the main checkout** (one checkout per branch): the *next* `gh pr merge --delete-branch` fails its post-merge checkout with `fatal: '<branch>' is already used by worktree at <path>`, and `--delete-branch` reports `cannot delete branch '<b>' used by worktree`. The merge itself still landed - confirm with `gh pr view <n> --json state,mergeCommit` before re-running anything. Free the branch: `git worktree list` → `git -C <worktree-path> switch <its-own-branch>` (or `switch --detach`).
4. If the worktree ran Docker Compose, stop its resources before deleting the checkout. Do not trust `.env.worktree` alone - Compose launched from a subdirectory uses that directory name as the project. Match containers by their Compose working-dir label, then `down -v` for that project from the compose directory (or `-f <compose-file>`). `down -v` removes named/anonymous volumes, not bind-mounted local paths; delete bind-mount data only when the user names it:
   ```bash
   docker ps -a --format '{{.Names}}\t{{.Label "com.docker.compose.project"}}\t{{.Label "com.docker.compose.project.working_dir"}}' | rg -F "$WT"
   docker compose -p <project> down -v --remove-orphans
   ```
5. Remove and verify no checkout, Compose containers, or named volumes remain:
   ```bash
   node $HOME/skills/skills/worktree/scripts/worktree.cjs remove "$WT"
   test ! -e "$WT" && echo removed
   git worktree list --porcelain
   docker volume ls --filter "label=com.docker.compose.project=<project>" --format '{{.Name}}'
   ```
6. If `remove` deleted a pushed branch that should keep a local ref, recreate it from the remote: `git branch --track <branch> origin/<branch>`.

```bash
node $HOME/skills/skills/worktree/scripts/worktree.cjs clean           # reclaimable overview (read-only)
node $HOME/skills/skills/worktree/scripts/worktree.cjs clean --yes     # actually free the disk
```
