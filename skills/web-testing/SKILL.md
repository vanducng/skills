---
name: web-testing
description: Headless Playwright replay for local web apps — scaffold a Playwright e2e suite whose logged-in identity comes from a vd:browser-profile storageState export, run it in CI, and parse Playwright/Vitest/JUnit results into one verdict. Use when the user says "set up playwright", "headless e2e", "run e2e in CI", "replay the logged-in session headless", "analyze test results", or wants the vd:web-e2e flows runnable without a headed browser.
license: MIT
compatibility: Requires Node 18+ and @playwright/test (project-local `npm i -D @playwright/test` + `npx playwright install chromium`). Identity export needs vd:browser-profile.
argument-hint: "[init|analyze] (run from the app repo; init reads .e2e/config.json)"
metadata:
  author: vanducng
  version: "0.1.0"
  attribution: scaffolder and results-parser patterns adapted from claudekit web-testing (Apache-2.0)
---

# web-testing

The headless layer of the e2e stack. `vd:web-e2e` drives a real headed Chrome through a persistent profile — ideal interactively, but useless in CI. This skill replays the same identity headless: `profile-export.sh` dumps the profile's cookies + localStorage as a Playwright `storageState`, and the scaffolded suite consumes it, so the human's one-time login powers unattended runs too.

Persistent-context headless is deliberately not used — it's flaky upstream and Chrome 136+ restricts CDP on default dirs. storageState is the supported, portable path.

## What this skill is — and isn't

| Skill | Role |
|---|---|
| `vd:web-e2e` | Interactive e2e: headed profile, agent-driven flows, trace evidence |
| `vd:web-testing` (this) | Unattended replay: Playwright suite + storageState identity + results verdict |
| `vd:browser-profile` | The identity source — `profile-export.sh` bridges the two |

**Not for:** unit tests (run the project's runner directly), interactive flow debugging (`vd:web-e2e`), load/k6 or a11y audits (out of scope by design).

## Quick start

```bash
SKILL="${CLAUDE_SKILL_DIR:-$(for d in "$HOME/skills/skills/web-testing" "$HOME/.claude/skills/web-testing" "$HOME/.agents/skills/web-testing"; do [ -d "$d" ] && { echo "$d"; break; }; done)}/scripts"
BP="$(for d in "$HOME/skills/skills/browser-profile" "$HOME/.claude/skills/browser-profile" "$HOME/.agents/skills/browser-profile"; do [ -d "$d" ] && { echo "$d"; break; }; done)/scripts"

node "$SKILL/init-playwright.cjs"                       # reads .e2e/config.json for baseURL/TLS
npm i -D @playwright/test && npx playwright install chromium
"$BP/profile-export.sh" <profile> .e2e/storageState.json   # profile must be open + logged in
npx playwright test
node "$SKILL/analyze-test-results.cjs" --playwright test-results/results.json --output markdown
```

## Command reference

| Script | Purpose |
|---|---|
| `init-playwright.cjs [--dir <path>]` | Scaffold `playwright.config.ts` + smoke/logged-out specs. Inherits `baseUrl` and `insecureTLS` from `.e2e/config.json`; defaults `storageState` to `.e2e/storageState.json` (env `E2E_STORAGE_STATE` overrides); appends state/artifact paths to `.gitignore`. Idempotent — never overwrites. |
| `analyze-test-results.cjs --playwright\|--vitest <json> \| --junit <xml> [--output text\|json\|markdown] [--fail-threshold <pct>]` | Unified summary across runners; exit 1 on any failure or below threshold. Markdown mode drops straight into a `vd:web-e2e`-style report. |

## Workflow

1. Scaffold once (`init-playwright.cjs`), install Playwright project-local — version skew between a global install and cached browsers causes "Executable doesn't exist"; project-local + `npx playwright install chromium` avoids it.
2. Export identity: `profile-export.sh <profile> .e2e/storageState.json`. Re-export whenever sessions expire (short-lived JWTs: every run; Laravel remember-me: rarely).
3. `npx playwright test` against the already-running app (`e2e.cjs status --wait` first — Playwright does not boot the app; that contract lives in `vd:web-e2e`).
4. Verdict: `analyze-test-results.cjs --output markdown` into the run report.
5. CI: see `references/ci-replay.md` for GH Actions + storageState-as-secret handling.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Every spec redirects to /login | storageState stale (expired JWT/session) | Re-export from an open, logged-in profile; for 8h JWTs export at run start |
| `Executable doesn't exist` | @playwright/test version ≠ cached browser build | Project-local install + `npx playwright install chromium` |
| TLS errors on `*.test` | Herd CA not in Node | Scaffold sets `ignoreHTTPSErrors` when `.e2e/config.json` has `insecureTLS` |
| Suite passes locally, fails in CI | App not booted / seeded in CI | Gate on the app's health endpoint before `playwright test`; seed deterministically (`references/test-data-management.md`) |
| Random failures | Timing-dependent waits | `references/test-flakiness-mitigation.md` |

## Security

- `storageState.json` is bearer credentials — gitignored by the scaffold, `chmod 600` by the exporter, never commit or log it. In CI, inject via secret store, not artifacts.

## Integration points

- **`vd:web-e2e`** — same `.e2e/` contract; flows verified interactively graduate into specs here.
- **`vd:browser-profile`** — `profile-export.sh` is the identity bridge.
- **`vd:ship` / CI** — `analyze-test-results.cjs --fail-threshold` as a pipeline gate.

## Future (deliberately out of scope for MVP)

- Auto re-export on expiry (needs an open profile — interactive by nature).
- Visual-regression baselines wired into reports (`references/visual-regression.md` covers the technique).
