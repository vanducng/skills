---
name: computer-clean
description: "Audit and reclaim disk space on macOS. Discovers cache hogs, dev caches, dead app data, old Downloads, dup installers, obsolete container images and volumes, merged worktrees, and stale node_modules/.venv dirs. Use when user says 'clean disk', 'free up space', 'computer-clean', 'cleanup mac', 'disk full', or shows ≥85% disk usage."
license: MIT
category: utilities
keywords: [disk, cleanup, space, cache, mac, macos, prune, storage]
metadata:
  author: vanducng
  version: "1.3.0"
---

# Computer Clean - macOS Disk Cleanup

Goal: surface the largest reclaimable space on the user's Mac, classify by risk, **always confirm before destructive ops**, then execute.

## Operating principle

**Audit → Classify → Confirm → Execute → Verify.** Never skip the confirm step for 🟡/🔴 buckets. The 🟢 cache bucket can run after a single user "go".

The skill **discovers** what's actually on the user's machine - don't assume specific apps/caches exist. Run audit commands first, then classify what was found.

---

## Phase 1 - Audit (read-only)

Run these in parallel. Report top consumers per bucket.

Never run `du -sh ~/*` in the foreground: a large project tree (`~/git`, `~/projects`) can take over 10 minutes and stall the audit. Size dotdirs one by one with a timeout, and size project roots per child in the background.

Stock macOS has no `timeout`. It comes from Homebrew coreutils, as `timeout` or `gtimeout`. The `tmo` helper defined in each block uses whichever one exists, and without either it runs the command with no time limit. A `${T:+$T 60}` prefix would break under zsh, which does not word-split.

```bash
# Volume stats - the Data volume is the real number; `/` is the sealed system volume
df -h / /System/Volumes/Data

# Home Library hot zones
du -sh ~/Library/Caches ~/Library/Logs ~/Library/Containers \
       ~/Library/Application\ Support ~/Library/Group\ Containers \
       ~/Downloads ~/.Trash 2>/dev/null
du -sh ~/Library/Group\ Containers/* 2>/dev/null | sort -rh | head -8

tmo() { local t; t=$(command -v timeout || command -v gtimeout); if [ -n "$t" ]; then "$t" "$@"; else shift; "$@"; fi; }

# Dotdirs (mise, pyenv, nvm, agent CLIs, logs) - per-dir timeout, skip symlinks
cd ~ && for d in .[!.]*; do [ -d "$d" ] && [ ! -L "$d" ] && \
  printf '%s\t%s\n' "$(tmo 60 du -sh "$d" 2>/dev/null | cut -f1)" "$d"; done | sort -rh | head -20

# Project roots - detached; read $TMPDIR/project-sizes.txt when the job finishes
( for r in "$HOME"/{git,code,src,projects,repos,dev}; do [ -d "$r" ] && find "$r" -mindepth 1 -maxdepth 1 -type d; done |
  while read -r d; do tmo 1800 du -sh "$d" 2>/dev/null; done | sort -rh > "$TMPDIR/project-sizes.txt" ) >/dev/null 2>&1 &

# Drill the heavy ones - top 15 each
du -sh ~/Library/Application\ Support/* 2>/dev/null | sort -rh | head -15
du -sh ~/Library/Caches/* 2>/dev/null | sort -rh | head -15
du -sh ~/Library/Containers/* 2>/dev/null | sort -rh | head -10
du -sh ~/Downloads/* 2>/dev/null | sort -rh | head -15

# Common dev caches outside Library (skip silently if missing)
du -sh ~/.npm ~/.yarn ~/.pnpm-store ~/Library/pnpm \
       ~/go/pkg ~/.cargo ~/.gradle ~/.m2 ~/.rustup \
       ~/.cache ~/.docker 2>/dev/null

# Drill ~/.cache children (uv, pip, puppeteer, pre-commit, etc.)
du -sh ~/.cache/* 2>/dev/null | sort -rh | head -15

# Unused images/volumes/build cache inside the active engine (skip if docker is down)
docker system df 2>/dev/null
# Per-volume sizes; links == 0 means no container (running or stopped) uses it
docker system df -v 2>/dev/null | awk '/^VOLUME NAME/{f=1;next} /^Build cache/{f=0} f && $2==0' | sort -k3 -rh | head -30

# Tool dry runs that report reclaimable size
brew cleanup -n --prune=all 2>/dev/null | tail -1
mise prune --dry-run 2>/dev/null

# Xcode (developers only)
du -sh ~/Library/Developer/Xcode/{DerivedData,Archives,iOS\ DeviceSupport} 2>/dev/null
```

