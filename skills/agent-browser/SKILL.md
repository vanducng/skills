---
name: agent-browser
description: Drive web pages with the agent-browser CLI (Playwright engine) - the primary local browser driver. Connect over CDP to the shared browser-profile Chrome (the hands of vd:web-e2e), or run standalone with --profile isolation. Snapshot with @e refs, fill/click, video recording, network mocking, deterministic batch replay. Use when the user says "agent-browser", "record a video of the flow", "mock that API call in the browser", or asks for browser automation with built-in waiting.
license: MIT
compatibility: Requires agent-browser pinned at 0.27.2 (`npm install -g agent-browser@0.27.2`) and a one-time `agent-browser install` for standalone Chromium. Connect mode needs a browser-profile Chrome with a live CDP port.
argument-hint: "[url or flow description]"
metadata:
  author: vanducng
  version: "0.2.0"
  attribution: wraps vercel-labs/agent-browser; command-surface notes adapted from claudekit agent-browser (Apache-2.0)
---

# agent-browser

The primary local browser driver in this catalog. In **connect mode** it attaches over CDP to the real Chrome launched by `vd:browser-profile` - persistent human-shared login, Google OAuth in a real browser, and `vd:browser-trace` observing the same session as a second CDP client (verified coexisting). That combination is the hands of `vd:web-e2e`. Its own **`--profile` mode** remains for standalone tasks that want isolation from the shared Chrome. `vd:browser` (Browserbase) is the remote escalation for CAPTCHA/anti-bot/proxy walls, not the default driver.

Pick per task, not per preference:

| Need | Use |
|---|---|
| e2e flows against a local app: shared login, human window, trace evidence | this skill in connect mode, via `vd:web-e2e` |
| Standalone automation, scratch rendering, per-identity isolated profiles | this skill with `--profile` or `--session` |
| Drive the profile Chrome *and* record video | connect mode - `record` works over CDP in 0.27.2 (see caveat below) |
| CAPTCHA, anti-bot, residential proxies, Browserbase Identity/contexts | `vd:browser` (remote escalation) |

## Prerequisites

```bash
which agent-browser || npm install -g agent-browser@0.27.2
agent-browser --version          # 0.27.2 pinned - the validated surface (see Verified facts)
agent-browser install            # one-time Chromium download; standalone --profile mode only
```

A background daemon (socket under `~/.agent-browser/`) keeps the browser alive between invocations; `idleTimeout` in `agent-browser.json` controls auto-shutdown.

The pin is deliberate: the facts below (positional screenshot path, `har stop <path>`, screencast `record`, `errors --json`, same-origin-only mocks) were validated live against 0.27.2. Before upgrading, re-run that capability checklist - do not assume the surface held.

## Connect to the shared profile Chrome (primary mode)

Canonical: the `vd:browser-profile` skill's attach wrapper, which sanitizes the environment and verifies the attachment for you:

```bash
profile-attach.sh <name>         # from vd:browser-profile scripts/
```

Manual equivalent - both steps are mandatory:

```bash
env -u AGENT_BROWSER_PROFILE agent-browser connect <port>
env -u AGENT_BROWSER_PROFILE agent-browser eval 'navigator.userAgent'
# must NOT contain "HeadlessChrome" - if it does, you are driving the wrong browser; stop
```

**The `AGENT_BROWSER_PROFILE` footgun.** If a shell rc exports `AGENT_BROWSER_PROFILE`, every command silently drives a self-launched headless profile browser instead of the CDP Chrome - with success exit codes. Nothing fails; the real Chrome just never moves. This is undetectable without the UA check. Sanitize with `env -u AGENT_BROWSER_PROFILE` on every call, or `unset AGENT_BROWSER_PROFILE` once in the session. One poisoned invocation also swaps the daemon's default session away from the CDP Chrome; recover with `agent-browser close --all`, then reconnect and re-verify.

## Teardown - close what you launched

**End every session by releasing the browser.** The background daemon keeps Chrome (and its
authenticated session) alive between invocations, so a skipped teardown leaks a live logged-in
window into the next run - and the next agent. This is a required last step, not an optional nicety.

- **You launched the profile Chrome** (via `vd:browser-profile` `profile-open.sh <name>`, i.e.
  it was not already running): close it when done - `profile-close.sh <name>`.
