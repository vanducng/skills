---
name: web-e2e
description: Full end-to-end browser testing for local web apps with a persistent logged-in session. Log in once into a named Chrome profile, then drive real flows with trace evidence against your locally served app — Laravel/Herd, docker compose, FastAPI+SPA, Vite. Adds per-project orchestration via .e2e/config.json — boot + health checks, process checks (queue workers), auth-state probing, flow files, pass/fail reports. Use when the user says "e2e test", "end-to-end test the app", "test this flow in the browser", "open the app logged in", or wants browser tests that remember credentials and cookies across runs.
license: MIT
allowed-tools: Bash, Read, Write
compatibility: Requires Node 18+, the browse CLI (`npm install -g @browserbasehq/browse-cli`), and Google Chrome. Builds on vd:browser-profile and vd:browser-trace. macOS-first (Chrome path overridable via BROWSER_PROFILE_CHROME).
argument-hint: "[status|--wait|flow-name] (run from the app repo; reads .e2e/config.json)"
metadata:
  author: vanducng
  version: "0.1.0"
---

# web-e2e

The orchestration layer for browser e2e against locally running web apps. Three sibling skills already provide the primitives — `vd:browser-profile` (persistent logged-in Chrome, one deterministic CDP port per profile), `vd:browser` (drive pages via snapshot + `@refs`), `vd:browser-trace` (read-only evidence capture on the same port). This skill sequences them per project: is the app up, is the session authenticated, run the flow, judge it with evidence.

Why this composition and not `agent-browser --profile`? agent-browser's profile mode is documented as mutually exclusive with CDP connections — no trace capture, no human-shareable window, no second observer. The browser-profile + CDP trio is the only stack where persistence, a human doing the one-time OAuth login, programmatic driving, and tracing all coexist on one port. agent-browser remains a fine alternative when you need its video recording and don't need traces.

## What this skill is — and isn't

| Skill | Role |
|---|---|
| `vd:browser-profile` | The session — named persistent profile, login survives across runs |
| `vd:browser` | The hands — navigate, snapshot, click, fill over CDP |
| `vd:browser-trace` | The eyes — network/console/screenshot evidence into `.o11y/` |
| `vd:web-e2e` (this) | The playbook — per-project config, readiness, auth state, flows, verdicts |

Alternatives: `agent-browser` (Playwright engine, video, `--profile`/`--state`) and Puppeteer-based chrome-devtools scripts work, but their persistence mechanisms don't share a window or port with the human or the tracer.

## When to use

- "Run the smoke flow against local", "e2e test the signup flow", "verify this change in the real app, logged in".
- Apps where login is expensive or impossible to script — Google-OAuth-only logins make a persistent profile the *only* repeatable path.
- Before shipping UI changes: drive the real flow with trace evidence instead of trusting unit tests.

**Not for:** server-side test suites (Pest/pytest/vitest — run them directly), cloud/anti-bot scraping (`vd:browser --remote`), or one-shot page checks with no auth (plain `vd:browser`).

## Prerequisites

```bash
node --version        # 18+
which browse || npm install -g @browserbasehq/browse-cli   # NOT registry "browse" — different CLI, lacks `env`
which jq || brew install jq   # optional, nicer JSON
```

## Quick start — zero config

The user's core need first: a browser that remembers creds/cookies every time. No config file required.

```bash
BP=$HOME/.claude/skills/browser-profile/scripts

"$BP/profile-open.sh" myapp-dev      # headed Chrome opens
# → human logs in ONCE (Google OAuth, MFA, whatever) in that window
"$BP/profile-attach.sh" myapp-dev    # browse daemon now points at that window
browse open https://myapp.test/dashboard
browse snapshot                      # still logged in — today, tomorrow, next month
```

Remember-me cookies live in the profile dir; with session-refresh on visit, weeks pass between logins.

## Make it repeatable — `.e2e/config.json`

The per-project layer encodes what cannot be detected: how the app boots, what "healthy" means, which auth strategy applies, where the login lives. Copy the closest example and edit (~15 lines):

- `references/examples/laravel-herd.config.json` — Herd-served, OAuth-only login, queue-worker check
- `references/examples/compose-spa.config.json` — docker compose boot, readyz gate, form login

```
<repo>/.e2e/
├── config.json     # the contract below
└── flows/
    └── smoke.md    # agent-executable flow files (see references/flows-and-reports.md)
```

Schema (only non-derivable facts; commit it — no secrets allowed, see Security):

