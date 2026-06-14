---
name: cktovd
description: "Migrate from claudekit (ck) to the vd-cli control plane — install clean-room hooks, convert .ck.json to .vd.json, audit CK_*→VD_* env consumers, and move a repo's plans/ artifacts into the .workbench umbrella (plans, reports, journals, visuals, state as siblings under <git-root>/.workbench/). Use when the user says 'cktovd', 'migrate to vd', 'migrate plans to .workbench', 'enable the .workbench umbrella', or 'switch this repo off claudekit'."
license: MIT
argument-hint: "[repo-path] [--machine] [--check]"
metadata:
  author: vanducng
  version: "1.1.0"
---

# cktovd — claudekit → vd-cli migration

Migrate two layers, in order:

1. **Machine** (once): vd-cli owns the Claude Code control plane — clean-room hooks in `~/.claude/hooks/`, config in `~/.claude/.vd.json`.
2. **Repo** (per project): opt into the `.workbench` umbrella via `<git-root>/.vd.json` and physically move `plans/` artifacts.

Detect scope from the argument: `--machine` → machine layer only; a repo path (default: cwd git root) → repo layer (runs a machine preflight first); `--check` → verify only, change nothing.

## Layout contract (source of truth: vd-cli `internal/hooks/assets/lib/paths.cjs`)

| Artifact | Legacy (no umbrella) | Umbrella on (`.workbench`) |
|---|---|---|
| Plans | `<cwd>/plans/` | `<git-root>/.workbench/plans/` |
| Reports | `plans/reports/` | `<git-root>/.workbench/reports/` (**sibling** of plans, not nested) |
| Journals | `plans/journals/` | `<git-root>/.workbench/journals/` |
| Visuals | `plans/visuals/` | `<git-root>/.workbench/visuals/` |
| State | `plans/goals/` | `<git-root>/.workbench/state/` (**renamed**: goals → state) |
| Docs | `<cwd>/docs/` | `<cwd>/docs/` — **never moves**: git-tracked team deliverables, umbrella-blind by design |

The umbrella dir is named tool-neutrally (`.workbench`, not `.vd`) because multiple agents share the repo. Git worktrees are a separate top-level `<git-root>/.worktrees/` (not under `.workbench`); artifacts written from *inside* a worktree resolve to the **main** repo's `.workbench/` (they survive `git worktree remove`), while `docs/` stays branch-local.

Config precedence: DEFAULT ← global `~/.claude/.vd.json` ← project `<git-root>/.vd.json`. **There is no `.ck.json` read fallback** (removed): vd reads `.vd.json` only. A lingering `.ck.json` *without* its `.vd.json` is no longer silently honored — it **raises a migration error** ("run the cktovd skill / rename to `.vd.json`"). So the cutover is: **create the `.vd.json`** (from `.ck.json` if present). Once `.vd.json` exists the old file is inert (ignored); it's safe to delete — the master backup is your real safety net. vd never writes `.ck.json`.

`paths.umbrella` must be a relative path with no `..`/empty segments that resolves inside the git root. An **invalid** value (absolute, traversal, empty) never errors — it's **silently coerced to null**, which restores the byte-identical legacy layout, so a bad value presents as "migration didn't take effect". A plausible **typo** (`.wrok`) passes sanitization and creates a wrong-named umbrella dir. Umbrella resolution anchors via `git rev-parse --show-toplevel` — a non-git dir never activates it; `git init` first.

## Machine layer

1. **Master backup** (the cutover is destructive; the full-restore recipe depends on this):
   ```sh
   ts=$(date +%Y%m%dT%H%M%S); bak=~/.claude-ck-removal-backup-$ts
   mkdir -p "$bak" && cp -Rp ~/.claude/hooks "$bak"/ && cp ~/.claude/settings.json "$bak"/
   cp ~/.claude/.ck.json "$bak"/ 2>/dev/null || true
   ```