- **You attached to a Chrome the human already had open**: do NOT close their window - just drop
  the daemon's session with `agent-browser close` (or `close --all` to recover a poisoned default
  session) so the next attach starts clean.
- **Standalone `--profile` / `--session <name>`**: `agent-browser --session <name> close`, or a
  bare `agent-browser close` for the default session, tears down the disposable Chromium.

Rule of thumb: **if you opened it, you close it** - and run teardown even when the flow failed. A
half-driven, still-open authenticated window is a security and correctness hazard, not just clutter.

## Verified 0.27.2 facts

| Surface | Rule |
|---|---|
| `screenshot` | Positional **absolute** path only - `-o` is not a flag; relative paths resolve to the daemon cwd |
| HAR | `network har start`, then `network har stop <abs path>`. That is the ONLY permitted form: `har start <path>` misparses - it saves to `~/.agent-browser/tmp/har/` AND opens a surprise auto-navigated tab in the shared authenticated Chrome (a safety issue, not a nit) |
| `errors` | Always `errors --json` - the plain form prints a bare `✗` with no detail |
| `network route` mocks | Same-origin only; no `--header` in 0.27.2, so cross-origin mocks die on CORS. Workaround: `eval`-patch `window.fetch` for the cross-origin host |
| `record` over connect | Works in 0.27.2 (screencast-based, undocumented upstream) - may regress on upgrade; do not build trace evidence on it, `vd:browser-trace` owns traces |
| `wait --url` | Can time out on SPA/Inertia navigations that actually succeeded - verify with `get url` instead of trusting the timeout |

## Quick start

Against the shared Chrome (after connect + UA verification above):

```bash
agent-browser open https://myapp.test/login
agent-browser snapshot -i                  # interactive elements with @e refs
agent-browser fill @e2 "user@example.com"
agent-browser fill @e3 "secret"
agent-browser click @e1
agent-browser get url                      # post-navigation check; do not rely on wait --url for SPAs
```

## Deterministic replay (batch)

`agent-browser batch --bail "cmd1" "cmd2" ...` runs commands in sequence, stops on the first failing step, and makes the exit code the verdict - no model in the loop. It takes quoted command strings as arguments (or a JSON array of argv arrays on stdin) - **not a file path**. `vd:web-e2e` stores flows as newline-separated `.batch` files and runs them with:

```bash
grep -v '^#' flow.batch | grep -v '^$' | tr '\n' '\0' | xargs -0 agent-browser batch --bail
```

Rules for a deterministic batch:

- Stable locators only: CSS selectors or `find role|text|label|testid <value>`. Never `@e` refs - they are snapshot-order-dependent and change across runs.
- Mechanical verdicts after the batch, jq-checkable: `agent-browser errors --json` must be `[]`; `agent-browser get url` must match the flow's terminal URL; failed requests via `network requests --json` or `network har stop <abs path>`.

## Auth persistence - standalone modes

In connect mode auth is not agent-browser's problem: the session lives in the browser-profile Chrome the human logged into. The mechanisms below apply to standalone use:

| Mechanism | What persists | When |
|---|---|---|
| `--profile <dir>` / `AGENT_BROWSER_PROFILE` | Everything (launchPersistentContext: cookies, localStorage, service workers) | Long-lived standalone logins; use a dedicated dir under `~/.agent-browser-profiles/<context>` - never a real Chrome profile (macOS keychain encryption breaks it) |
| `state save/load <file>` or `--state` | Cookies + storage snapshot | Portable, per-repo (gitignored `.browser/auth.json` convention); pairs with CI - `vd:web-e2e` CI runs feed a `profile-export.sh` storageState here |
| `--session-name <name>` | Auto-saved/restored session state | Convenience for recurring tasks |

Profile mode still excludes `--cdp`, `--state`, and extensions - documented upstream, not a bug to debug. The standardized e2e stack sidesteps the exclusivity entirely by using connect mode against a real Chrome.

### Named profiles - one per identity context

Keep a separate persistent profile per identity (work org, client, personal) so the right account logs into the right service: `~/.agent-browser-profiles/<context>`. An explicit `--profile` flag wins over the `AGENT_BROWSER_PROFILE` fallback - and remember that fallback poisons connect mode (see the footgun above). A repo may pin its profile via project memory or a repo-local skill - check there first.