| Field | Meaning |
|---|---|
| `name`, `baseUrl` | App identity and origin under test |
| `profile` | `vd:browser-profile` profile name holding the logged-in session |
| `insecureTLS` | `true` for Herd `*.test` certs (Node can't see the system keychain; Node ≥22.15 alternative: `NODE_OPTIONS=--use-system-ca`) |
| `boot.up` / `boot.down` | Detaching shell commands (`make up`); absence = externally managed (Herd). Foreground servers are unsupported by design |
| `health[]` | GET-only checks: `{url, expect?, bodyContains?}`. Redirects are not followed — expect the 3xx explicitly |
| `checks[]` | `{name, cmd}` process checks, e.g. queue worker via `pgrep` — async flows silently hang without it |
| `auth` | `strategy` + `probeUrl` (an authed route) + `loginUrlPattern` (regex; include IdP origins like `accounts\.google\.com`) + per-strategy fields |

## Command reference

One script, one verb. `--json` for agent consumption.

```bash
E2E=$HOME/.claude/skills/web-e2e/scripts/e2e.cjs

node "$E2E" status            # health + checks + profile state + auth probe
node "$E2E" status --wait     # run boot.up first if unhealthy, then poll until green (--timeout 120)
node "$E2E" status --json     # full machine-readable result; exit 0 = READY
```

`status` probes auth by opening a tab in the profile window via the CDP HTTP API and watching where it lands (`loginUrlPattern` ⇒ logged-out; URL stable past a settle window ⇒ logged-in). The tab flashes briefly in the shared headed window — that's the probe, not a rogue agent. `probeUrl` must be side-effect-free under GET.

## Workflow

1. **Ready the app** — `node "$E2E" status --wait --json`. Fix what's red before touching the browser: failed health = app down; failed check = e.g. start `php artisan queue:listen` before async flows.
2. **Ensure auth** — on `logged-out`: `form` → drive the login form per `references/auth-strategies.md`; `token-inject` → always re-inject (skip probing); `oauth-interactive` → run `profile-open.sh <profile>` and ask the human to log in once, then re-run status. Never ask the human to run scripts — run them, ask only for the in-browser login.
3. **Start evidence** — `vd:browser-trace` `start-capture.mjs` against the profile's port (in `status --json` output).
4. **Drive the flow** — `profile-attach.sh <profile>`, then execute the flow file's steps with `browse open/snapshot/click/fill`. `browse fill` presses Enter by default — use `--no-press-enter` on every field except the final submit.
5. **Stop + bisect** — `stop-capture.mjs`, `bisect-cdp.mjs`; `query.mjs errors` for exceptions and failed requests.
6. **Verdict** — per-flow PASS/FAIL with absolute evidence paths, per `references/flows-and-reports.md`. Reports go to the hook-injected Reports path when present, else `<repo>/.e2e/runs/`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `auth: skipped — profile not running` | No Chrome on the profile's port | `profile-open.sh <profile>` (and log in if first time) |
| Probe says logged-in but app rejects requests | SPA guard only checks token *presence*; an expired JWT (e.g. 8h) passes the URL probe | Use `token-inject` strategy — it re-authenticates every run |
| `health FAIL ... -> 0` on `https://*.test` | Node doesn't trust Herd's CA | `"insecureTLS": true`, or Node ≥22.15 with `NODE_OPTIONS=--use-system-ca` |
| Flow "passes" but side effects never appear | Queue worker not running | Add a `checks[]` pgrep entry; start the worker |
| Another app answers on the profile port | cksum port collision (100 slots) | Rename one profile |
| External API calls fail mid-flow | Live third-party dependency (payments, voice APIs) | Mock at the network layer or scope the flow to exclude it |
| Probe says logged-in on a fresh profile | Cold SPA boot: the client-side redirect to `/login` fires *after* JS boot + an auth API round-trip, slower than the settle window | Raise `auth.settleMs` (default 3000); server-side-redirecting probe URLs (Laravel `/dashboard` 302) don't have this race |

Chrome ≥136 ignores `--remote-debugging-port` on the *default* profile dir — a forward-looking constraint browser-profile already satisfies with dedicated dirs. Don't "simplify" to the real Chrome profile; on macOS its cookies are keychain-encrypted and unreadable to automation anyway.

## Security

- Never put real credentials in `config.json`. `credentials.source: "gopass"` (path) or `"env"` (var name) for anything sensitive; `"inline"` strictly for dev-seeded throwaway users already public in the repo's README/seeders.
- Profile dirs and `storageState.json` exports are bearer credentials — never commit, never print.
- Flows run against your live dev database. Seeding/reset commands are deliberately not auto-run; trigger them explicitly per flow preconditions.

## Integration points

- **`vd:browser-profile` / `vd:browser` / `vd:browser-trace`** — the substrate; this skill never reimplements them.
- **`vd:worktree`** — per-worktree app instance + its own profile name = parallel e2e without port or cookie collisions.
- **`vd:gopass`** — credential source for `form` and `token-inject` strategies.
- **`vd:cook` / `vd:fix`** — use a flow run as the verification step after implementing or fixing UI-facing work.

## Future (deliberately out of scope for MVP)

- Headless CI replay via `profile-export.sh` storageState + Playwright.
- Port the deterministic pieces to the `vd` CLI once the workflow proves out.
- Cross-platform Chrome paths (inherits browser-profile's macOS-first stance).
