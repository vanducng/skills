# samber/slog-* — Structured logging pipeline for Go

**Pinned versions (verified 2026-05-23):**

| Package | Tag | Released |
|---|---|---|
| `samber/slog-multi` | **v1.8.0** | 2026-03-25 |
| `samber/slog-sampling` | **v1.6.0** | 2026-03-25 |
| `samber/slog-formatter` | **v1.3.0** | 2026-03-25 |
| `samber/slog-gin` | **v1.21.1** | 2026-04-29 |
| `samber/slog-chi` | **v1.19.1** | 2026-04-29 |
| `samber/slog-echo` | **v2.0.0** | 2026-05-04 *(breaking change from v1)* |
| `samber/slog-fiber` | **v1.22.2** | 2026-04-29 |
| `samber/slog-datadog` | **v2.10.4** | 2026-03-25 |
| `samber/slog-sentry` | **v2.10.3** | 2026-03-25 |
| `samber/slog-loki` | **v3.7.2** | 2026-03-25 *(on v3)* |

All MIT licensed.

20+ composable `slog.Handler` packages for Go 1.21+ stdlib `log/slog`. The three core libraries (`slog-multi`, `slog-sampling`, `slog-formatter`) provide the pipeline; HTTP middlewares and cloud sinks plug into it.

## My take

The load-bearing combination is **`slog-multi` + `slog-sampling`**. Everything else (HTTP middlewares, cloud sinks, bridges) is convenience that saves real time in production.

**Where I deviate from upstream guidance:**

- The upstream doc presents `Fanout` and `Router` symmetrically. In practice, **`Router`** is almost always what you want — `Fanout` forces every record through every handler (latency = sum of all sinks). `Router` evaluates predicates and skips non-matching handlers.
- The doc says "sample first, format second, route last". I'd phrase it stronger: **sampling must be the outermost handler.** Anything else is wasted CPU.
- The cloud sinks (`slog-datadog`, `slog-loki`, `slog-kafka`, `slog-parquet`) **buffer records internally**. If you don't `defer handler.Stop(ctx)` in your shutdown path, buffered logs disappear on every restart. This is the single most-missed best practice in production deployments.

## Install — the canonical setup

```bash
go get github.com/samber/slog-multi@v1.8.0
go get github.com/samber/slog-sampling@v1.6.0
go get github.com/samber/slog-formatter@v1.3.0
```

HTTP middlewares (pick what matches your framework):

```bash
go get github.com/samber/slog-gin@v1.21.1
go get github.com/samber/slog-chi@v1.19.1
go get github.com/samber/slog-echo@v2.0.0     # NB: v2 breaking changes
go get github.com/samber/slog-fiber@v1.22.2
```

Cloud sinks:

```bash
go get github.com/samber/slog-datadog/v2@v2.10.4
go get github.com/samber/slog-sentry/v2@v2.10.3
go get github.com/samber/slog-loki/v3@v3.7.2  # v3 path mandatory
```

## The pipeline model

```
record → [Sampling] → [Pipe: PII + trace context] → [Router] → [Sinks]
              ↑                  ↑                       ↑          ↑
       outermost,         middleware              decides       handlers
       drop early         transformation          where         (stdout,
                                                  records       Datadog,
                                                  go            Sentry…)
```

Order is non-negotiable: sampling before formatting saves CPU. Formatting before routing ensures all sinks see clean attributes.

## `slog-multi` — handler composition

Six patterns:

| Pattern | What it does | Latency cost |
|---|---|---|
| `Fanout(h1, h2, h3)` | Broadcast to all (sequentially) | Sum of all |
| `Router().Add(h, predicate).Handler()` | Route to ALL matching | Sum of matching |
| `Router().Add(...).FirstMatch().Handler()` | Route to FIRST match | Single handler |
| `Failover()(h1, h2, h3)` | Try sequentially until one succeeds | Primary (happy path) |
| `Pool()(h1, h2, h3)` | Concurrent broadcast | max of all (parallel) |
| `Pipe(mw1, mw2).Handler(sink)` | Middleware chain before sink | mw overhead + sink |