**Before driving any authenticated service standalone: confirm the profile with the user.** If the task touches a login-bearing site and the profile choice wasn't already pinned (memory/repo skill/explicit user instruction), open the target URL **headed** with the candidate profile and ask the user to confirm it's the right identity - and to complete login (SSO/2FA) in that window if the session is missing:

```bash
agent-browser close   # daemon holds one profile; restart to switch
agent-browser --profile ~/.agent-browser-profiles/<context> --headed open https://target.example
# pause → user confirms profile / logs in once → session persists in the profile dir
```

Do not guess between profiles; a wrong-identity action on a real service is hard to undo.

## Command surface (high-traffic subset)

```bash
agent-browser connect <port>                             # attach to CDP Chrome (env -u AGENT_BROWSER_PROFILE!)
agent-browser snapshot -i | -c | -d 3 | -s "nav"        # refs, compact, depth, scoped
agent-browser click|dblclick|hover @e1 · fill|type @e2 "text" · press Enter
agent-browser get text|html|value|attr|title|url|count|box [@ref|selector]
agent-browser wait @e1 | --text "Done" | --idle | --fn "() => window.ready"   # avoid --url on SPAs
agent-browser find role|text|label|placeholder|testid <value>
agent-browser screenshot [selector] [path] [--full]    # positional path (NOT -o); pass an ABSOLUTE path · pdf -o page.pdf
agent-browser record start [out.webm] · record stop · record restart
agent-browser network route "**/api/*" --body '{"data":[]}' · --abort · network requests --json
agent-browser network har start · network har stop /abs/path/trace.har        # NEVER har start <path>
agent-browser errors --json · console --json
grep -v '^#' flow.batch | grep -v '^$' | tr '\n' '\0' | xargs -0 agent-browser batch --bail   # deterministic replay
agent-browser cookies|storage local|state save f.json
agent-browser set viewport 1920 1080 · set device "iPhone 14" · set media dark   # browser-settings are `set` subcommands
agent-browser tabs · tab new|<n>|close · frame <n> · dialog accept · eval "expr"
agent-browser --session <name> ...                       # parallel isolated instances
```

`--json` on any command for machine-readable output. Full reference: `agent-browser --help` and the upstream README.

## Recipes

**Record an e2e flow** (e.g. evidence for a UI bug report) - works both connected to the shared Chrome and standalone:

```bash
agent-browser record start flow.webm
# ... drive the flow via snapshot/click/fill ...
agent-browser record stop
```

**Mock a same-origin API during a flow** - the answer to "test the UI without hitting the real endpoint":

```bash
agent-browser network route "**/api/**" --body '{"ok":true}'
# drive the flow; the page sees the mock
agent-browser network unroute "**/api/**"
```

Cross-origin hosts fail on CORS in 0.27.2 (no `--header`). Workaround: `eval` a `window.fetch` patch that short-circuits the vendor host before driving the flow.