Re-run `df` when the audit ends. If free space dropped by several GB while you were only reading, something is writing to disk (a container VM, a build, a log). Report it before you execute.

## Phase 2 - Classify

Bucket discovered items by risk.

### 🟢 Safe (regenerable) - execute on single confirm

Standard regenerable caches. Apply only if path exists.

| Path / tool | Reclaim command |
|---|---|
| Homebrew | `brew cleanup -s --prune=all` |
| Go | `go clean -cache && go clean -modcache` (or `rm -rf ~/Library/Caches/go-build ~/go/pkg`) |
| npm | `npm cache clean --force && rm -rf ~/.npm/_npx` (`npm cache clean` does not clear the npx cache) |
| pnpm | `pnpm store prune` |
| yarn | `yarn cache clean` |
| Cargo | `cargo cache --autoclean` (if `cargo-cache` installed) |
| Gradle | `rm -rf ~/.gradle/caches` |
| uv (Python) | `uv cache clean --force` (lock is often a live `uvx` MCP; `--force` is the documented override. Kill `uv` only if it is hung, not serving) |
| pip | `pip cache purge` |
| Generic `~/.cache/<tool>` | `rm -rf` after confirming tool is regenerable (puppeteer, pre-commit, packer, etc.) |
| Old JetBrains caches (>1yr) | `rm -rf ~/Library/Caches/JetBrains/*<old-year>*` |
| App auto-updaters | `~/Library/Caches/*ShipIt*`, `~/Library/Caches/*.updater` |
| App caches | `~/Library/Caches/<bundle-id>` per app, after the app has quit (see App-quit guard) |
| Container build cache + unused images | see Container engine prune |
| Xcode `DerivedData` | `rm -rf ~/Library/Developer/Xcode/DerivedData` (rebuilds on next compile) |

### 🟡 Review (user data, easy wins - confirm each)

Move user-owned files (Downloads, logs, app snapshots) to the Trash with `/usr/bin/trash <path>` (macOS 15+) instead of `rm` or `find -delete`. If `/usr/bin/trash` is missing (macOS 14 or older), stop and ask the user before falling back to `mv -n <path> ~/.Trash/`. Never fall back to `rm`. Files moved to the Trash stay recoverable until the user empties the Trash. Regenerable items have their own commands below: re-downloadable media, `mise prune`, container volumes and dependency dirs.

- **Downloads**: `*.dmg`/`*.pkg`/`*.zip`/`*.rar`/`*.tar.gz` older than 30 days
- **Downloads**: duplicate installers matching `* (1).*`, `* (2).*`
- **Downloads**: stray data dumps (large CSVs, sample videos), abandoned project folders, leftover venvs
- **Apple Podcasts** episodes (auto-downloaded media, not subscriptions)
- **Mail attachments**: `~/Library/Mail/V*/MailData/Attachments` (re-downloadable from server)
- **LLM model weights**: `~/.cache/huggingface`, `~/.ollama` - regenerable but slow/expensive to redownload
- **Cursor snapshots**: `~/Library/Application Support/Cursor/snapshots` - local codebase snapshots, rebuilds
- **Claude Desktop VM**: `~/Library/Application Support/Claude/vm_bundles` - VM image, redownloads
- **Agent / CLI logs**: one multi-GB JSONL under `~/.<tool>/logs/` is common. Check its mtime, then move it to Trash. Session transcripts (`~/.claude/projects`, `~/.codex/sessions`) are user history, so keep them by default
- **Old tool runtimes**: `mise prune -y` removes versions that no config references. `~/.pyenv`, `~/.nvm` and conda installs need a per-version review
- **Anonymous unused container volumes** (64-hex names, links 0): one approval covers the set. When asking, say that a database container started without `-v` writes to one of these, so they can hold data. See Container engine prune
- **Regenerable named volumes**: `*playwright*`, `*venv*`, `*npm-cache*`, `*composer-cache*`, `buildx_buildkit_*_state`
- **Stale dependency dirs**: `node_modules` / `.venv` in idle repos. See Stale dependency dirs

### 🔴 Big-ticket (explicit per-item auth required)

- **Container engine VMs** - typically the largest single item. Confirm engine is unused (see Phase 4 migration check):
  - Docker Desktop: `~/Library/Containers/com.docker.docker/Data/vms`
  - OrbStack: `~/Library/Group Containers/*.dev.orbstack/data` (old installs: `~/.orbstack/data`)
  - Rancher Desktop: `~/Library/Application Support/rancher-desktop/lima`, `~/.rd`
  - Colima/Lima: `~/.colima`, `~/.lima`
  - Podman: `~/.local/share/containers`
