# samber/ro — Reactive streams for Go

**Pinned: v0.3.0 (released 2026-03-02) · Apache-2.0 · ⚠ PRE-1.0 — young library, API churning · verified 2026-05-23**

ReactiveX implementation for Go. 150+ type-safe operators, cold/hot observables, 5 subject types, declarative pipelines via `Pipe`, 40+ plugins (HTTP, cron, fsnotify, JSON, logging), automatic backpressure, error propagation, context integration.

Upstream: [github.com/samber/ro](https://github.com/samber/ro) · [ro.samber.dev](https://ro.samber.dev) · [pkg.go.dev](https://pkg.go.dev/github.com/samber/ro)

## My take

**Default to not using this.** Go has goroutines + channels + `errgroup` + `sync.Cond` + `context`. Reactive Extensions exists because some ecosystems (RxJS, RxJava) needed a way to model async streams without first-class concurrency primitives. Go has those primitives natively.

`samber/ro` is well-built and the API is clean. The justification problem is sociological: when a Go reviewer reads `ro.Pipe5(...).Subscribe(...)`, they have to learn a programming paradigm that doesn't appear elsewhere in idiomatic Go. The cognitive cost is real.

**The cases where I'd actually reach for it:**

1. Multi-source async pipeline that needs `CombineLatest` / `Zip` semantics and would be a 200-line `select { }` ladder otherwise
2. Pub/sub with multiple consumers and replay semantics — `ReplaySubject` is genuinely useful for late-joiner WebSocket clients
3. Real-time event enrichment from 3+ async sources with retry/timeout/throttle per source

**Where I deviate from upstream guidance:**

- Upstream pitches it as a general-purpose tool. I'd recommend it as a **specialized tool**: reach for it when the channel-based equivalent would be unmistakably worse.
- **Pre-1.0 means pin exact**, and budget for breaking changes between minors. v0.2 → v0.3 already had renames.
- Always use typed `Pipe2`, `Pipe3`, … `Pipe25` — the untyped `Pipe(any, any, …)` loses compile-time type safety and surfaces errors at runtime. Never use it.
- The 40+ plugins are worth knowing about, but most of them (`plugins/http`, `plugins/fsnotify`, `plugins/cron`) are wrappers over Go libraries you'd otherwise use directly. The plugin is convenient only if you're already in a reactive pipeline.

**When I'd definitely skip:**

- Finite slice transforms — `samber/lo`
- Bounded goroutine fan-out — `errgroup` + `semaphore`
- Simple pub/sub — channels with reference counting
- Sequential async with retry — `cenkalti/backoff` + a loop

## Install

```bash
go get github.com/samber/ro@v0.3.0
```

```go
import "github.com/samber/ro"
```

## When to use which Go tool

| Scenario | Tool | Why |
|---|---|---|
| Transform a slice (Map/Filter/Reduce) | `samber/lo` | Finite, synchronous, eager |
| Goroutine fan-out with error handling | `errgroup` | Stdlib-adjacent, lightweight |
| Bounded concurrency | `errgroup` + `golang.org/x/sync/semaphore` | Standard, well-understood |
| Infinite event stream (WebSocket, ticker, file watcher) | `samber/ro` | Declarative pipeline with backpressure/retry/timeout |
| Multi-source async combine with `CombineLatest`/`Zip` | `samber/ro` | Composes dependent streams without manual select |
| Pub/sub with replay semantics for late subscribers | `samber/ro` Subjects | Replay/Behavior subjects do this natively |

## Core concepts

Four building blocks:

1. **Observable** — a data source emitting values over time. Cold by default (each subscriber triggers independent execution from scratch)
2. **Observer** — three callbacks: `onNext(T)`, `onError(error)`, `onComplete()`
3. **Operator** — function turning one observable into another, chained via `Pipe`
4. **Subscription** — the connection; call `.Wait()` to block or `.Unsubscribe()` to cancel

```go
observable := ro.Pipe2(
    ro.RangeWithInterval(0, 5, 1*time.Second),
    ro.Filter(func(x int) bool { return x%2 == 0 }),
    ro.Map(func(x int) string { return fmt.Sprintf("even-%d", x) }),
)

observable.Subscribe(ro.NewObserver(
    func(s string) { fmt.Println(s) },
    func(err error) { log.Println(err) },
    func() { fmt.Println("Done") },
))
```

Synchronous collection (finite streams):

```go
values, err := ro.Collect(observable)
```

## Cold vs hot

**Cold** (default): each `.Subscribe()` starts independent execution. Predictable.

**Hot**: subscribers share one execution. Use when:

- The source is expensive (WebSocket connection, DB poll)
- All subscribers must see the same events

| Conversion | Behavior |
|---|---|
| `Share()` | Cold → hot with reference counting. Last unsubscribe tears down |
| `ShareReplay(n)` | Same + buffers last N for late subscribers |
| `Connectable()` | Cold → hot, but waits for explicit `.Connect()` |
| Subjects | Natively hot — call `.Send/.Error/.Complete` directly |

| Subject | Replay behavior |
|---|---|
| `PublishSubject` | None — late subscribers miss past events |
| `BehaviorSubject` | Replays last value to new subscribers |
| `ReplaySubject` | Replays last N values |
| `AsyncSubject` | Emits only last value, on complete |
| `UnicastSubject` | Single subscriber only |

`ReplaySubject` is the one I'd reach for in a WebSocket fan-out scenario — late-joining clients catch up on the last N events.

## Operator categories

| Category | Key operators | Purpose |
|---|---|---|
| Creation | `Just`, `FromSlice`, `FromChannel`, `Range`, `Interval`, `Defer`, `Future` | Create observables |
| Transform | `Map`, `MapErr`, `FlatMap`, `Scan`, `Reduce`, `GroupBy` | Transform values |
| Filter | `Filter`, `Take`, `TakeLast`, `Skip`, `Distinct`, `Find`, `First`, `Last` | Selectively emit |
| Combine | `Merge`, `Concat`, `Zip2…Zip6`, `CombineLatest2…CombineLatest5`, `Race` | Multi-observable |
| Error | `Catch`, `OnErrorReturn`, `OnErrorResumeNextWith`, `Retry`, `RetryWithConfig` | Recover |
| Timing | `Delay`, `DelayEach`, `Timeout`, `ThrottleTime`, `SampleTime`, `BufferWithTime` | Time control |
| Side effect | `Tap`/`Do`, `TapOnNext`, `TapOnError`, `TapOnComplete` | Observability |
| Terminal | `Collect`, `ToSlice`, `ToChannel`, `ToMap` | Consume into Go types |

**Use typed `Pipe2` through `Pipe25`.** Don't use untyped `Pipe(...)`.

## Common mistakes

| Mistake | Why it fails | Fix |
|---|---|---|
| Subscribing with `OnNext` only | Errors silently dropped | Use `NewObserver(onNext, onError, onComplete)` |
| Untyped `Pipe()` | Loses compile-time type safety | Always use `Pipe2`, `Pipe3`, … `Pipe25` |
| Forgetting `.Unsubscribe()` on infinite streams | Goroutine leak | Use `TakeUntil(signal)`, context cancellation, explicit `Unsubscribe` |
| Hot when cold suffices | Overcomplicated lifecycle | Use `Share` only when multi-subscriber requires same stream |
| Using `ro` for finite slices | Stream overhead for synchronous data | Use `lo` |
| Not propagating context | Streams ignore shutdown signals | `ContextWithTimeout` or `ThrowOnContextCancel` |
| `v0.x` with caret/tilde pinning | Surprise breakage | Pin exact in `go.mod` |

## Plugin ecosystem (40+)

Convenient if you're already in a reactive pipeline; otherwise prefer the underlying library directly.

| Category | Plugins | Import prefix |
|---|---|---|
| Encoding | JSON, CSV, Base64, Gob | `plugins/encoding/…` |
| Network | HTTP, I/O, FSNotify | `plugins/http`, `plugins/io`, `plugins/fsnotify` |
| Scheduling | Cron, ICS | `plugins/cron`, `plugins/ics` |
| Observability | Zap, Slog, Zerolog, Logrus, Sentry, Oops | `plugins/observability/…`, `plugins/samber/oops` |
| Rate limit | Native, Ulule | `plugins/ratelimit/…` |
| Data | Bytes, Strings, Sort, Strconv, Regexp, Template | `plugins/bytes`, `plugins/strings`, etc. |
| System | Process, Signal | `plugins/proc`, `plugins/signal` |

## When to use `ro` — concrete examples

### Multi-source enrichment (CombineLatest)

```go
// Subscribe to three streams; emit a combined view whenever any updates
combined := ro.Pipe1(
    ro.CombineLatest3(userStream, accountStream, prefsStream),
    ro.Map(func(t ro.Tuple3[User, Account, Prefs]) View {
        return View{User: t.A, Account: t.B, Prefs: t.C}
    }),
)
```

The same logic with `select` + three channels + state caching would be ~80 lines and error-prone.

### Pub/sub with replay (WebSocket fan-out)

```go
events := ro.NewReplaySubject[Event](100)  // last 100

// publisher
events.Send(Event{...})

// new subscriber catches up on last 100, then live stream
events.Subscribe(ro.NewObserver(
    func(e Event) { ws.WriteJSON(e) },
    onError, onComplete,
))
```

### Retry with timeout on each subscription

```go
robust := ro.Pipe2(
    ro.Defer(func() ro.Observable[Data] { return apiCall(ctx) }),
    ro.Timeout(5*time.Second),
    ro.RetryWithConfig(ro.RetryConfig{Count: 3, Backoff: ro.ExponentialBackoff}),
)
```

## When *not* to use `ro` — concrete refusals

- "I want to call N URLs in parallel and collect responses" → `errgroup`
- "I want to debounce user input" → `time.AfterFunc` or `lo.Debounce`
- "I want to retry a single HTTP call" → `cenkalti/backoff` or `hashicorp/go-retryablehttp`
- "I want to transform a slice" → `samber/lo`

If the answer is one of the above, reach for the simpler tool. `ro` earns its keep only when the channel-based equivalent would be unmistakably worse.

## Cross-refs

- See `lo.md` — for finite slice transforms (don't use ro for those)
- See `oops.md` — error propagation through the reactive pipeline
- See `vd:py2go` worker playbook — sometimes the Python `asyncio` source is reactive enough to warrant ro
