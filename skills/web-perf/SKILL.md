---
name: web-perf
description: Measure Core Web Vitals (LCP, CLS, INP, FCP, TTFB), JS heap, and record DevTools performance traces against a running Chrome - attaches to vd:browser-profile's deterministic CDP ports, no Puppeteer, no separate browser. Use when the user says "why is this page slow", "measure web vitals", "check LCP/CLS/INP", "record a performance trace", "profile page load", or wants performance evidence in an e2e run.
license: MIT
allowed-tools: Bash, Read
compatibility: Requires Node 22+ (global WebSocket) and a Chrome exposing a CDP port - typically a vd:browser-profile profile. No npm dependencies.
argument-hint: "[vitals|trace] --port <cdp-port> [--url <page>]"
metadata:
  author: vanducng
  version: "0.1.0"
  attribution: vitals/tracing approach adapted from claudekit chrome-devtools (Apache-2.0), Puppeteer replaced with raw CDP
---

# web-perf

Performance measurement that attaches to the browser you already have. `vd:browser-trace` is a read-only observer - it never sends CDP commands, so it can't compute vitals or drive Chrome's tracer. This skill is the *active* counterpart: two stdlib Node scripts that connect to a CDP port (a `vd:browser-profile` profile's deterministic port, or any `--remote-debugging-port` Chrome), evaluate buffered `PerformanceObserver`s in-page, and stream a DevTools-loadable `trace.json` out.

No Puppeteer, no bundled Chromium, no node_modules - measuring against the persistent profile means vitals reflect the *logged-in* app surface (authed dashboards, not marketing pages), with warm-cache caveats noted below.

## What this skill is - and isn't

| Skill | Role |
|---|---|
| `vd:browser-trace` | Passive evidence: network/console/screenshots, never interferes |
| `vd:web-perf` (this) | Active measurement: vitals, heap, Chrome tracing - sends CDP commands |
| `vd:agent-browser` | Driving: navigate/click/fill - pair it to create the interactions INP needs |

**Not for:** load testing (k6 territory), Lighthouse-style audits/scores, or production RUM.

## Quick start

```bash
SKILL="${CLAUDE_SKILL_DIR:-$(for d in "$HOME/skills/skills/web-perf" "$HOME/.claude/skills/web-perf" "$HOME/.agents/skills/web-perf"; do [ -d "$d" ] && { echo "$d"; break; }; done)}/scripts"
BP="$(for d in "$HOME/skills/skills/browser-profile" "$HOME/.claude/skills/browser-profile" "$HOME/.agents/skills/browser-profile"; do [ -d "$d" ] && { echo "$d"; break; }; done)/scripts"

"$BP/profile-open.sh" myapp-dev          # or reuse one that's already open
PORT=9382                                 # from profile-open output / e2e.cjs status --json

node "$SKILL/vitals.cjs" --port $PORT --url https://myapp.test/dashboard
node "$SKILL/perf-trace.cjs" --port $PORT --url https://myapp.test/dashboard --out trace.json
```

## Command reference

| Script | Purpose |
|---|---|
| `vitals.cjs --port <p> [--url <u>] [--match <tab-substring>] [--json]` | LCP/CLS/FCP/TTFB/INP (buffered observers), JS heap + DOM node counts (`Performance.getMetrics`), resource summary. Without `--url` it measures the page already loaded in the matched tab. |
| `perf-trace.cjs --port <p> --url <u> [--out trace.json] [--settle <ms>] [--json]` | Chrome tracing around a navigation (devtools.timeline categories), streamed to `trace.json` + long-task (>50ms) and top-cost summary. Open the file in DevTools → Performance → Load profile. |

## Workflow

1. Get a CDP port: an open profile (`e2e.cjs status --json` reports it) or `chrome --remote-debugging-port=NNNN --user-data-dir=<dedicated>` (Chrome 136+ refuses the default dir).
2. Baseline: `vitals.cjs --url <page>` on the cold path; re-run for the warm read. A persistent profile has a primed cache - for cold-cache numbers use a fresh profile or note "warm" in the report.
3. INP needs interactions: drive clicks/typing via `vd:browser` first, then `vitals.cjs` *without* `--url` (re-navigating clears interaction history). `INP: n/a` on a fresh load is correct.
4. Slow page? `perf-trace.cjs` around the navigation; the long-task summary names the top main-thread offenders, the trace file gives the flame chart.
5. In an e2e run, append the vitals JSON and trace path to the flow report as evidence (`vd:web-e2e` report convention).

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `no CDP endpoint on :<port>` | Profile not open / wrong port | `profile-open.sh <name>`; port = 9300 + cksum(name)%100 |
| `no page target matching ...` | `--match` substring misses every tab | Drop `--match` (most recent page tab is picked) or open the page first |
| LCP null on `--url` re-run | SPA soft-navigation doesn't re-emit LCP | Measure on a hard navigation (the `--url` path does one) |
| INP always null | No interactions in this page's lifetime | Drive real clicks first; measure without `--url` |
| Suspiciously fast numbers | Warm profile cache | Note warm-vs-cold; use a fresh profile for cold-path numbers |
| Trace huge / slow to end | Long settle on a busy page | Lower `--settle`; scope categories are already minimal |

## Security

- Read-only against your own local Chrome; never point it at a CDP port you don't own - a CDP connection can read any page state in that browser.
- Trace files can embed page URLs and timing of authed routes - treat as internal artifacts.

## Integration points

- **`vd:browser-profile`** - the deterministic port is the default attach target.
- **`vd:web-e2e`** - perf evidence slots into flow reports; run vitals after a flow's steps for interaction-aware INP.
- **`vd:browser-trace`** - both can attach to the same port simultaneously (tracer observes, this measures).

## Future (deliberately out of scope for MVP)

- CPU/network throttling presets (`Emulation.setCPUThrottlingRate`).
- Vitals budgets with pass/fail thresholds in `.e2e/config.json`.