- **Named database volumes** (`*postgres*`, `*mysql*`, `*pgdata*`, `*redis*`, `*-data`), even when unused
- **Xcode** archives + simulators: `~/Library/Developer/Xcode/{Archives,iOS DeviceSupport,watchOS DeviceSupport}`, `~/Library/Developer/CoreSimulator`
- **Chat / messaging app data** (Slack, Teams, Discord, Zalo, WeChat, Telegram, Signal) - user-owned history
- **Browser profiles** (Chrome, Brave, Arc, Edge, Firefox, Safari, Vivaldi, etc.) - bookmarks/sessions/extensions live here
- **iOS device backups**: `~/Library/Application Support/MobileSync/Backup`
- **iCloud / Photos library**: `~/Pictures/Photos Library.photoslibrary`
- **Time Machine local snapshots**: `tmutil thinlocalsnapshots / 0 4`

## Phase 3 - Confirm

Present a single summary table (path · size · bucket) and ask:
1. Proceed with all 🟢? (default yes)
2. For 🟡: which to keep / delete?
3. For each 🔴: is the underlying app still in use? Run dependency checks (Phase 4) before approval.

## Phase 4 - Execute

### App-quit guard

Before quitting anything, walk the agent's parent PID chain (`p=$$; while [ "$p" -gt 1 ]; do ps -o pid=,ppid=,comm= -p "$p"; p=$(ps -o ppid= -p "$p" | tr -d ' '); done`). If the app is an ancestor, for example an IDE's integrated terminal, quitting it kills the session, so ask the user to quit it instead.

Before deleting any app's data dir or cache, quit the app cleanly and confirm it is gone:
```bash
tmo() { local t; t=$(command -v timeout || command -v gtimeout); if [ -n "$t" ]; then "$t" "$@"; else shift; "$@"; fi; }
tmo 20 osascript -e 'quit app "<App Name>"' 2>/dev/null; sleep 5
ps -axo comm= | grep -E '/<App Name>\.app/Contents/MacOS/' || echo quit
```
If the app ignores quit, skip its paths and report them. Never force-kill it.

### One path per delete

Each regenerable cache is its own command. Do not pass several roots to one `rm`. A mid-run "leave this one" then stops only that path. List each browser's `~/Library/Caches/<App>` as its own row. That directory is cache. `~/Library/Application Support/<App>` is the profile and stays 🔴.

### Container engine prune (engine still in use)

Do not delete the VM. Do not run `docker system prune -af --volumes`, and never fold volumes into an image prune. Named database volumes are 🔴. Anonymous unused volumes are 🟡 and need their own explicit approval, because they can still hold a database's data.

Show `docker system df`, then run only the lines the user approved:

```bash
docker ps --format '{{.Names}}' | sort > "$TMPDIR/ps-before.txt"
docker builder prune -af    # build cache; regenerable
docker image prune -af      # images no container uses; running containers keep theirs
docker volume prune -f      # unused ANONYMOUS volumes only on API >= 1.42; never add -a
docker volume rm <name>     # one approved named volume per command
docker ps --format '{{.Names}}' | sort | diff "$TMPDIR/ps-before.txt" -
```

Before running `volume prune`, check that `docker version --format '{{.Server.APIVersion}}'` is at least 1.42 and that `docker volume prune --help` lists `-a, --all`. On older engines, plain `prune` deletes named volumes too.

The final `diff` must be empty: the same containers are still up. Sparse VM disks (OrbStack, Docker Desktop) return freed space to the host slowly, over minutes, so check `df -h /System/Volumes/Data` again before reporting the totals.

### Container engine migration (generic)

If user is decommissioning one engine in favor of another, **verify migration first**:

```bash
docker context ls                          # which engine is active (asterisk)
which docker                               # current binary
ls -la "$(which docker)"                   # follow symlink chain
/usr/bin/which -a docker                   # all docker binaries on PATH
kubectl config get-contexts                # k8s contexts that may be orphaned
grep -nE 'rancher|orbstack|colima|docker' ~/.zshrc ~/.zprofile ~/.bashrc ~/.bash_profile ~/.config/fish/config.fish 2>/dev/null
```

