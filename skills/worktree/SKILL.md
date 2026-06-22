---
name: worktree
description: "Create, inspect, and clean isolated git worktrees for parallel feature development. Standardizes worktrees under a top-level .worktrees/ dir, auto-copies .env files (nested included), assigns each worktree a deterministic port block, and runs lifecycle hooks for DB seed/teardown. Use for feature isolation, parallel-agent workflows, worktree health audits, stale cleanup, port conflicts, and monorepo or submodule setups. Hands Laravel Herd projects to herd-worktree for site/env/database setup. Runtime-agnostic: works in Claude Code, Codex CLI, and plain shell."
license: MIT
argument-hint: "[feature-description] | [project] [feature] | status | list | ports | clean | repair | remove <name>"
metadata:
  author: vanducng
  version: "2.3.0"
---

# Worktree

Spin up an isolated git worktree so a new feature, bugfix, or parallel agent run lives on its own branch and its own filesystem path — without disturbing your main checkout. Each worktree arrives ready to run: env files copied, a private port block assigned, install commands detected. **By default the agent session moves into the new worktree** so subsequent work happens there — pass `--no-enter` to stay put. Pairs naturally with `vd:cook` and `vd:fix` (implement in the worktree) and `vd:ship` (land it).

## What this skill is — and isn't

| Skill | Question it answers | Output |
|---|---|---|
| **`vd:worktree`** | Where does this feature/branch live on disk, and how does it run without colliding? | Worktree + branch + env + ports, ready for work |
| `vd:git` | How do I stage/commit/push *this branch*? | Conventional commits on the current branch |
| `vd:ship` | Is this branch ready to land? | Tests → review → version → PR |
| `vd:scout` / `vd:plan` | What am I going to build? | Reports + phase files |
| `vd:herd-worktree` | How should a Laravel app served by Herd be isolated? | This skill's worktree mechanics + Herd link/secure/env/DB/Vite setup |

## Standard location: `.worktrees/`

All worktrees live at **`<git-root>/.worktrees/<repo>-<feature>/`** — one rule for every repo type:

- **Standalone** → `<repo>/.worktrees/`
- **Monorepo** → `<monorepo-root>/.worktrees/`
- **Submodule** → topmost superproject's `.worktrees/`

`.worktrees/` is a **top-level sibling of the `.workbench/` artifact umbrella**, deliberately not nested under it. Worktrees are full checkouts (heavy, contain source), so nesting them inside `.workbench/` would pollute artifact globs (`reports/`, `plans/`) and bloat the umbrella. The script auto-appends `/.worktrees/` and `.env.worktree` to `.git/info/exclude` when the repo doesn't already ignore them, so `git status` stays clean without touching tracked files.

**Worktrees + the umbrella (artifacts survive worktree removal).** Artifact paths anchor to the **main** worktree, so work done from any linked worktree writes back to the *main* checkout's `.workbench/` — surviving `git worktree remove`. Under `paths.layout: feature-first`, each worktree's branch resolves its own feature (e.g. `feat/ELT-3316-…` → `.workbench/features/elt-3316-…/`), so parallel worktrees on different tickets land in **separate feature folders under the one shared main umbrella** — never colliding, never duplicated. A linked worktree has no local `.workbench/`.

**Hazard:** `git clean -fdx` in the main checkout can delete in-repo worktrees (single `-f` skips dirs containing `.git`, double `-ff` does not). Run `clean` afterward to tidy stale metadata.

**Overrides:** `--worktree-root <path>` flag → `WORKTREE_ROOT` env → `.worktrees` default. Older worktrees in sibling `worktrees/` or legacy `.work/worktrees/` dirs keep working (`list`/`status`/`remove`/`clean` find them via git); new ones land in `.worktrees/`.

