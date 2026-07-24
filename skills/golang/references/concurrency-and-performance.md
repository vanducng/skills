# Concurrency, Context & Performance

## Concurrency

Structured concurrency: every goroutine has a clear owner, a predictable exit, and error propagation. A goroutine is a liability until proven necessary.

**Core rules:**
1. **Every goroutine has a defined exit** - context, done channel, or WaitGroup. No exit → leak → crash.
2. Share by communicating (channels transfer ownership) rather than shared mutable state.
3. Send copies/immutable values on channels, not pointers (pointers reintroduce invisible sharing).
4. **Only the sender closes a channel** (closing from the receiver panics the sender). Type channel directions (`chan<-`, `<-chan`).
5. Default to **unbuffered** channels - a buffer masks backpressure; add one only with measured justification.
6. **Always include `ctx.Done()` in `select`** or the goroutine leaks after cancellation.
7. Never `time.After` in a loop - each call leaks a timer until it fires. Use `time.NewTimer` + `Reset`.
8. Call `wg.Add` *before* `go` (else `Wait` may return early). Detect leaks in tests with `go.uber.org/goleak` (`goleak.VerifyTestMain`).

**Choosing a primitive:**

| Need | Use |
| --- | --- |
| Pass data / transfer ownership | Channel |
| Protect shared struct fields | `sync.Mutex` / `RWMutex` (keep critical sections short; never hold across I/O) |
| Simple counters/flags | typed `sync/atomic` (`atomic.Int64`, `atomic.Bool`) |
| Read-heavy concurrent map | `sync.Map` (concurrent read/write on a plain map is a hard crash) |
| Wait, no errors | `sync.WaitGroup` (1.24+: `wg.Go()`) |
| Wait + first error + cancel siblings | `errgroup.WithContext` |
| Bounded worker pool | `errgroup.SetLimit(n)` (replaces hand-rolled pools) |
| Dedupe concurrent identical calls | `x/sync/singleflight` |
| One-time init | `sync.Once` (1.21+: `OnceValue`/`OnceFunc`) |
| Reuse temporaries, cut GC | `sync.Pool` (always `Reset()` before `Put()`) |

Before spawning: how will it exit? can I signal stop? can I wait? who owns/closes the channels? should this just be synchronous? Always `go test -race ./...` in CI.

## Context

`context.Context` carries cancellation, deadlines, and request-scoped metadata across API boundaries - the "session" of a request.

1. **Propagate the same ctx** end-to-end: handler → service → DB → external API. Cancelling the parent then cancels all downstream work.
2. `ctx` is the **first parameter**, named `ctx context.Context`. Never store it in a struct.
3. Never pass `nil` - use `context.TODO()` as a placeholder when you don't have one yet.
4. **`defer cancel()`** immediately after `WithCancel`/`WithTimeout`/`WithDeadline`.
5. `context.Background()` only at entry points (main, init, tests); never mint a new Background mid-request.
6. Context value keys are **unexported types** (collision-safe) and carry only request-scoped metadata (request ID, trace ID) - never function parameters.
7. `context.WithoutCancel` (1.21+) for background work that must outlive the request (audit logs).
8. Use `*Context` DB/HTTP method variants (`QueryContext`, `ExecContext`, `NewRequestWithContext`) so deadlines/cancellation are honored.

## Performance

**Never optimize without profiling first - intuition is wrong ~80% of the time.** Measure → hypothesize → change one thing → re-measure.

- **Rule out external bottlenecks first** - if 90% of latency is a slow query or upstream, Go-side allocation tuning won't help. Use `fgprof` (on- + off-CPU) or a goroutine profile (many blocked in `net.Read`/`database/sql` = external wait).
- **Allocation reduction has the biggest ROI.** GC is fast but not free.

**Optimization cycle:** define the metric (latency/throughput/memory/CPU) → write an atomic benchmark → baseline (`-count=6 | tee report-1.txt`) → diagnose with the right tool → apply **one** change with an explanatory comment → `benchstat report-1.txt report-2.txt` to confirm significance → repeat.

**Decision tree:**

| Signal (from pprof) | Action |
| --- | --- |
| High `alloc_objects` in heap profile | Reduce allocations; `sync.Pool`; preallocate |
| Function dominates CPU profile | Inlining, cache locality, avoid `reflect` |
| High GC% / OOM in a container | `GOMEMLIMIT` at 80–90% of the limit; `GOGC` tuning |
| Goroutines blocked on I/O | Tune `http.Transport` (`MaxIdleConnsPerHost` defaults to 2), stream, batch |
| Same work repeated | Cache, `singleflight` |
| Mutex/block profile hot | Shorten critical sections, reduce contention |

Common mistakes: default `http.Client` without a tuned `Transport`; logging in hot loops (allocates even when the level is off - use `slog.LogAttrs`); `panic`/`recover` as control flow; `reflect.DeepEqual` in prod (use `slices.Equal`/`maps.Equal`/`bytes.Equal`); `unsafe` without benchmark proof of >10% gain in a verified hot path.

## Benchmarking & profiling

**`b.Loop()` (Go 1.24+) is preferred** - prevents dead-code elimination and auto-excludes setup from timing:

```go
func BenchmarkParse(b *testing.B) {
    data := loadFixture("large.json") // excluded from timing
    for b.Loop() {
        Parse(data)
    }
}
```

Run with `-benchmem -count=10` for statistical significance; `-count=6+` then `benchstat` - never conclude from a single run. Output: `... 230.5 ns/op  128 B/op  2 allocs/op`.

Profile directly from benchmarks (no HTTP server needed):

```bash
go test -bench=BenchmarkParse -cpuprofile=cpu.prof ./pkg/parser && go tool pprof cpu.prof
go test -bench=BenchmarkParse -memprofile=mem.prof ./pkg && go tool pprof -alloc_objects mem.prof
```

`fieldalignment` for struct padding, escape analysis (`go build -gcflags="-m"`) for unexpected heap allocations, `go tool trace` for scheduler/GC timeline. Gate regressions in CI with `benchdiff`/`cob`.

## Debugging (no fix without root cause)

Read the error → reproduce (a failing test, made deterministic) → measure one thing → fix → verify. One hypothesis at a time; escalate tools only when simpler ones fail (`fmt.Println` → `slog` → pprof → Delve → GODEBUG). Never propose a fix you can't explain.

| Symptom | First move |
| --- | --- |
| Won't compile | `go build ./... 2>&1`, `go vet ./...` |
| Wrong output | Write a failing test; check error handling, nil, off-by-one |
| Random panics | `GOTRACEBACK=all`, `go test -race ./...` |
| Intermittent | `go test -race ./...` |
| Hangs | `curl localhost:6060/debug/pprof/goroutine?debug=2` |
| High CPU / memory growth | pprof CPU / heap profile |

Most Go bugs: missing error checks, nil pointers, forgotten `cancel()`, unclosed resources, races, swallowed errors. Red flags in your own reasoning: "quick fix for now", changing several things at once, 3+ attempts on one issue (wrong mental model - re-trace from scratch), "it works on my machine", blaming the stdlib/compiler.