After confirmation, the removal pattern is:
1. Quit the app (`osascript -e 'quit app "..."'`).
2. `rm -rf` the app's `Application Support` data dir + dotfile dir under `$HOME` (e.g., `~/.rd`, `~/.colima`).
3. `rm -rf` its `Caches`, `Logs`, and `Preferences/<bundle-id>.*`.
4. `kubectl config delete-context/cluster/user <name>` for orphaned k8s contexts.
5. `rm -rf /Applications/<App>.app`.
6. Remind user to remove any `PATH` entries from shell rc files if grep found matches.

### Downloads sweep

```bash
# Duplicates created by re-downloads
find ~/Downloads -maxdepth 1 -type f \( -name '* (1).*' -o -name '* (2).*' -o -name '* (3).*' \) -print -exec /usr/bin/trash {} +

# Old installer payloads (>30d)
find ~/Downloads -maxdepth 3 -type f \
  \( -name '*.dmg' -o -name '*.pkg' -o -name '*.zip' -o -name '*.rar' -o -name '*.tar.gz' -o -name '*.tgz' \) \
  -mtime +30 -print -exec /usr/bin/trash {} +
```

### Apple Podcasts media purge

```bash
tmo() { local t; t=$(command -v timeout || command -v gtimeout); if [ -n "$t" ]; then "$t" "$@"; else shift; "$@"; fi; }
tmo 20 osascript -e 'quit app "Podcasts"' 2>/dev/null; sleep 5
ps -axo comm= | grep -qE '/Podcasts\.app/Contents/MacOS/' && echo "Podcasts still running - skip" ||
find ~/Library/Group\ Containers/*.groups.com.apple.podcasts \
     ~/Library/Containers/com.apple.podcasts \
     -type f \( -name '*.mp3' -o -name '*.m4a' -o -name '*.mp4' \) -delete 2>/dev/null   # re-downloadable episodes
```

### Files older than N months

Always **preview first** with `find … -print` before adding `-delete`. Show total size before deleting. Skip if <100MB total unless user insists. **Never** blanket-delete `~/Documents`, `~/Pictures`, `~/Movies`, or iCloud-synced paths, and never delete anything under `~/git`/`~/code`/`~/src`/`~/projects` without explicit per-path approval.

## Phase 5 - Verify

```bash
df -h / /System/Volumes/Data        # confirm space freed; compare Data with the Phase 1 number
node "$HOME/skills/skills/worktree/scripts/worktree.cjs" clean --merged 2>/dev/null
docker context show 2>/dev/null     # if container engines were touched
docker version --format '{{.Server.Version}}' 2>/dev/null
```

Report: GB freed, before/after free space, how much is sitting in the Trash for the user to empty, and residual >5GB items the user declined (so they can revisit later).

---

## Git worktrees (🟡 project data - defer to vd:worktree)

Discover roots read-only:

```bash
for root in "$HOME/git" "$HOME/code" "$HOME/src" "$HOME/projects" \
           "$HOME/worktrees" "$HOME/Worktrees" "$HOME/repos" "$HOME/dev"; do
  [ -d "$root" ] || continue
  find "$root" -maxdepth 8 -type d \
    \( -name .worktrees -o -name worktrees \
       -o -path '*/.claude/worktrees' -o -path '*/.dmux/worktrees' \) -print 2>/dev/null
done
```

For per-repo registration (including worktrees not co-located under a directory named `worktrees`), use `git -C "$repo" worktree list --porcelain`. Do not grep or `find` for a literal `.git/worktrees` path - the `scout-block` hook denies any Bash command matching `(^|/)\.git(/|$)`.

All cleanup runs through `vd:worktree` (`node "$HOME/skills/skills/worktree/scripts/worktree.cjs" clean` from each repository root) - never `rm -rf` a worktree. Flags and semantics (dry run by default, `--yes`, `--merged`, `--force` and its dirty-worktree skip) are vd:worktree's to consult; the approval aliases are `clean merged` → `clean --merged --yes` and `clean all` → `clean --yes`. Always show the dry-run candidates and total size before applying either alias, grouped into `.worktrees/`, task-workspace checkouts, and scratch dirs. `clean` from a repo root selects all three. Do not run repo-wide `clean --yes` when a candidate sits outside `.worktrees/` unless that path was named; remove named paths with `remove <path>`. Never infer approval for dirty paths from `clean all`. The dirty skip ignores untracked files, so also skip a candidate whose `git status --porcelain` shows `??` other than `.env*`.

Before removing candidates, take one open-file snapshot (`lsof -nP -Fn 2>/dev/null | grep '^n/' | sed 's/^n//' | sort -u > "$TMPDIR/lsof.txt"`). Skip any candidate where `grep -qxF "$WT" "$TMPDIR/lsof.txt" || grep -qF "$WT/" "$TMPDIR/lsof.txt"` succeeds. The exact match catches a cwd at the worktree root, and the prefix match catches cwds and open files under it. Running `lsof +D` per worktree takes minutes on large trees. If a worktree you need is in use, ask the user to close it. Never kill agent processes.

