---
name: agent-browser
description: Drive web pages with the agent-browser CLI (Playwright engine) — snapshot with @e refs, fill/click, video recording, network mocking, persistent --profile and storage-state auth. The alternative driver to vd:browser for when you need WebM recordings of a flow, request mocking/blocking, device emulation, or Playwright wait semantics. Use when the user says "agent-browser", "record a video of the flow", "mock that API call in the browser", or asks for browser automation with built-in waiting.
license: MIT
compatibility: Requires the agent-browser CLI (`npm install -g agent-browser`, verified against 0.27.x) and a one-time `agent-browser install` to fetch its Chromium. Profile mode is mutually exclusive with CDP attach.
argument-hint: "[url or flow description]"
metadata:
  author: vanducng
  version: "0.1.0"
  attribution: wraps vercel-labs/agent-browser; command-surface notes adapted from claudekit agent-browser (Apache-2.0)
---

# agent-browser

The second browser-driving stack in this catalog, and deliberately so. The primary stack (`vd:browser-profile` + `vd:browser` + `vd:browser-trace`) wins whenever a persistent human-shareable login or trace evidence matters, because everything attaches to one CDP port. agent-browser brings what that stack lacks: **video recording** of flows, **network route mocking/blocking**, device emulation, and Playwright's auto-waiting — at the cost of the one constraint that decides everything: **`--profile` mode cannot combine with CDP connections**, so `vd:browser-trace` cannot observe a profile session and no human shares the window.

Pick per task, not per preference:

| Need | Use |
|---|---|
| Persistent login shared with the human, trace evidence, e2e flows | `vd:browser` trio via `vd:web-e2e` |
| WebM recording of a flow, request mocking, device/geolocation emulation | this skill |
| Drive the profile Chrome *and* record | not possible — profile ⊕ CDP; record on agent-browser's own profile instead |

## Prerequisites

```bash
which agent-browser || npm install -g agent-browser
agent-browser --version          # 0.27.x verified; ≥0.20 required for --state/--session-name
agent-browser install            # one-time Chromium download
```

A background daemon (socket under `~/.agent-browser/`) keeps the browser alive between invocations; `idleTimeout` in `agent-browser.json` controls auto-shutdown.

## Quick start

```bash
agent-browser open https://myapp.test/login
agent-browser snapshot -i                  # interactive elements with @e refs
agent-browser fill @e2 "user@example.com"
agent-browser fill @e3 "secret"
agent-browser click @e1
agent-browser wait --url "**/dashboard"
```

## Auth persistence — three mechanisms, one decision

| Mechanism | What persists | When |
|---|---|---|
| `--profile <dir>` / `AGENT_BROWSER_PROFILE` | Everything (launchPersistentContext: cookies, localStorage, service workers) | Long-lived logins for *this* stack; use a dedicated dir under `~/.agent-browser-profiles/<context>` — never a real Chrome profile (macOS keychain encryption breaks it) |
| `state save/load <file>` or `--state` | Cookies + storage snapshot | Portable, per-repo (gitignored `.browser/auth.json` convention); pairs with CI |
| `--session-name <name>` | Auto-saved/restored session state | Convenience for recurring tasks |

Profile mode excludes `--cdp`, `--state`, and extensions — documented upstream, not a bug to debug.

### Named profiles — one per identity context

Keep a separate persistent profile per identity (work org, client, personal) so the right account logs into the right service: `~/.agent-browser-profiles/<context>` (e.g. `default` for personal, one dir per organization). `AGENT_BROWSER_PROFILE` (often exported in the shell rc) sets the fallback; an explicit `--profile` flag wins. A repo may pin its profile via project memory or a repo-local skill — check there first.

**Before driving any authenticated service: confirm the profile with the user.** If the task touches a login-bearing site and the profile choice wasn't already pinned (memory/repo skill/explicit user instruction), open the target URL **headed** with the candidate profile and ask the user to confirm it's the right identity — and to complete login (SSO/2FA) in that window if the session is missing:

```bash
agent-browser close   # daemon holds one profile; restart to switch
agent-browser --profile ~/.agent-browser-profiles/<context> --headed open https://target.example
# pause → user confirms profile / logs in once → session persists in the profile dir
```

Do not guess between profiles; a wrong-identity action on a real service is hard to undo.

## Command surface (high-traffic subset)

```bash
agent-browser snapshot -i | -c | -d 3 | -s "nav"        # refs, compact, depth, scoped
agent-browser click|dblclick|hover @e1 · fill|type @e2 "text" · press Enter
agent-browser get text|html|value|attr|title|url|count|box [@ref|selector]
agent-browser wait @e1 | --text "Done" | --url "**/x" | --idle | --fn "() => window.ready"
agent-browser find role|text|label|placeholder|testid <value>
agent-browser screenshot [selector] [path] [--full]    # positional path (NOT -o); pass an ABSOLUTE path · pdf -o page.pdf
agent-browser record start [out.webm] · record stop · record restart
agent-browser network route "**/api/*" --body '{"data":[]}' · --abort · network requests
agent-browser cookies|storage local|state save f.json
agent-browser set viewport 1920 1080 · set device "iPhone 14" · set media dark   # browser-settings are `set` subcommands
agent-browser tabs · tab new|<n>|close · frame <n> · dialog accept · eval "expr"
agent-browser --session <name> ...                       # parallel isolated instances
agent-browser -p browserbase ...                         # cloud (BROWSERBASE_API_KEY)
```