```go
// My typical setup: errors → Sentry, all logs → stdout JSON, request middleware adds trace ID
import (
    slogmulti "github.com/samber/slog-multi"
    slogsentry "github.com/samber/slog-sentry/v2"
)

logger := slog.New(
    slogmulti.Router().
        Add(sentryHandler, slogmulti.LevelIs(slog.LevelError)).
        Add(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
            Level: slog.LevelInfo,
        })).
        Handler(),
)
```

Built-in predicates: `LevelIs`, `LevelIsNot`, `MessageIs`, `MessageContains`, `AttrValueIs`, `AttrKindIs`.

**Use `Pool()` when you have 2+ slow sinks** (Datadog + Sentry on the same record): the parallel broadcast gives you `max(latency)` instead of `sum(latency)`.

## `slog-sampling` — throughput control

| Strategy | Behavior | Use for |
|---|---|---|
| Uniform | Drop fixed % | Dev/staging |
| **Threshold** | First N per interval, then sample at rate R | **Production default** — preserves initial visibility |
| Absolute | Cap at N per interval | Hard cost control |
| Custom | Function returns rate per record | Level/time-aware |

```go
import slogsampling "github.com/samber/slog-sampling"

logger := slog.New(
    slogmulti.
        Pipe(slogsampling.ThresholdSamplingOption{
            Tick:      5 * time.Second,
            Threshold: 10,    // first 10 per 5s pass unconditionally
            Rate:      0.1,   // after that, sample 10%
        }.NewMiddleware()).
        Handler(innerHandler),
)
```

**The sampling-first rule:** wrap sampling around your entire pipeline. The middleware is a `slog.Handler` itself — chain it outermost via `slogmulti.Pipe`.

Matchers group similar records for dedup: `MatchByLevel`, `MatchByMessage`, `MatchByLevelAndMessage` (default), `MatchBySource`, `MatchByAttribute`.

## `slog-formatter` — PII + error formatting + flattening

Apply as `Pipe` middleware so all downstream sinks see clean attributes.

```go
import slogformatter "github.com/samber/slog-formatter"

logger := slog.New(
    slogmulti.Pipe(slogformatter.NewFormatterMiddleware(
        slogformatter.PIIFormatter("user"),          // mask "user.*" fields
        slogformatter.ErrorFormatter("error"),       // structured error (works with samber/oops)
        slogformatter.IPAddressFormatter("client"),  // mask IPs
    )).Handler(slog.NewJSONHandler(os.Stdout, nil)),
)
```

Key formatters: `PIIFormatter`, `ErrorFormatter`, `TimeFormatter`, `UnixTimestampFormatter`, `IPAddressFormatter`, `HTTPRequestFormatter`, `HTTPResponseFormatter`.

Generic: `FormatByType[T]`, `FormatByKey`, `FormatByKind`, `FormatByGroup`, `FormatByGroupKey`.

Flatten nested attributes via `FlattenFormatterMiddleware`.

## HTTP middleware — consistent pattern

```go
router.Use(slogXXX.New(logger))
```

Available: `slog-gin`, `slog-echo`, `slog-fiber`, `slog-chi`, `slog-http` (stdlib net/http).

Shared `Config`:

```go
import sloggin "github.com/samber/slog-gin"

router.Use(sloggin.NewWithConfig(logger, sloggin.Config{
    DefaultLevel:     slog.LevelInfo,
    ClientErrorLevel: slog.LevelWarn,
    ServerErrorLevel: slog.LevelError,
    WithRequestBody:  true,
    WithRequestID:    true,
    WithTraceID:      true,
    Filters: []sloggin.Filter{
        sloggin.IgnorePath("/health", "/metrics"),  // skip noise
    },
}))
```

## Cloud sinks — `Option{}.NewXxxHandler()` pattern

```go
import slogdatadog "github.com/samber/slog-datadog/v2"

ddHandler, err := slogdatadog.Option{
    Level:    slog.LevelInfo,
    Service:  "user-api",
    Hostname: hostname,
    APIKey:   os.Getenv("DD_API_KEY"),
}.NewDatadogHandler()
if err != nil { /* … */ }

defer ddHandler.Stop(ctx)  // ← MANDATORY: flushes the buffer
```