Dry-run handling:
- Give each repo's dry run a generous timeout and save the full output to a file. Never pipe it through `tail` or `head`: truncation hides candidates, and a dry run that prints nothing may have timed out on a repo with a lot of worktrees.
- Task-workspace checkouts registered from outside the discovery roots only show up in the dry run or in `git worktree list`. Size them from there.
- Pass the exact candidate paths from the dry run to `remove`. Never select them by name pattern: a pattern also matches non-candidate siblings such as `<name>-stg` or `<name>-staging`.
- `remove` also deletes the local branch. Show "merged" candidates apart from "gone from remote" ones, since the latter may hold commits that never landed. They need their own approval.

## Stale dependency dirs (🟡 - per-list approval)

`node_modules` and `.venv` in idle repos are often the biggest regenerable item under project roots. Discover them, measure each repo's idle time, and present tiers. Hundreds of `du` calls take minutes, so the scan runs detached. Read `$TMPDIR/deps.tsv` when the job finishes:

```bash
( now=$(date +%s); : > "$TMPDIR/deps-nogit.txt"; : > "$TMPDIR/deps.tsv"; roots=()
for r in "$HOME"/{git,code,src,projects,repos,dev}; do [ -d "$r" ] && roots+=("$r"); done
[ ${#roots[@]} -gt 0 ] && find "${roots[@]}" -type d \( -name node_modules -o -name .venv \) -prune -print 2>/dev/null |
while read -r d; do
  p=$(dirname "$d")
  ct=$(git -C "$p" log -1 --format=%ct HEAD 2>/dev/null || echo 0)
  idx=$(git -C "$p" rev-parse --path-format=absolute --git-path index 2>/dev/null)
  it=$( [ -n "$idx" ] && stat -f %m "$idx" 2>/dev/null || echo 0)
  last=$(( ct > it ? ct : it ))
  [ "$last" -eq 0 ] && { echo "$d" >> "$TMPDIR/deps-nogit.txt"; continue; }
  printf '%s\t%s\t%s\n' "$(du -sk "$d" | cut -f1)" "$(( (now - last) / 86400 ))" "$d"
done | sort -rn > "$TMPDIR/deps.tsv" ) >/dev/null 2>&1 &   # KB, idle days, path
```

- Idle time is the later of the HEAD commit time and the index mtime. The index changes on checkout, add and status refresh, so it catches recent work.
- Paths outside a git repo have no timestamp and would look about 20,000 days idle. They go to `deps-nogit.txt` and never into a tier. List them separately for per-path review.
- Show the 30, 60 and 90-day tiers with directory counts and GB. Call out worktrees with unmerged work separately, since their deps need a reinstall when the user picks them back up. Write the full path list to a scratch file and have the user approve that file. That meets the per-path rule for project roots.
- Leave out paths inside worktrees that are being removed in the same run.
- Before deleting: take a fresh `lsof` snapshot and skip any path that appears in it exactly or as a prefix, and check that each path ends in `/node_modules` or `/.venv`. Use one `rm -rf` per path, and run it in the background, because hundreds of small-file trees take more than 10 minutes.
- A context-guard hook may block any command that mentions `node_modules` or `venv`. Ask the user before adding a temporary allow entry (for scout-block's `.vdignore` that is the glob `!node_modules`, not a regex), and remove the entry when you finish.

## Hard rules

1. **Never** wipe browser profiles. Bookmarks, sessions, history, extensions, saved passwords live there.
2. **Never** use `sudo` to bypass file locks. If a tool's cache is locked (`uv`, `pnpm`), prefer the tool's `--force` (or wait). Kill only if the process is actually hung, not a live `uvx` / MCP / package-manager.
3. **Never** delete an app's `Application Support` while the app is running - quit it first.
4. **Surface skipped items** at the end so user can decide later - don't silently leave reclaimable space on the table.
5. **Adapt to what's there.** macOS evolves; new caches appear (LLM tool caches, Playwright/Cypress, Hugging Face, Ollama models). Small regenerable caches are 🟢. Multi-GB model weights (Hugging Face, Ollama) are 🟡 even though they regenerate.
6. **Never empty the Trash yourself.** It is irreversible. Report its size and let the user empty it from Finder.
7. **Never force-kill an app** to clear its data. If it ignores quit, skip it and report it.