**Reuse a login across standalone runs** (repo-local, gitignored):

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
agent-browser --session r set viewport 1440 1024 && agent-browser --session r screenshot --full /abs/path/desktop.png
agent-browser --session r set viewport 390 844  && agent-browser --session r screenshot --full /abs/path/narrow.png
# overflow check - measure documentElement, NOT body: body.scrollWidth can read clean while the page overflows
agent-browser --session r eval 'JSON.stringify({iw:innerWidth, sw:document.documentElement.scrollWidth, overflow:document.documentElement.scrollWidth>innerWidth})'
agent-browser --session r close
```

- Use `screenshot --full` for the whole page - Chrome's own `--headless --screenshot` captures only the viewport.
- If `documentElement.scrollWidth > innerWidth` but `body.scrollWidth` looks fine, an absolutely-positioned descendant (e.g. an `sr-only`/visually-hidden cell) is escaping a horizontally-scrolling container; give that container `position:relative` rather than papering over it with a width hack.

**Screenshot an animated drawer / Sheet / Dialog** (shadcn/reka-ui `slide-in`) - headless Chromium throttles the open animation, so the panel stays translated off-screen (`getBoundingClientRect().left === innerWidth`) and the capture is blank or right-clipped; `wait --idle` also times out when an HMR websocket keeps the page busy. Force it open before capturing:

```bash
agent-browser open https://myapp.test/page
# click the trigger scoped to ITS row - closest('tr'); going N parents up matches a container holding every row and opens the wrong one
agent-browser eval "(() => { const b=[...document.querySelectorAll('button')].find(x => x.closest('tr')?.textContent.includes('Target Name')); b.click(); })()"
agent-browser wait --text "Workflow run"
agent-browser eval '(() => { const d=document.querySelector("[role=dialog]"); if (d) { d.style.animation="none"; d.style.transition="none"; d.style.transform="none"; } })()'
agent-browser screenshot /abs/path/drawer.png      # positional, ABSOLUTE path
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Commands succeed but the real Chrome never moves | `AGENT_BROWSER_PROFILE` exported in the shell - driving a self-launched headless browser | `env -u AGENT_BROWSER_PROFILE` on every call (or `unset`), then `agent-browser close --all`, reconnect, verify `eval 'navigator.userAgent'` has no HeadlessChrome |
| `connect` attached but session acts headless | Daemon default session poisoned by a prior profile invocation | `agent-browser close --all`, reconnect with sanitized env, re-verify UA |
| `wait --url` times out but the app clearly navigated | SPA/Inertia navigation does not always satisfy the URL matcher | Assert with `get url` instead |
| A surprise tab opened in the shared Chrome after a HAR command | `har start <path>` misparse auto-navigates a remembered URL | Only ever `har start` (bare) then `har stop <abs path>` |
| `command not found` after install | Stale bin symlink from another tool's vendored copy | `rm $(which agent-browser); npm i -g agent-browser@0.27.2` |
| `Unknown command: viewport` (or `device`/`media`) | Those are `set` subcommands | `agent-browser set viewport <w> <h>` - same for `set device`, `set media` |
| Refs go stale | Page changed since snapshot | Re-run `snapshot -i` after every navigation/mutation; use CSS/`find` locators in batch files |
| Batch flow passes locally, fails on replay | `@e` refs baked into the batch file | Rewrite with CSS or `find role|text|label|testid` locators - refs are non-deterministic |
| Can't trace a `--profile` session | Profile ⊕ CDP exclusivity (still true in 0.27.2) | Use connect mode against the browser-profile Chrome - `vd:browser-trace` attaches as a second CDP client there |
| Logins vanish on real-Chrome profile reuse | macOS keychain cookie encryption | Dedicated automation profile, log in once there |
| Sheet/Dialog drawer captured blank or right-clipped | Headless throttles the `slide-in` enter-animation; drawer stuck translated off-screen | Force `transform/animation/transition:none` on `[role=dialog]` via `eval` before `screenshot` (see Recipes) |
| `screenshot -o file.png` saves to a temp dir instead | `-o` is not a flag; usage is `screenshot [selector] [path]` | Pass a positional, **absolute** path (relative paths resolve to the daemon cwd, not yours) |
| Daemon pinned to a stale tab; flags ignored after `close` | Half-dead daemon kept the old session | `pkill -9 -f agent-browser; rm ~/.agent-browser/default.*`, then reopen (add `--ignore-https-errors` for Herd/self-signed TLS) |

## Security

- `state` files and profile dirs are bearer credentials: gitignore `.browser/`, never commit, never print.
- `network route` mocks are visible app-wide in that session - unroute before measuring anything real.
- In connect mode you are driving a real authenticated Chrome the human also uses: never run the forbidden `har start <path>` form, and treat unexpected navigations as incidents, not noise.

## Integration points

- **`vd:web-e2e`** - this skill in connect mode is its hands: agent-executed flows plus deterministic `.batch` replays.
- **`vd:browser-profile`** - launches the shared Chrome and owns `profile-attach.sh`, the canonical env-sanitized connect + UA verification.
- **`vd:browser-trace`** - raw-CDP observer that coexists with this driver on the same Chrome; use it when trace evidence is required.
- **`vd:browser`** - Browserbase remote escalation when a local run hits CAPTCHA/anti-bot walls; not the default driver.
- **`vd:gopass`** - credential source for scripted logins.

## Future (deliberately out of scope)

- Browserbase cloud recipes (`vd:browser` owns cloud sessions, Identity, and contexts).