**No nested worktrees.** Running `create` from *inside* a linked worktree does **not** nest a new `.worktrees` under it — the script resolves back to the main checkout (first entry of `git worktree list`) and lands the new worktree as a sibling at the main root, emitting a redirect warning. If a repo already has a worktree created the old (nested) way, `status` flags it and `repair` relocates it: `worktree repair` (dry-run) → `worktree repair --yes` runs `git worktree move` to the canonical root + `git worktree repair` to fix admin links (`--force` for a dirty worktree).

## Script path

Canonical: `node $HOME/skills/skills/worktree/scripts/worktree.cjs`. If the repo isn't at `$HOME/skills`, use the installed symlink `node $HOME/.claude/skills/worktree/scripts/worktree.cjs`. Pick one at the start of the session and stick with it — don't retry both paths every call.

## Laravel Herd auto-handoff

Before creating a worktree, check whether the current/source repo is a Laravel app served by Herd. Treat it as Laravel when `artisan` exists and `composer.json` requires `laravel/framework`. Treat it as Herd-served when the user says Herd, the `herd` CLI is available and `herd links` includes the repo/site path, or `.env` has an `APP_URL` ending in `.test`.

If both are true, activate `vd:herd-worktree` and let it compose this skill. Do not hand-roll Herd link/secure, `APP_URL`, session/Sanctum, database isolation, Vite TLS/CORS, or teardown-hook rules here; `vd:herd-worktree` owns that layer. This skill still owns the generic worktree mechanics underneath it.

## Workflow

### Step 1 — Repo info

```bash
node $HOME/skills/skills/worktree/scripts/worktree.cjs info --json
```

Parse: `repoType`, `baseBranch`, `projects`, `worktreeRoot`, `worktreeRootSource`, `dirtyState`, `dirtyDetails`.

If the base branch must be fresh (release work, long-running repos), run `git fetch origin <base>` first — `create` warns when the local base is behind an already-fetched `origin/<base>`, but it cannot see commits that were never fetched.

### Step 2 — Decide branch name

**Ticket-driven work is authoritative.** If the task is tied to a Jira, Linear, Shortcut, GitHub issue, or similar ticket, extract the issue key first and use it as the branch name before any slug/prefix logic:
- Jira URL `https://teamcnb.atlassian.net/browse/ELT-3267` → branch `ELT-3267`
- Text `fix ELT-3267 transfer phones` → branch `ELT-3267`
- Bare key `ELT-3267` → branch `ELT-3267`

Run the create command with `--no-prefix` for ticket branches:

```bash
node $HOME/skills/skills/worktree/scripts/worktree.cjs create "ELT-3267" --no-prefix
```

**Use `--no-prefix` (skip Step 3) when the caller supplies an exact branch name** — uppercase letters, an issue-tracker key, or slashes used as a convention:
- `ND-1377-cleanup-docs` → `--no-prefix` → branch `ND-1377-cleanup-docs`
- `kai/feat/604-startup-option` → `--no-prefix` → branch `kai/feat/604-startup-option`

**Attaching to an existing branch:** pass the existing branch name (usually with `--no-prefix`). If the branch exists locally or on origin, `create` attaches the worktree to it instead of creating a new branch — no need to drop to raw `git worktree add`.

**If a ticket is discovered after a non-ticket worktree already exists**, rename the branch before shipping:

```bash
git branch -m ELT-3267 && git push -u origin ELT-3267
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

`create` does the session-setup work automatically:

1. Copies untracked `.env*` files from the source checkout — **including nested ones** (`backend/.env`, `frontend/.env.local`, up to 3 levels). Disable with `--no-copy-env`.
2. Copies `.env*.example` templates for any env name not already copied.
3. Copies `.worktreeinclude` entries (see below).
4. Assigns a deterministic 10-port block and writes `.env.worktree`.
5. Verifies the checkout landed on the requested branch (auto-rescues via `git switch` if git silently attached elsewhere) and warns when the base branch is behind its fetched remote.
6. Detects lockfiles and returns `suggestedInstalls`.

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

### Step 6 — Install deps

Run the `suggestedInstalls` from the create output in the new worktree (background bash, don't block):

```json
"suggestedInstalls": [
  { "dir": ".", "command": "pnpm install" },
  { "dir": "backend", "command": "uv sync" }
]
```

Each entry runs in `<worktreePath>/<dir>`. This replaces guessing from lockfiles by hand. Repos that need more than installs should check in a post-create hook (below).

### Step 7 — Enter the worktree (default)

Unless `--no-enter` was passed, **move the working session into the new worktree** as soon as `create` returns, so all subsequent edits, commands, and git ops land there. The script can't switch a parent session itself — it reports *how* in the `sessionSwitch` block of the create output (`{ enter, path, runtime, action }`); the agent performs the switch per its runtime:

- **Claude Code** — call the `EnterWorktree` tool with the worktree path:
  ```javascript
  EnterWorktree({ path: "<worktreePath>" })   // seamless in-session cwd switch
  ```
  Later, leave with `ExitWorktree({ action: "keep" })` (keeps the branch + files) or `{ action: "remove" }` (deletes both). The path is already registered in `git worktree list`, so `EnterWorktree` accepts it even though it lives under `.worktrees/`, not `.claude/worktrees/`.
- **Codex** — there is **no in-session cwd switch**. Either relaunch rooted at the worktree (`codex --cd "<worktreePath>"`) or run subsequent commands from it. The `sessionSwitch.action` field gives the exact `codex --cd` command.
- **Plain shell / unknown** — `cd "<worktreePath>"`.

Installs (Step 6) run with explicit `<worktreePath>/<dir>` paths, so entering before or after them is equivalent — kick the installs off in the background and enter immediately.

**Skip entering when:** the user said "stay" / "don't switch", you're scripting multiple creates in a loop, or you need to keep operating in the main checkout. Pass `--no-enter` (or set `WORKTREE_NO_ENTER=1`); the `sessionSwitch` block then reports `enter: false`.

## Per-worktree isolation kit

### `.env.worktree` — identity + ports

Every worktree gets a generated `.env.worktree` (excluded from git):

```bash
WORKTREE_NAME=app-login-fix        # directory name
WORKTREE_BRANCH=fix/login-fix
WORKTREE_ID=app_login_fix          # safe for Postgres/MySQL db names
WORKTREE_PORT_BASE=23450           # block of 10: 23450-23459
PORT=23450
COMPOSE_PROJECT_NAME=app-login-fix # docker compose isolation for free
```

Port blocks are a deterministic hash of the worktree name into 20000–39990, collision-checked against sibling worktrees — stable across recreations, no registry. Main checkout keeps default ports (3000/8000/5173); only worktrees get offsets.

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

### `.worktreeinclude` — copy manifest

Same convention Claude Code's native worktrees use: one repo-relative path per line (file or directory, literal paths, `#` comments) copied into each new worktree. For local-only files the env auto-copy doesn't cover:

```
.claude/settings.local.json
.secrets/age-key.txt
config/master.key
```

Unsafe entries (absolute, `..`, globs) are skipped with a warning.