2. **Preflight:** `vd --version` (hooks support landed in 2.4.0; the `.vd.json` rename is post-2.5.0 — `brew upgrade vd` if older). Never patch deployed hooks in place — ck's `ck update` clobbers its files, and vd's are redeployed by `vd install hooks`.
3. **Cut over:**
   ```sh
   npm uninstall -g claudekit-cli
   vd install hooks
   grep -n '\$HOME/.claude/hooks' ~/.claude/settings.json   # all entries must show literal $HOME
   ```
   `vd install hooks` is idempotent: byte-identical files are skipped, a differing vd-owned file is backed up once as `<name>.bak.<UTC-ts>.cjs`, unknown files are never touched. settings.json edits are surgical (only vd's hook entries + the top-level `statusLine` key are patched; a one-time `settings.json.bak` is taken first). Registered commands keep `$HOME` **literal** — the hook runner shell-expands it; never bake a personal absolute path in. Caution: registration matches existing entries by `.cjs` **filename substring** and rewrites them to vd's canonical command — a custom wrapper referencing the same filename gets clobbered.
4. **Config rename (required — prevents the migration error):** `[ -f ~/.claude/.ck.json ] && [ ! -f ~/.claude/.vd.json ] && cp ~/.claude/.ck.json ~/.claude/.vd.json`. With the fallback gone, a global `~/.claude/.ck.json` without `~/.claude/.vd.json` errors on *every* session, so this `cp` is mandatory when a legacy global config exists. After `.vd.json` exists, `rm ~/.claude/.ck.json` (it's inert and backed up). Do **not** set `paths.umbrella` globally — that flips every repo at once and strands un-migrated `plans/` content. Go per-repo; consider the global flip only after all active repos are migrated.
5. **CK_* consumer audit** — the env rename is a hard cut: every `CK_*` session var has a `VD_*` successor (`VD_REPORTS_PATH`, `VD_PLANS_PATH`, `VD_GIT_ROOT`, `VD_ACTIVE_PLAN`, …) and anything still reading `CK_*` silently gets nothing. Temp files renamed `ck-session-*` → `vd-session-*`.
   ```sh
   grep -rn 'CK_' ~/.claude/ --include='*.cjs' --include='*.json' --include='*.sh' \
     | grep -v node_modules | grep -v '.bak'
   ```
   When fixing hits, work from an explicit inventory of your variable names — a blanket `CK_→VD_` replace hits substring false-positives (`SLACK_WEBHOOK_URL`, `BLOCK_LOW_AND_ABOVE`, …) and third-party vars.

## Repo layer

1. **Opt in** at the git root (commit this file — it's the project's umbrella marker; keep it to exactly this minimal form):
   ```sh
   cd "$(git rev-parse --show-toplevel)"
   printf '{\n  "paths": {\n    "umbrella": ".workbench"\n  }\n}\n' > .vd.json
   ```
2. **Move artifacts** (named subdirs first so plan dirs don't swallow them; ONE rename to remember: goals → state):
   ```sh
   mkdir -p .workbench/plans
   [ -d plans/reports ]  && mv plans/reports  .workbench/reports
   [ -d plans/journals ] && mv plans/journals .workbench/journals
   [ -d plans/visuals ]  && mv plans/visuals  .workbench/visuals
   [ -d plans/goals ]    && mv plans/goals    .workbench/state
   find plans -mindepth 1 -maxdepth 1 -exec mv {} .workbench/plans/ \; 2>/dev/null
   rmdir plans
   ```
   Missing sources are fine — absent subdirs appear lazily on first use. If the **current session** is writing into a plan dir, move that dir last (or from a copy). Follow-ups that bite: rewrite embedded `plans/goals` paths inside moved state files; `git ls-files .workbench/ | xargs -r git rm -r --cached` for anything previously tracked under `plans/` (a `mv` into an ignored dir doesn't untrack it).
3. **Gitignore:** replace the `plans` entry with `.workbench`. Don't keep both — if a non-migrated tool recreates `plans/`, it should show up untracked as a signal. The whole migration commit is tiny (5-line `.vd.json` + 1 gitignore line); the file moves are untracked filesystem ops.
4. **Stale references:** grep the repo (`CLAUDE.md`, `AGENTS.md`, `docs/`, `.github/`, scripts) for hardcoded `plans/` paths and point them at the hook-injected paths instead.

**Already on the legacy `.work` umbrella?** A repo migrated before the `.workbench` rename just needs the dir + config flipped: `git mv .work .workbench` (or `mv` if untracked), set `paths.umbrella` to `.workbench` in `.vd.json`, and swap the `.gitignore` entry `.work/` → `.workbench/`. The hook re-resolves to `.workbench/` on the next prompt; legacy `.work/` is still recognized read-only by the resume probes during the transition.

## Verify (also the whole of `--check`)

Run **from inside the target repo** — `loadConfig()` resolves the project `.vd.json` from `process.cwd()`; the payload `cwd` only anchors path strings, so piping from elsewhere false-negatives into legacy output.

```sh
cd "$(git rev-parse --show-toplevel)"
git check-ignore -v .workbench/reports/x && echo "OK .workbench ignored"
git check-ignore -v docs/x; [ $? -eq 1 ] && echo "OK docs NOT ignored"
echo "{\"cwd\":\"$PWD\",\"session_id\":\"check\"}" | node ~/.claude/hooks/dev-rules-reminder.cjs
```

Pass = the injected `## Paths` block shows **six** paths (Reports/Plans/Docs/Visuals/Journals/State) with everything except Docs under `.workbench/`. **Three paths = umbrella did not activate** (invalid umbrella value, missing `.vd.json`, or you ran from outside the repo). A malformed `.vd.json` doesn't crash — it silently falls back to the 3-path legacy injection, so assert on output, never trust the config edit. **No paths at all = a legacy `.ck.json` lingers without a `.vd.json`**: the loader now raises a migration error and the fail-open hook injects nothing — create the `.vd.json` (step 4 / repo step 1). New paths take effect on the **next prompt**; the current session's earlier injection still shows old paths — don't chase that as a bug.

## Rollback

- Repo: delete `<git-root>/.vd.json` (or set umbrella null) and reverse the gitignore swap → legacy layout resumes byte-identically; `mv` the `.workbench` trees back if needed.
- Machine: `vd hooks rollback` (restore newest `*.bak.*` + `settings.json.bak`) or `vd hooks uninstall` (remove + unregister vd-managed files only; third-party hooks untouched). Both support `--dry-run`. Caution: the uninstall allowlist can lag the deployed asset set — check `--dry-run` output and remove orphans by hand.
- Full restore: copy the master backup back over `~/.claude/hooks` + `settings.json`, then `npm i -g claudekit-cli`.

## Gotchas

- Reports under the umbrella is a **direct sibling** of plans — anything string-concatenating `plans/reports/...` breaks; only a session-active plan still redirects reports into the plan dir. Always use the hook-injected `Reports:` path.
- `task-completed-handler.cjs` / `teammate-idle-handler.cjs` live in `~/.claude/hooks` but are deliberately **not** in settings.json (team-runtime invoked) — an "unregistered hook" finding there is not a bug; don't register or delete them.
- Subagent prompts must pass the **work-context** repo's `.workbench/` paths, not the cwd's, when editing another project.
- Monorepos: the umbrella anchors to the **git root**, not cwd — one `.vd.json` and one `.workbench/` per repo, even when working from a subdirectory.
- A corrupted ancestor `.git/config` (e.g. a stray repo at `$HOME`) silently disables git-root resolution for loose dirs beneath it — umbrella just stays off, no error.
