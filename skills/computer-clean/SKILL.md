---
name: computer-clean
description: "Audit and reclaim disk space on macOS. Identifies cache hogs, dev caches, dead app data, old Downloads, dup installers, and obsolete VMs/containers. Use when user says 'clean disk', 'free up space', 'computer-clean', 'cleanup mac', 'disk full'."
category: utilities
keywords: [disk, cleanup, space, cache, mac, macos, prune]
metadata:
  author: vanducng
  version: "1.0.0"
---

# Computer Clean — macOS Disk Cleanup

Goal: surface the largest reclaimable space on the user's Mac, classify by risk, **always confirm before destructive ops**, then execute.

## Operating principle

**Audit → Classify → Confirm → Execute → Verify.** Never skip the confirm step for 🟡/🔴 buckets. The 🟢 cache bucket can run after a single user "go".

---

## Phase 1 — Audit (read-only)

Run these in parallel. Report top consumers per bucket.

```bash
# Volume stats (use the data volume, not the firmlinked root)
df -h / && df -h | grep -E 'Data|Volumes'

# Home Library hot zones
du -sh ~/Library/Caches ~/Library/Logs ~/Library/Containers \
       ~/Library/Application\ Support ~/Downloads ~/.Trash 2>/dev/null

# Drill the heavy ones
du -sh ~/Library/Application\ Support/* 2>/dev/null | sort -rh | head -15
du -sh ~/Library/Caches/* 2>/dev/null | sort -rh | head -15
du -sh ~/Library/Containers/* 2>/dev/null | sort -rh | head -10
du -sh ~/Downloads/* 2>/dev/null | sort -rh | head -15

# Dev caches scattered outside Library
du -sh ~/.npm ~/.yarn ~/.cache ~/.pnpm-store ~/Library/pnpm \
       ~/go/pkg ~/.cargo ~/.gradle ~/.m2 ~/.rustup 2>/dev/null

# Inspect ~/.cache children
du -sh ~/.cache/* 2>/dev/null | sort -rh | head -15
```

## Phase 2 — Classify

Bucket by risk.

### 🟢 Safe (regenerable) — execute on single confirm
- `~/Library/Caches/go-build`, `~/go/pkg` → `go clean -cache && go clean -modcache`
- `~/.cache/uv` → `uv cache clean` (or `rm -rf` if locked — kill stuck uv first)
- `~/.npm` → `npm cache clean --force`
- `~/.cache/{puppeteer,packer,prek,pre-commit,chrome-devtools-mcp,pkg,nvim.bak}`
- Homebrew → `brew cleanup -s --prune=all`
- `~/.Trash/*`
- Old JetBrains caches: `~/Library/Caches/JetBrains/{*2022.*,*2023.*}` (>1yr)
- Browser ShipIt updaters: `~/Library/Caches/*ShipIt*` (re-fetched on next update)

### 🟡 Review (user data, easy wins)
- Downloads: `*.dmg`/`*.pkg`/`*.zip`/`*.rar` >30d, dup installers (`* (1).dmg`, `* (2).dmg`)
- Downloads: stray data dumps (CSV shards, sample videos)
- `~/Downloads/Telegram Desktop`, `~/Downloads/Archives`
- Apple Podcasts cache + episodes (`~/Library/Containers/com.apple.podcasts`, `~/Library/Group Containers/243LU875E5.groups.com.apple.podcasts`)

### 🔴 Big-ticket (explicit auth required)
- `~/Library/Application Support/rancher-desktop/lima` (often 50–150GB) — **only nuke if user confirms Rancher is unused**
- Docker Desktop VM: `~/Library/Containers/com.docker.docker/Data/vms`
- OrbStack VM: `~/.orbstack/data` (ask before touching)
- Chat app data: `ZaloData`, `Slack`, `Teams` (user-owned chat history/media)
- Browser profiles: Arc, Chrome, Brave (`Application Support/<browser>`) — bookmarks/history risk
- Xcode: `~/Library/Developer/Xcode/{DerivedData,Archives,iOS DeviceSupport}` (rebuildable but slow)
- `~/Library/Application Support/MobileSync/Backup` (iPhone backups)

