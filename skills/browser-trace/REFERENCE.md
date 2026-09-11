# Browser Trace - Reference

Technical reference for the capture pipeline, the bisect mapping, and the jq recipe library.

## Architecture

```
                       ┌──────────────────────────────────────┐
   main automation ──▶ │  Chrome CDP target                   │ ◀── tracer (this skill)
   (agent-browser,     └──────────────────────────────────────┘
    Playwright, …)          │                        │
        │                   ▼                        ▼
    drives page   cdp-firehose.mjs <target>   snapshot-loop.mjs <target>
                  (native WebSocket, one       (one persistent WebSocket)
                   event per line → raw.ndjson)  Page.captureScreenshot → screenshots/
                                                 Runtime.evaluate outerHTML → dom/
                                                 Runtime.evaluate location.href → index.jsonl
```

CDP allows multiple concurrent clients on the same target. The firehose is purely passive: it enables the observation domains and only listens, never sending a command that changes page state. The sampler issues read-only commands (`Page.captureScreenshot` and two `Runtime.evaluate` reads of `document.body.outerHTML` / `location.href`); it observes without driving the flow, so it cannot perturb the run.

Both pieces open their own `WebSocket` to the target via `cdpConnect` in `lib.mjs`, which resolves a port to a debuggable page target (`/json/list`, falling back to `/json/version`) or accepts a full `ws://`/`wss://` URL as-is. When given a port, it picks the *first* page target in `/json/list`, so a multi-tab Chrome traces whichever tab is listed first; pass the specific tab's `webSocketDebuggerUrl` to trace a particular tab. The firehose exits if its socket closes (keeping `raw.ndjson` gap-free); the sampler reconnects on the next tick.

## Scripts

All scripts read `O11Y_ROOT` (default `.o11y`) so runs land under `$O11Y_ROOT/<run-id>/`. They are Node ESM modules (`node` 18+) and depend only on the Node standard library, with no `npm install` step. `jq` is referenced throughout the docs for ad-hoc querying but the scripts themselves don't need it.

### `start-capture.mjs <target> [run-id] [interval-sec]`

Starts both background processes and writes `manifest.json`.

- `target` - port number (e.g. `9222`) or full WebSocket URL.
- `run-id` - optional; defaults to `YYYYMMDDTHHMMSSZ`.
- `interval-sec` - sampler period in seconds; default `2`.

Honours `O11Y_DOMAINS` (space-separated) to control which CDP domains the firehose enables. Default: `Network Console Runtime Log Page`. Add `DOM` for DOM tree mutations, `Performance` for navigation timing, `Security` for mixed-content/cert events.

PIDs are stored in `<run-dir>/.cdp.pid` and `<run-dir>/.loop.pid` so `stop-capture.mjs` can find them.

### `stop-capture.mjs <run-id>`

SIGTERM → 3s grace → SIGKILL on both background processes, then stamps `manifest.json` with `stopped_at`.

### `bisect-cdp.mjs <run-id>`

Slices `cdp/raw.ndjson` two ways, then writes `cdp/summary.json`:

1. **Session-wide** buckets at `cdp/<domain>/...` (legacy layout, always written; see [bisect map](#bisect-map) below).
2. **Per-page** buckets at `cdp/pages/<pid>/...`, indexed by top-level `Page.frameNavigated` boundaries. Pages are zero-padded so they lex-sort numerically (`000`, `001`, …). Within each page only non-empty bucket files are written so empty directories don't pollute search results.

`cdp/summary.json` carries the run-level rollup: `sessionId`, `duration` (wall-clock ms anchored to `manifest.started_at`), `totalEvents`, and a `pages[]` array. Each entry has `{pageId, url, startMs, endMs, durationMs, eventCount, domains, network}` - same shape as the per-page `summary.json`.

Idempotent: rerun safely. The `cdp/pages/` tree is wiped and rebuilt each call.

### `query.mjs <run-id> <subcommand> [args...]`

Reads the bisected output and prints either tabular text or NDJSON. Subcommands:

| Subcommand                                | Output                                                         |
| ----------------------------------------- | -------------------------------------------------------------- |
| `list`                                    | one-line page table (`pid`, `events`, `duration`, `url`)       |
| `summary`                                 | full `cdp/summary.json`                                        |
| `page <pid>`                              | per-page `summary.json`                                        |
| `page <pid> <bucket>`                     | cat `pages/<pid>/<bucket>.jsonl` (e.g. `network/failed`, `console/logs`, `raw`) |
| `errors [pid\|all]`                       | unified error stream across pages: network failed, runtime exceptions, console errors, log-level errors. Each line tagged with `pid` and `kind` |
| `hosts [pid\|all]`                        | top hosts by request count                                     |
| `host <hostname> [pid\|all]`              | every request/response for that hostname, prefixed with `[pid]` |
| `timeline`                                | ordered nav + lifecycle markers                                |

Bypassable with raw `jq`/`rg` against `cdp/summary.json` and `cdp/pages/<pid>/` once you know the layout.

### `snapshot-loop.mjs` *(internal)*

Invoked by `start-capture.mjs`; not meant to be called directly. Holds one persistent CDP connection for the whole run and loops at the configured interval, writing PNG (`Page.captureScreenshot`) + HTML (`Runtime.evaluate` of `document.body.outerHTML`) + an entry to `index.jsonl` (`Runtime.evaluate` of `location.href`) per tick. If the socket drops it reconnects on the next tick. DOM dumps go through a `.partial` temp file so a SIGTERM mid-write never leaves a 0-byte HTML behind; `stop-capture.mjs` sweeps any survivors.

## Bisect map

| File                                    | CDP method                       | What's in it                                                 |
| --------------------------------------- | -------------------------------- | ------------------------------------------------------------ |
| `cdp/network/requests.jsonl`            | `Network.requestWillBeSent`      | every outgoing request: url, method, headers, postData, requestId |
| `cdp/network/responses.jsonl`           | `Network.responseReceived`       | response status, headers, mimeType, remoteIPAddress, fromDiskCache |
| `cdp/network/finished.jsonl`            | `Network.loadingFinished`        | byte count + timestamp on success                            |
| `cdp/network/failed.jsonl`              | `Network.loadingFailed`          | errorText (e.g. `net::ERR_ABORTED`), `canceled`              |
| `cdp/network/websocket.jsonl`           | `Network.webSocket*`             | every WebSocket lifecycle event                              |
| `cdp/console/logs.jsonl`                | `Runtime.consoleAPICalled`       | `console.log/info/warn/error` with `args[]`                  |
| `cdp/console/exceptions.jsonl`          | `Runtime.exceptionThrown`        | unhandled JS errors with stack                               |
| `cdp/runtime/all.jsonl`                 | `Runtime.*`                      | execution-context create/destroy, binding calls, etc.        |
| `cdp/log/entries.jsonl`                 | `Log.entryAdded`                 | browser-level warnings (CSP, deprecation, mixed content)     |
| `cdp/page/navigations.jsonl`            | `Page.frameNavigated`            | each top-level + iframe navigation                           |
| `cdp/page/lifecycle.jsonl`              | `Page.lifecycleEvent`            | per-navigation milestones: `init`, `commit`, `DOMContentLoaded`, `load`, `firstPaint`, `firstContentfulPaint`, `firstMeaningfulPaint`, `networkAlmostIdle`, `networkIdle` |
| `cdp/page/frames.jsonl`                 | `Page.frame*`                    | frame attached/detached/started/stoppedLoading                |
| `cdp/page/dialogs.jsonl`                | `Page.javascriptDialog*`         | alert / confirm / prompt / beforeunload                      |
| `cdp/page/all.jsonl`                    | `Page.*`                         | catch-all for everything Page emits                          |
| `cdp/dom/all.jsonl`                     | `DOM.*`                          | tree mutations *(only populated if `O11Y_DOMAINS` adds `DOM`)* |
| `cdp/target/attached.jsonl`             | `Target.attachedToTarget`        | each new page/iframe target attached to the tracer         |
| `cdp/target/detached.jsonl`             | `Target.detachedFromTarget`      | each detach                                                  |

### Note on response bodies

The firehose does not embed response bodies: that would require a synchronous `Network.getResponseBody` round-trip per request, which the passive tracer deliberately avoids. If you need bodies, capture them from the driver side: `agent-browser network requests --json`, or `browse network on` (in the `browser` skill), which writes per-request directories with `request.json` + `response.json` including body. The two compose: driver-side body capture for payloads + `cdp-firehose.mjs` for the timeline.

## jq recipe library

All recipes assume `cd .o11y/<run-id>/cdp` for brevity.

### Network

```bash
# Top hosts by request count
jq -r '.params.request.url' network/requests.jsonl \
  | awk -F/ '{print $3}' | sort | uniq -c | sort -rn | head

# All XHR/fetch (exclude subresources)
jq -c 'select(.params.type == "XHR" or .params.type == "Fetch")' \
  network/requests.jsonl

# Slow responses (>1000ms) - join finished against requests by requestId
jq -s '
  (.[0] | map({(.params.requestId): .params.timestamp}) | add) as $start |
  .[1] | map(select(.params.encodedDataLength != null))
       | map({
           rid: .params.requestId,
           dur_ms: ((.params.timestamp - $start[.params.requestId]) * 1000 | floor),
           bytes: .params.encodedDataLength
         })
       | map(select(.dur_ms > 1000))
       | sort_by(-.dur_ms)
' network/requests.jsonl network/finished.jsonl

# All POST bodies that aren't form-encoded
jq -c 'select(.params.request.method == "POST")
       | {url: .params.request.url, body: .params.request.postData}' \
  network/requests.jsonl
```

### Console & exceptions

```bash
# Console errors with the originating url+line
jq -r 'select(.params.type == "error")
       | "\(.params.stackTrace.callFrames[0].url):\(.params.stackTrace.callFrames[0].lineNumber)\t\(.params.args[0].value // .params.args[0].description // "")"' \
  console/logs.jsonl

# Pretty-print every exception
jq -c '.params.exceptionDetails
       | {text, line: .lineNumber, url, stack: .stackTrace.callFrames[0:3]}' \
  console/exceptions.jsonl
```

### Page navigation

```bash
# Linear visit log
jq -r '.params.frame.url' page/navigations.jsonl

# Navigations only on the top frame (skip iframes)
jq -r 'select(.params.frame.parentId == null) | .params.frame.url' \
  page/navigations.jsonl
```

### Page lifecycle (timing milestones)

`Page.lifecycleEvent` fires per-navigation for `init`, `commit`, `DOMContentLoaded`, `load`, `firstPaint`, `firstContentfulPaint`, `firstMeaningfulPaint`, `networkAlmostIdle`, `networkIdle`. These only fire after `Page.setLifecycleEventsEnabled {enabled:true}`, which `cdp-firehose.mjs` sends whenever `Page` is in `O11Y_DOMAINS`; drop `Page` from the domain set and `lifecycle.jsonl` stays empty.

```bash
# Time-to-DOMContentLoaded and time-to-load per navigation (seconds since loader start)
jq -s '
  group_by(.params.loaderId) | map({
    loader: .[0].params.loaderId,
    init:               (map(select(.params.name == "init"))               | first | .params.timestamp // null),
    DOMContentLoaded:   (map(select(.params.name == "DOMContentLoaded"))   | first | .params.timestamp // null),
    load:               (map(select(.params.name == "load"))               | first | .params.timestamp // null),
    firstContentfulPaint: (map(select(.params.name == "firstContentfulPaint")) | first | .params.timestamp // null),
    networkIdle:        (map(select(.params.name == "networkIdle"))        | first | .params.timestamp // null)
  } | . + {
    ttDCL_s:  (if .DOMContentLoaded   and .init then (.DOMContentLoaded - .init) else null end),
    ttLoad_s: (if .load               and .init then (.load - .init) else null end),
    ttFCP_s:  (if .firstContentfulPaint and .init then (.firstContentfulPaint - .init) else null end),
    ttIdle_s: (if .networkIdle        and .init then (.networkIdle - .init) else null end)
  })
' page/lifecycle.jsonl
```

### Joining events to screenshots

`index.jsonl` (sibling of `cdp/`) holds the sampler index. To find the screenshot closest to a CDP event timestamp:

```bash
# Pick an exception timestamp (Runtime.exceptionThrown uses .params.timestamp in ms)
EVT_MS=$(jq -r '.params.timestamp' console/exceptions.jsonl | head -1)
EVT_ISO=$(date -u -r $((EVT_MS/1000)) +%Y%m%dT%H%M%SZ)

# Find the first screenshot >= that ISO timestamp
ls ../screenshots | sort | awk -v t="$EVT_ISO" '$0 >= t { print; exit }'
```

For a quick visual diff, open `../dom/<ts>.html` at the same timestamp.

## Per-page drill-down

The same recipes work scoped to a single page. Replace `cdp/<bucket>.jsonl` with `cdp/pages/<pid>/<bucket>.jsonl`, or use `query.mjs` for the common patterns.

```bash
RUN=.o11y/<run-id>

# Browse the page index quickly
jq '.pages | map({pageId, url, durationMs, eventCount})' $RUN/cdp/summary.json

# Pages with the most network errors
jq '.pages | map(select(.domains.Network.errors > 0))
            | map({pageId, url, errors: .domains.Network.errors})' \
  $RUN/cdp/summary.json

# Pages by event volume (hot pages)
jq '.pages | sort_by(-.eventCount) | .[:5] | map({pageId, url, eventCount})' \
  $RUN/cdp/summary.json

# All requests on page 2 grouped by type
jq -r '.params.type' $RUN/cdp/pages/002/network/requests.jsonl \
  | sort | uniq -c | sort -rn

# Did page 1 fire firstContentfulPaint?
jq -c 'select(.params.name == "firstContentfulPaint") | .params.timestamp' \
  $RUN/cdp/pages/001/page/lifecycle.jsonl

# All POST bodies submitted on page 3
jq -c 'select(.params.request.method == "POST")
       | {url: .params.request.url, body: .params.request.postData}' \
  $RUN/cdp/pages/003/network/requests.jsonl
```

## Bash traversal cheatsheet

```bash
# Total artifact size
du -sh .o11y/<run-id>

# Every URL ever requested, deduped
jq -r '.params.request.url' .o11y/*/cdp/network/requests.jsonl | sort -u

# Find runs that hit a specific host
grep -lr 'api\.example\.com' .o11y/*/cdp/network/requests.jsonl

# Search DOM dumps for an element class that came and went
rg -l 'class="error-banner"' .o11y/<run-id>/dom/

# Tail the firehose live (re-run start-capture is fine - it appends to raw.ndjson? no, it overwrites)
tail -f .o11y/<run-id>/cdp/raw.ndjson | jq -c '{m:.method, u:.params.request.url // .params.frame.url // ""}'
```

## Configuration

| Var                | Default                                | Effect                                                       |
| ------------------ | -------------------------------------- | ------------------------------------------------------------ |
| `O11Y_ROOT`        | `.o11y`                                | base directory under which `<run-id>/` is created             |
| `O11Y_DOMAINS`     | `Network Console Runtime Log Page`     | space-separated CDP domains for the firehose                 |

The interval-second arg to `start-capture.mjs` controls only the sampler. The firehose is always streamed in real time.

## Troubleshooting

| Symptom                                        | Likely cause                                                  | Fix                                                          |
| ---------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------ |
| `cdp-firehose exited immediately`              | unreachable target                                            | read the echoed `cdp/stderr.log`; verify the port has a debuggable page (`curl http://127.0.0.1:9222/json/version`) |
| `cdp-firehose: no debuggable target on port N` | the port is up but has no page target yet                     | open a tab / navigate the driver first, then start the tracer |
| `index.jsonl` shows `"url": ""`                 | sampler `Runtime.evaluate('location.href')` returned empty transiently | benign; happens during navigation transitions                 |
| Screenshots empty / huge / inconsistent sizes  | viewport not set on the target                                | set the viewport from your driver before capture, or push a CDP `Emulation.setDeviceMetricsOverride` on the target |
| `raw.ndjson` grows but bisect buckets empty    | wrong domains; e.g. you wanted DOM but didn't enable it       | `O11Y_DOMAINS="Network Console Runtime Log Page DOM" node scripts/start-capture.mjs ...` |
| Loop process leaks after crash                  | `stop-capture.mjs` not run                                     | `pkill -f snapshot-loop.mjs`; PID files in `<run-dir>` are stale  |
