---
name: computer-clean
description: "Audit and reclaim disk space on macOS. Discovers cache hogs, dev caches, dead app data, old Downloads, dup installers, and obsolete container/VM images. Use when user says 'clean disk', 'free up space', 'computer-clean', 'cleanup mac', 'disk full', or shows ≥85% disk usage."
category: utilities
keywords: [disk, cleanup, space, cache, mac, macos, prune, storage]
metadata:
  version: "1.1.0"
---

# Computer Clean — macOS Disk Cleanup

Goal: surface the largest reclaimable space on the user's Mac, classify by risk, **always confirm before destructive ops**, then execute.

## Operating principle

**Audit → Classify → Confirm → Execute → Verify.** Never skip the confirm step for 🟡/🔴 buckets. The 🟢 cache bucket can run after a single user "go".

The skill **discovers** what's actually on the user's machine — don't assume specific apps/caches exist. Run audit commands first, then classify what was found.

---

## Phase 1 — Audit (read-only)

Run these in parallel. Report top consumers per bucket.

```bash
# Volume stats
df -h /

# Home Library hot zones
du -sh ~/Library/Caches ~/Library/Logs ~/Library/Containers \
       ~/Library/Application\ Support ~/Downloads ~/.Trash 2>/dev/null

# Drill the heavy ones — top 15 each
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

# Xcode (developers only)
du -sh ~/Library/Developer/Xcode/{DerivedData,Archives,iOS\ DeviceSupport} 2>/dev/null
```

## Phase 2 — Classify

Bucket discovered items by risk.

### 🟢 Safe (regenerable) — execute on single confirm

Standard regenerable caches. Apply only if path exists.

| Path / tool | Reclaim command |
|---|---|
| `~/.Trash/*` | `rm -rf ~/.Trash/* ~/.Trash/.[!.]*` |
| Homebrew | `brew cleanup -s --prune=all` |
| Go | `go clean -cache && go clean -modcache` (or `rm -rf ~/Library/Caches/go-build ~/go/pkg`) |
| npm | `npm cache clean --force` |
| pnpm | `pnpm store prune` |
| yarn | `yarn cache clean` |
| Cargo | `cargo cache --autoclean` (if `cargo-cache` installed) |
| Gradle | `rm -rf ~/.gradle/caches` |
| uv (Python) | `uv cache clean` (kill stuck `uv` first if locked, then `rm -rf ~/.cache/uv`) |
| pip | `pip cache purge` |
| Generic `~/.cache/<tool>` | `rm -rf` after confirming tool is regenerable (puppeteer, pre-commit, packer, etc.) |
| Old JetBrains caches (>1yr) | `rm -rf ~/Library/Caches/JetBrains/*<old-year>*` |
| App auto-updaters | `~/Library/Caches/*ShipIt*`, `~/Library/Caches/*.updater` |
| Xcode `DerivedData` | `rm -rf ~/Library/Developer/Xcode/DerivedData` (rebuilds on next compile) |

### 🟡 Review (user data, easy wins — confirm each)

- **Downloads**: `*.dmg`/`*.pkg`/`*.zip`/`*.rar`/`*.tar.gz` older than 30 days
- **Downloads**: duplicate installers matching `* (1).*`, `* (2).*`
- **Downloads**: stray data dumps (large CSVs, sample videos), abandoned project folders, leftover venvs
- **Apple Podcasts** episodes (auto-downloaded media, not subscriptions)
- **Mail attachments**: `~/Library/Mail/V*/MailData/Attachments` (re-downloadable from server)

### 🔴 Big-ticket (explicit per-item auth required)

- **Container engine VMs** — typically the largest single item. Confirm engine is unused (see Phase 4 migration check):
  - Docker Desktop: `~/Library/Containers/com.docker.docker/Data/vms`
  - OrbStack: `~/.orbstack/data`
  - Rancher Desktop: `~/Library/Application Support/rancher-desktop/lima`, `~/.rd`
  - Colima/Lima: `~/.colima`, `~/.lima`
  - Podman: `~/.local/share/containers`
