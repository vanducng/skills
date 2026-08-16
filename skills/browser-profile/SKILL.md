---
name: browser-profile
description: Manage named persistent browser profiles (cookies, localStorage, IndexedDB, cache) that both you and Claude can use against the SAME Chrome window without collisions. Each profile lives in its own `--user-data-dir` and exposes a deterministic `--remote-debugging-port`. Use when the user says "open profile X", "attach to profile X", "log me into staging once and reuse it", or asks to test frontend flows with persistent auth across runs. Pairs with the `agent-browser` CLI (`agent-browser connect <port>`) for the CDP attach step.
license: MIT
allowed-tools: Bash, Read
metadata:
  author: vanducng
  version: "0.1.0"
---

# browser-profile

A thin profile registry on top of Chrome's `--user-data-dir` + `--remote-debugging-port`. Solves three problems at once:

1. **Persistent state per logical user.** Cookies, localStorage, IndexedDB, disk cache survive across runs.
2. **Manual access.** You open the profile in real Chrome and log in / poke around without Claude involved.
3. **Programmatic access on the same window.** Claude attaches via CDP using `agent-browser connect <port>` - no separate Chromium spawn, no SingletonLock collision.

Why not Playwright `launchPersistentContext`? Because that path requires Playwright to own the browser lifecycle - you can't have a normal Chrome window on the same `user-data-dir` simultaneously. The CDP-attach pattern here lets both of you share one window; connect-over-CDP is exactly how agent-browser participates in it. That's also why agent-browser must attach in `connect` mode, never `--profile` mode: profile mode launches its own Playwright-owned browser, which breaks the shared window this skill exists to provide.

## When to use

- Frontend tests where re-running the login flow on every iteration is wasteful or impossible (MFA, SSO).
- Long-lived debugging sessions where you want to come back tomorrow and have the same logged-in dashboards.
- Hand-off flows: you log in manually, then ask Claude to drive the rest.

**Not for:** cloud-only / anti-bot use cases (use Browserbase contexts via `vd:browser` `--context-id` instead) or one-shot ephemeral scraping (just use `agent-browser` directly, no profile needed).

## Prerequisites

- macOS with Google Chrome at `/Applications/Google Chrome.app` (override via `BROWSER_PROFILE_CHROME` env var).
- `agent-browser` CLI on PATH (`npm install -g agent-browser`, then one-time `agent-browser install`) - used by `attach`.
- Optional: `jq` for pretty `profile list` output.

## Quick start

```bash
SKILL="${CLAUDE_SKILL_DIR:-$(for d in "$HOME/skills/skills/browser-profile" "$HOME/.claude/skills/browser-profile" "$HOME/.agents/skills/browser-profile"; do [ -d "$d" ] && { echo "$d"; break; }; done)}/scripts"

# 1. Open a fresh profile manually (you'll log in once)
"$SKILL/profile-open.sh" retell-staging

# 2. In another shell - let Claude attach to that same window
"$SKILL/profile-attach.sh" retell-staging
# → env-sanitized `agent-browser connect <port-for-retell-staging>` + UA verification

# 3. List profiles and their status
"$SKILL/profile-list.sh"

# 4. When done
"$SKILL/profile-close.sh" retell-staging
```

Naming convention: `<env>-<role>`. Examples: `retell-staging`, `goclaw-admin`, `cnb-snowflake-ui`.

## Command reference

| Script | Purpose |
|---|---|
| `profile-open.sh <name>` | Launch headed Chrome with the profile's user-data-dir and deterministic debug port. Creates the dir on first run. Refuses if already open. |
| `profile-attach.sh <name>` | Run env-sanitized `agent-browser connect <port>` so the agent-browser daemon drives this profile's Chrome (connect mode, never `--profile`), then verify the attachment via `navigator.userAgent`. Probes the CDP endpoint first; suggests `open` if nothing is listening. |
| `profile-list.sh` | Show all profiles with status (open / closed), port, dir size. |
| `profile-close.sh <name>` | Send SIGTERM to the Chrome PID for that profile, clear stale lock files. |
| `profile-export.sh <name> [<out.json>]` | Dump cookies + localStorage as Playwright-compatible `storageState.json` for CI replay. Requires the profile to be open. |
| `profile-reset.sh <name>` | **Destructive.** Wipe the profile dir. Asks for confirmation. |

## How port allocation works

Ports are deterministic from the profile name so `attach` doesn't need a registry file:

```
port = 9300 + (cksum(name) % 100)
```

Range 9300–9399 avoids the conventional 9222. If two names hash to the same port, `open` will fail loudly - rename one.

## Profile directory layout

```
$HOME/.claude/browser-profiles/
├── retell-staging/
│   ├── Default/                 # Chrome user data (cookies.db, Local Storage/, IndexedDB/, Cache/, …)
│   ├── DevToolsActivePort       # written by Chrome on launch; contains the actual port + WS path
│   ├── SingletonLock            # dangling symlink to "<hostname>-<pid>"; may be stale after a crash
│   └── .browser-profile.pid     # PID of the Chrome process we launched (for `close`)
└── goclaw-admin/
    └── ...
```

`SingletonLock` is Chrome's own collision marker - a *dangling symlink* whose target encodes `<hostname>-<pid>` (so `-f`/`-e` tests see nothing; only `-L` does). The scripts treat a profile as open only when that PID is a live Chrome whose command line carries this `--user-data-dir`; stale locks left by crashed sessions are cleared automatically on `open`.

## Security

- Profile dirs are created with `chmod 700`. Storage cookies are tied to your user account.
- Never commit `$HOME/.claude/browser-profiles/` to any repo.
- Same applies to `storageState.json` exports - those are bearer credentials.
- The skill **never** prints cookies / tokens to stdout.

## Integration points

- **`vd:cook` flows that hit authenticated dashboards** - start a step with `profile-attach.sh <name>` so agent-browser is pre-connected to the right session.
- **`vd:browser-trace`** - attaches as a third CDP client on the same target, gets a full trace without interfering. Use the profile's deterministic port as the trace target.
- **`vd:web-e2e`** - project-aware full e2e on top of these profiles: boot/health checks, auth-state probing, flows, and reports. The e2e config's `profile` field names a profile managed here.
- **Playwright `storageState` fixtures** - export `storageState.json` once, then any Playwright test (local or CI) gets the same identity via `{ storageState: '<path>' }`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `open` refuses: "profile already open" | A live Chrome owns this profile | Run `profile-close.sh <name>` first, or use `profile-attach.sh` if you intended to share |
| `list` shows `no-cdp` | Chrome is running but not answering on the deterministic port (launched without the debug flag, or another Chrome took over) | `profile-close.sh <name>` then `profile-open.sh <name>` |
| `attach` says "no CDP endpoint" | Chrome not running on that port | Run `profile-open.sh <name>` first |
| Cookies disappear after sleep/wake | Service-worker eviction by Chrome | Re-login. Chrome's call, not ours. Open issue if reproducible. |
| Port collision between two profiles | cksum hash collision | Rename one of them (e.g., add a `-2` suffix) |
| Chrome won't launch (corrupted profile) | Crash during last session | `profile-reset.sh <name>` and re-login - wipes the whole dir |

## Future (deliberately out of scope for MVP)

- Cross-platform Chrome path resolution (Linux, Windows).
- Registry JSON with `last_used`, custom port overrides, descriptions.
- Auto-renew expired cookies via headless re-login.
- Headless mode for CI - use `profile-export.sh` + Playwright `storageState` instead; persistent-context headless is flaky upstream.
