# Web vitals - thresholds and diagnosis

## Thresholds (75th percentile targets)

| Metric | Good | Needs improvement | Poor | Measures |
|---|---|---|---|---|
| LCP | ≤ 2.5s | 2.5-4s | > 4s | Loading - largest text/image render |
| INP | ≤ 200ms | 200-500ms | > 500ms | Interactivity - worst interaction latency (replaced FID in 2024) |
| CLS | ≤ 0.1 | 0.1-0.25 | > 0.25 | Visual stability - unexpected layout shifts |
| FCP | ≤ 1.8s | 1.8-3s | > 3s | First paint of any content |
| TTFB | ≤ 800ms | 0.8-1.8s | > 1.8s | Server/network - first response byte |

Lab numbers from `vitals.cjs` are single-sample and environment-dependent - useful for regressions and diagnosis, not for claiming field (CrUX) performance.

## Diagnosis by metric

**High TTFB** - server-side: slow controller/query, no opcache, cold container. Confirm with the app's own profiler before touching the frontend; nothing downstream can compensate for a slow first byte.

**High LCP, fine TTFB** - find the LCP element (DevTools → Performance → LCP marker in the trace from `perf-trace.cjs`). Usual suspects: render-blocking CSS/JS in `<head>`, hero image without `fetchpriority="high"`/preload, client-side rendering waterfalls (SPA fetches after JS boot - visible as a gap between FCP and LCP). The `resources` summary from `vitals.cjs` shows transfer volume; the trace shows ordering.

**High INP** - long main-thread tasks during interactions. `perf-trace.cjs`'s long-task list (>50ms `RunTask`) names them; in the flame chart look for wide `FunctionCall`/`V8.Execute` blocks under the interaction. Fixes: split work with `setTimeout`/`scheduler.yield`, debounce input handlers, virtualize big lists. Remember: INP needs real interactions - drive the page first.

**High CLS** - images/iframes without dimensions, late-loading fonts (FOUT reflow), content injected above existing content. Each `layout-shift` entry is in the trace; `hadRecentInput` shifts are excluded from the score by design.

**Heap growth across a flow** - run `vitals.cjs` (no `--url`) before and after repeating an action; steadily climbing `usedMB`/`nodes` with no recovery indicates leaked listeners/detached DOM. Confirm with a DevTools heap snapshot - this skill flags, it doesn't prove.

## Warm vs cold

A persistent profile has primed caches, service workers, and HTTP/3 connection reuse - its numbers answer "how fast is the app for a returning logged-in user", which is usually the right e2e question. For first-visit numbers use a fresh profile (`profile-open.sh <new-name>`), and label which mode a report's numbers came from.

## Reading the trace

Load `trace.json` in DevTools → Performance → Load profile. Priority order: long tasks (red corners) → network waterfall gaps → forced reflows (purple `Layout` under script). The `topByTotalDuration` summary from `perf-trace.cjs` tells you which lane to inspect first.