**Always defer Stop / Close on batch handlers:**

| Sink | Shutdown call |
|---|---|
| `slog-datadog` | `handler.Stop(ctx)` |
| `slog-loki` | `lokiClient.Stop()` |
| `slog-kafka` | `writer.Close()` |
| `slog-parquet` | `writer.Close()` |

Without this, buffered records vanish on every redeploy.

## My typical production setup

```go
import (
    "log/slog"
    "os"
    "time"

    slogmulti "github.com/samber/slog-multi"
    slogsampling "github.com/samber/slog-sampling"
    slogformatter "github.com/samber/slog-formatter"
    slogdatadog "github.com/samber/slog-datadog/v2"
    slogsentry "github.com/samber/slog-sentry/v2"
)

func newLogger() (*slog.Logger, func() error, error) {
    // sinks
    stdout := slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo})

    dd, err := slogdatadog.Option{ /* ... */ }.NewDatadogHandler()
    if err != nil { return nil, nil, err }

    sentry, err := slogsentry.Option{ Level: slog.LevelError }.NewSentryHandler()
    if err != nil { return nil, nil, err }

    // pipeline: sampling → formatter (PII + errors) → router (level-based)
    handler := slogmulti.
        Pipe(slogsampling.ThresholdSamplingOption{
            Tick:      5 * time.Second,
            Threshold: 100,
            Rate:      0.2,
        }.NewMiddleware()).
        Pipe(slogformatter.NewFormatterMiddleware(
            slogformatter.PIIFormatter("user"),
            slogformatter.ErrorFormatter("error"),
        )).
        Handler(
            slogmulti.Router().
                Add(sentry, slogmulti.LevelIs(slog.LevelError)).
                Add(slogmulti.Pool()(dd, stdout)).  // both for non-error
                Handler(),
        )

    logger := slog.New(handler)

    // shutdown cleanup
    shutdown := func() error {
        return dd.Stop(context.Background())
    }
    return logger, shutdown, nil
}
```

## Common mistakes

| Mistake | Cost | Fix |
|---|---|---|
| Sampling **inside** the pipeline | CPU spent on records that get dropped | Sampling MUST be outermost |
| `Fanout` to multiple synchronous sinks | Latency = sum(handlers) | Use `Pool()` for concurrent |
| Missing `defer ddHandler.Stop(ctx)` | Buffered logs lost on restart | Always defer cleanup |
| `Router` with no catch-all | Unmatched records dropped silently | Add a handler with no predicate |
| `AttrFromContext` without HTTP middleware | Context has no request attrs | Install `slog-gin/echo/fiber/chi` first |
| Using `Pipe` with zero middleware | No-op wrapper, per-record overhead | Remove the `Pipe()` call |
| Many formatters in `Pipe` | Each adds per-record allocation | Keep formatter chains short (2–4); or implement `slog.LogValuer` on your types |
| Treating `slog-echo v2` like v1 | Breaking API changes | Read the v2 release notes before upgrading |

## When to skip these packages

- Single sink + single level + no PII → bare `slog.NewJSONHandler(os.Stdout, nil)` is enough
- A library (not an application) — don't impose a pipeline on your callers; expose a `slog.Logger` parameter
- CLI tool — `slog.New(slog.NewTextHandler(os.Stderr, nil))` is fine

## Performance notes

- `Fanout` is sequential — 5 handlers × 10ms = 50ms per log call
- `Pipe` middlewares add per-record function call overhead; keep chains under 4
- For hot-path attribute formatting, prefer implementing `slog.LogValuer` on your own types over `slog-formatter`
- Benchmark with `go test -bench` before deploying — log infrastructure changes can spike p99

## Cross-refs

- See `oops.md` — the `slog-formatter` `ErrorFormatter` extracts `oops` attributes automatically
- See `vd:py2go` HTTP playbook — `slog` is the default logger, `slog-gin` the default middleware
- See `vd:debug` — log routing decisions determine on-call signal-to-noise