`--json` on any command for machine-readable output. Full reference: `agent-browser --help` and the upstream README.

## Recipes

**Record an e2e flow** (e.g. evidence for a UI bug report):

```bash
agent-browser --profile ~/.agent-browser-profiles/myapp open https://myapp.test
agent-browser record start flow.webm
# ... drive the flow via snapshot/click/fill ...
agent-browser record stop
```

**Mock an external API during a flow** — the answer to "test the UI without hitting the real vendor":

```bash
agent-browser network route "**/api.vendor.com/**" --body '{"ok":true}'
# drive the flow; the page sees the mock
agent-browser network unroute "**/api.vendor.com/**"
```

**Reuse a login across runs** (repo-local, gitignored):

```bash
agent-browser open https://myapp.test/login   # log in once (headed: --headed)
agent-browser state save .browser/auth.json
# later runs:
agent-browser --state .browser/auth.json open https://myapp.test/dashboard
```

**Render + validate a static HTML artifact** (design references, mockups) at multiple widths, and catch page-level horizontal overflow that `overflow-x:hidden` would hide:

```bash
F="file://$PWD/page.html"
agent-browser --session r open "$F"
agent-browser --session r set viewport 1440 1024 && agent-browser --session r screenshot --full desktop.png
agent-browser --session r set viewport 390 844  && agent-browser --session r screenshot --full narrow.png
# overflow check — measure documentElement, NOT body: body.scrollWidth can read clean while the page overflows
agent-browser --session r eval 'JSON.stringify({iw:innerWidth, sw:document.documentElement.scrollWidth, overflow:document.documentElement.scrollWidth>innerWidth})'
agent-browser --session r close
```

- Use `screenshot --full` for the whole page — Chrome's own `--headless --screenshot` captures only the viewport.
- If `documentElement.scrollWidth > innerWidth` but `body.scrollWidth` looks fine, an absolutely-positioned descendant (e.g. an `sr-only`/visually-hidden cell) is escaping a horizontally-scrolling container; give that container `position:relative` rather than papering over it with a width hack.

**Screenshot an animated drawer / Sheet / Dialog** (shadcn/reka-ui `slide-in`) — headless Chromium throttles the open animation, so the panel stays translated off-screen (`getBoundingClientRect().left === innerWidth`) and the capture is blank or right-clipped; `wait --idle` also times out when an HMR websocket keeps the page busy. Force it open before capturing:

```bash
agent-browser open https://myapp.test/page
# click the trigger scoped to ITS row — closest('tr'); going N parents up matches a container holding every row and opens the wrong one
agent-browser eval "(() => { const b=[...document.querySelectorAll('button')].find(x => x.closest('tr')?.textContent.includes('Target Name')); b.click(); })()"
agent-browser wait --text "Workflow run"
agent-browser eval '(() => { const d=document.querySelector("[role=dialog]"); if (d) { d.style.animation="none"; d.style.transition="none"; d.style.transform="none"; } })()'
agent-browser screenshot /abs/path/drawer.png      # positional, ABSOLUTE path
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `command not found` after install | Stale bin symlink from another tool's vendored copy | `rm $(which agent-browser); npm i -g agent-browser` |
| Profile flags seem ignored | Pre-0.2x version | `npm i -g agent-browser@latest` (`--state`/`--session-name` landed in 0.2x) |
| `Unknown command: viewport` (or `device`/`media`) | Those are `set` subcommands | `agent-browser set viewport <w> <h>` — same for `set device`, `set media` |
| Refs go stale | Page changed since snapshot | Re-run `snapshot -i` after every navigation/mutation |
| Can't trace a profile session | Profile ⊕ CDP exclusivity | Use the `vd:browser` trio when trace evidence is required |
| Logins vanish on real-Chrome profile reuse | macOS keychain cookie encryption | Dedicated automation profile, log in once there |
| Sheet/Dialog drawer captured blank or right-clipped | Headless throttles the `slide-in` enter-animation; drawer stuck translated off-screen | Force `transform/animation/transition:none` on `[role=dialog]` via `eval` before `screenshot` (see Recipes) |
| `screenshot -o file.png` saves to a temp dir instead | `-o` is not a flag; usage is `screenshot [selector] [path]` | Pass a positional, **absolute** path (relative paths resolve to the daemon cwd, not yours) |
| Daemon pinned to a stale tab; flags ignored after `close` | Half-dead daemon kept the old session | `pkill -9 -f agent-browser; rm ~/.agent-browser/default.*`, then reopen (add `--ignore-https-errors` for Herd/self-signed TLS) |

## Security

- `state` files and profile dirs are bearer credentials: gitignore `.browser/`, never commit, never print.
- `network route` mocks are visible app-wide in that session — unroute before measuring anything real.

## Integration points

- **`vd:web-e2e`** — flows that need video or mocking can run on this driver; note in the flow file that trace assertions don't apply.
- **`vd:browser`** — the default driver; this skill is the documented alternative, not a replacement.
- **`vd:gopass`** — credential source for scripted logins.

## Future (deliberately out of scope for MVP)

- Browserbase cloud recipes beyond `-p browserbase` (the `vd:browser` skill owns cloud contexts).