### Hooks — DB seeding and teardown

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
# .worktree/hooks/pre-remove — failure warns, never blocks removal
dropdb "$WORKTREE_ID" 2>/dev/null || true
docker compose -p "$COMPOSE_PROJECT_NAME" down -v 2>/dev/null || true
```

**Docker compose:** `COMPOSE_PROJECT_NAME` already isolates containers/volumes/networks per worktree — `docker compose up` in two worktrees won't collide (map host ports from the block: `"${PORT}:3000"`).

**SQLite:** db files are not auto-copied — add them to `.worktreeinclude`, or copy from `$WORKTREE_SOURCE` in the post-create hook (`cp "$WORKTREE_SOURCE/db.sqlite" ./db.sqlite`).

## Commands

| Command | Usage | Purpose |
|---|---|---|
| `create` | `create [project] <feature>` | Create worktree + branch + env + ports |
| `remove` | `remove <name-or-path>` | Remove **one** worktree: backup env → pre-remove hook → remove + delete branch |
| `clean` | `clean [--merged\|--stale] [--force] [--yes]` | Sweep **all** dead worktrees + prune metadata to free disk |
| `repair` | `repair [--yes] [--force]` | Relocate worktrees nested inside another worktree to the main root + fix admin links |
| `info` | `info` | Repo type, base branch, projects, worktree location |
| `list` | `list` | All existing worktrees (normalized paths) |
| `status` | `status` | Health audit + divergence + disk usage; flags merged/prunable, **nested worktrees**, + reclaimable total |
| `ports` | `ports` | Port block assignment per worktree |

**`remove` vs `clean`:** `remove` takes a name and removes that one. `clean` takes no target — it finds every worktree whose branch is merged into its base or gone from the remote, shows them with disk sizes (dry-run by default), and removes them on `--yes`. `clean` also prunes stale git metadata (the old `prune` command folded in here). Both rescue untracked `.env*` files to `<trees-root>/.env-backups/<name>/` before deletion.

```bash
# See what's reclaimable (safe, read-only)
node $HOME/skills/skills/worktree/scripts/worktree.cjs clean
# Actually free the disk
node $HOME/skills/skills/worktree/scripts/worktree.cjs clean --yes
# Only merged branches; include dirty ones
node $HOME/skills/skills/worktree/scripts/worktree.cjs clean --merged --force --yes
```

## JSON output fields (high-signal)

| Field | Description |
|---|---|
| `baseBranch` / `baseBranchSource` | Base branch and how it was chosen (`explicit` / `auto-detected`) |
| `worktreePath` / `worktreeRootSource` | New worktree location and root-selection source |
| `portBase` | First port of this worktree's 10-port block |
| `worktreeId` | DB-name-safe identifier |
| `suggestedInstalls` | `[{dir, command}]` — run these in the worktree |
| `sessionSwitch` | `{enter, path, runtime, action, exit?, note?}` — how to move the session into the worktree (`enter:false` if `--no-enter`) |
| `envFilesCopied` | Untracked `.env*` files copied (incl. nested paths) |
| `envTemplatesCopied` | `.env*.example` → `.env*` mappings (gap-fill only) |
| `includeCopied` | `.worktreeinclude` entries copied |
| `envBackup` | (remove) `{dir, files}` of rescued env files |
| `currentWorktree` / `worktrees` | Health records (from `status --json` / `list --json`) |
| `assignments` | Port blocks per worktree (from `ports --json`) |

## Exit codes (for shell scripting + Codex tool-use loops)

| Code | Meaning | Retry-able? |
|---:|---|---|
| `0` | success | n/a |
| `2` | bad CLI input, not a git repo, unknown command | no |
| `10` | git command failed (incl. unrecoverable branch mismatch) | maybe (transient) |
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
| `WORKTREE_ROOT` | Override default `.worktrees/` root directory |
| `WORKTREE_NO_ENTER` | Set to `1` to default to *not* switching the session into new worktrees (same as `--no-enter`) |
| `WORKTREE_AGENT_CMD` | Override the "Next steps" CLI hint (for runtimes the script can't auto-detect) |
| `WORKTREE_*` (exported to hooks) | `NAME`, `BRANCH`, `ID`, `PORT_BASE`, `PATH`, `SOURCE` + `PORT`, `COMPOSE_PROJECT_NAME` |

## Notes

- All operations are **idempotent and reversible** except branch deletion via `remove` (which checks for unmerged commits).
- Secrets never leave the machine: env copying is checkout → worktree on the same filesystem.
- `status` normalizes the main checkout path in submodule repos before reporting health.
- `clean` (no `--yes`) is the safe first pass — it lists removable worktrees + reclaimable disk without changing anything.
- The script has **no machine-specific assumptions** — `git`, Node.js ≥18, standard library only.

## Workflow position

**Typically precedes:** `vd:cook` (implement in worktree), `vd:fix` (debug + fix in worktree), `vd:ship` (land from worktree).
**Setup primitive** — creates the isolated filesystem + branch + runtime environment before any implementation work begins.