## Phase 3 — Confirm

Present a single table to user with sizes and bucket. Ask:
1. Proceed with all 🟢? (default yes)
2. Which 🟡 to keep / delete?
3. For each 🔴: is the underlying app still in use? List dependencies (e.g., docker context, kubectl context, PATH) before approval.

## Phase 4 — Execute

### Switching container engines (Rancher → OrbStack)

If removing Rancher Desktop, **always verify first**:
```bash
docker context ls                  # ensure orbstack is active
which docker                       # if /Users/$USER/.rd/bin/docker, fallback at /usr/local/bin/docker (OrbStack symlink)
ls /usr/local/bin/docker           # confirm OrbStack symlink exists
kubectl config get-contexts        # note which contexts will be orphaned
grep -r 'rancher\|\.rd' ~/.zshrc ~/.zprofile ~/.bashrc ~/.bash_profile 2>/dev/null
```

Then nuke:
```bash
osascript -e 'quit app "Rancher Desktop"' 2>/dev/null; sleep 1
rm -rf ~/Library/Application\ Support/rancher-desktop ~/.rd
rm -rf ~/Library/Caches/rancher-desktop ~/Library/Logs/rancher-desktop
rm -rf ~/Library/Preferences/io.rancherdesktop.* 2>/dev/null
kubectl config delete-context rancher-desktop 2>/dev/null
kubectl config delete-cluster rancher-desktop 2>/dev/null
rm -rf "/Applications/Rancher Desktop.app"
```

### Apple Podcasts purge
```bash
osascript -e 'quit app "Podcasts"' 2>/dev/null; sleep 1
find ~/Library/Group\ Containers/243LU875E5.groups.com.apple.podcasts \
  -type f \( -name '*.mp3' -o -name '*.m4a' -o -name '*.mp4' \) -delete
find ~/Library/Containers/com.apple.podcasts \
  -type f \( -name '*.mp3' -o -name '*.m4a' -o -name '*.mp4' \) -delete
```

### Downloads sweep
```bash
# Dup installers
find ~/Downloads -maxdepth 1 -type f \( -name '* (1).*' -o -name '* (2).*' \) -delete
# Old installer payloads
find ~/Downloads -maxdepth 3 -type f \
  \( -name '*.dmg' -o -name '*.pkg' -o -name '*.zip' -o -name '*.rar' -o -name '*.tar.gz' \) \
  -mtime +30 -print -delete
```

### Files older than N months (only after listing)
Always **preview first** with `find … -print` before `-delete`. Skip when total size <100MB unless user insists. Don't blanket-delete `Documents/`, `Pictures/`, `Movies/`.

## Phase 5 — Verify

```bash
df -h /                             # confirm space freed
which docker && docker context show # if container engines were changed
docker version --format '{{.Server.Version}}' 2>/dev/null
```

Report: GB freed, before/after percentages, residual >5GB items the user declined.

---

## Hard rules

1. **Never** delete `~/Documents`, `~/Pictures`, `~/Movies`, iCloud Drive, or repos under `~/git`/`~/code` without explicit per-path approval.
2. **Never** delete an app's `Application Support` folder while the app is running — `osascript -e 'quit app "X"'` first.
3. **Never** wipe browser profiles (`Arc`, `Chrome`, `Brave`, `Safari`, `Firefox`, `Dia`, `Zen`, `Min`) — bookmarks, sessions, extensions live there.
4. When `~/.cache/uv` is locked, kill stragglers (`pkill -f uv`) before `rm -rf`. Don't bypass with sudo.
5. For container VMs (Rancher/Docker Desktop/OrbStack/Lima), verify the user has migrated to the surviving engine before deleting the unused one's data dir. Check: `docker context ls`, `kubectl config get-contexts`, shell rc PATH.
6. Surface skipped items at the end so user can decide later — don't silently leave money on the table.

## Heuristic: when to suggest /computer-clean proactively

After noticing in environment data:
- `df -h` capacity ≥85%
- Build/test failures with "no space left on device"
- User mentions "slow Mac", "running out of space", "can't update macOS"

End by offering a one-line sweep, never auto-executing without confirmation.