- **Xcode** archives + simulators: `~/Library/Developer/Xcode/{Archives,iOS DeviceSupport,watchOS DeviceSupport}`, `~/Library/Developer/CoreSimulator`
- **Chat / messaging app data** (Slack, Teams, Discord, Zalo, WeChat, Telegram, Signal) — user-owned history
- **Browser profiles** (Chrome, Brave, Arc, Edge, Firefox, Safari, Vivaldi, etc.) — bookmarks/sessions/extensions live here
- **iOS device backups**: `~/Library/Application Support/MobileSync/Backup`
- **iCloud / Photos library**: `~/Pictures/Photos Library.photoslibrary`
- **Time Machine local snapshots**: `tmutil thinlocalsnapshots / 0 4`

## Phase 3 — Confirm

Present a single summary table (path · size · bucket) and ask:
1. Proceed with all 🟢? (default yes)
2. For 🟡: which to keep / delete?
3. For each 🔴: is the underlying app still in use? Run dependency checks (Phase 4) before approval.

## Phase 4 — Execute

### App-quit guard

Before deleting any app's data dir, quit the app cleanly:
```bash
osascript -e 'quit app "<App Name>"' 2>/dev/null; sleep 1
```

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
find ~/Downloads -maxdepth 1 -type f \( -name '* (1).*' -o -name '* (2).*' -o -name '* (3).*' \) -delete

# Old installer payloads (>30d)
find ~/Downloads -maxdepth 3 -type f \
  \( -name '*.dmg' -o -name '*.pkg' -o -name '*.zip' -o -name '*.rar' -o -name '*.tar.gz' -o -name '*.tgz' \) \
  -mtime +30 -print -delete
```

### Apple Podcasts media purge

```bash
osascript -e 'quit app "Podcasts"' 2>/dev/null; sleep 1
find ~/Library/Group\ Containers/*.groups.com.apple.podcasts \
     ~/Library/Containers/com.apple.podcasts \
     -type f \( -name '*.mp3' -o -name '*.m4a' -o -name '*.mp4' \) -delete 2>/dev/null
```

### Files older than N months

Always **preview first** with `find … -print` before adding `-delete`. Show total size before deleting. Skip if <100MB total unless user insists. **Never** blanket-delete `~/Documents`, `~/Pictures`, `~/Movies`, or iCloud-synced paths.

## Phase 5 — Verify

```bash
df -h /                             # confirm space freed
docker context show 2>/dev/null     # if container engines were touched
docker version --format '{{.Server.Version}}' 2>/dev/null
```

Report: GB freed, before/after free space, residual >5GB items the user declined (so they can revisit later).

---

## Hard rules

1. **Discover, don't assume.** Inspect the machine first — don't pre-supply paths that may not exist. Skip silently when paths are absent.
2. **Never** delete `~/Documents`, `~/Pictures`, `~/Movies`, iCloud Drive, or anything under `~/git`/`~/code`/`~/src`/`~/projects` without explicit per-path approval.
3. **Never** delete an app's `Application Support` while the app is running — quit it first.
4. **Never** wipe browser profiles. Bookmarks, sessions, history, extensions, saved passwords live there.
5. **Never** use `sudo` to bypass file locks. If a tool's cache is locked (e.g., `uv`, `pnpm`), kill the stuck process first.
6. **Container engines:** before deleting one engine's VM, verify the user has migrated to another via `docker context ls`, `kubectl config get-contexts`, and shell rc grep. State the migration target explicitly to the user.
7. **Surface skipped items** at the end so user can decide later — don't silently leave reclaimable space on the table.
8. **Adapt to what's there.** macOS evolves; new caches appear (LLM tool caches, Playwright/Cypress, Hugging Face, Ollama models). Apply the regenerable-cache heuristic: if it's recreated automatically on next use, it's 🟢.

## When to suggest `vd:computer-clean` proactively

End the message with a one-line offer when you notice:
- `df -h` capacity ≥ 85%
- Build/test failures with "no space left on device"
- User mentions "slow Mac", "running out of space", "can't update macOS", "Time Machine full"

Never auto-execute without confirmation.
