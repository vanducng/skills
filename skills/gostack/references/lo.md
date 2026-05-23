# samber/lo — Lodash-style helpers for Go

**Pinned: v1.53.0 (released 2026-03-02) · MIT · 21.2k stars · zero deps · verified 2026-05-23**

500+ generics-first, type-safe utility functions for slices, maps, channels, strings, math, tuples, and concurrency. The library people actually keep installing because Go's stdlib `slices`/`maps` only covers ~10 basic ops.

Upstream: [github.com/samber/lo](https://github.com/samber/lo) · [lo.samber.dev](https://lo.samber.dev) · [pkg.go.dev](https://pkg.go.dev/github.com/samber/lo)

## My take

The gateway drug of the samber ecosystem. Worth installing on day one of a Go project where collection transforms aren't trivial — Map/Filter/Reduce/GroupBy/Chunk/Flatten/Uniq are universally useful and the stdlib doesn't have them.

**The trap:** people reach for `lo.Contains`, `lo.Sort`, `lo.Keys` out of habit. The Go 1.21+ stdlib (`slices.Contains`, `slices.Sort`, `maps.Keys`) handles those — no dependency needed. Pulling in `lo` for stdlib-covered ops is a code-review smell I always flag.

**Where I deviate from upstream guidance:**

- `lo/parallel` (`lop`) is **rarely** the right answer for I/O fan-out. The library doc says "use it for parallel work" — true, but Go's `errgroup.Group` + bounded `semaphore` is more idiomatic for I/O. `lop` shines only on CPU-bound work on large slices (1000+ items). I default to `errgroup`.
- `lo/mutable` (`lom`) breaks immutability. Touch only after `pprof` confirms allocation pressure. Reaching for it preemptively because "it's faster" is premature optimization 99% of the time.
- `lo/it` (lazy iterators) needs Go 1.23+ and is worth it when you have 3+ chained transforms on a large dataset — saves intermediate allocations. Not worth the cognitive overhead on short chains.

## Install

```bash
go get github.com/samber/lo@v1.53.0
```

| Package | Import path | Alias | Min Go | When |
|---|---|---|---|---|
| Core (immutable) | `github.com/samber/lo` | `lo` | 1.18+ | **Default** |
| Parallel | `github.com/samber/lo/parallel` | `lop` | 1.18+ | CPU-bound, 1000+ items, after benchmarking |
| Mutable | `github.com/samber/lo/mutable` | `lom` | 1.18+ | Hot path, after `pprof` proves it |
| Iterator | `github.com/samber/lo/it` | `loi` | 1.23+ | Long chains on large data |
| SIMD (exp) | `github.com/samber/lo/exp/simd` | — | 1.25+ amd64 | Numeric bulk ops, benchmark first |

## Core patterns I actually use

### Transform a slice

```go
// ✓
names := lo.Map(users, func(u User, _ int) string {
    return u.Name
})

// ✗ Don't do this for one-liners — readable, but the boilerplate is the cost
names := make([]string, 0, len(users))
for _, u := range users { names = append(names, u.Name) }
```

### Filter then reduce — chain reads top-to-bottom

```go
total := lo.Reduce(
    lo.Filter(orders, func(o Order, _ int) bool { return o.Status == "paid" }),
    func(sum float64, o Order, _ int) float64 { return sum + o.Amount },
    0,
)
```

### GroupBy — the killer feature

```go
byStatus := lo.GroupBy(tasks, func(t Task, _ int) string { return t.Status })
// map[string][]Task{"open": [...], "closed": [...]}
```

### Error variants — short-circuit on first error

```go
results, err := lo.MapErr(urls, func(url string, _ int) (Response, error) {
    return fetch(url)
})
// stops at first error, no need for manual error collection
```

### Chunking — for batch APIs

```go
for _, batch := range lo.Chunk(userIDs, 100) {
    if err := db.BatchInsert(ctx, batch); err != nil {
        return err
    }
}
```

### `lo.Must` — only in tests and init

```go
// ✓ test
cfg := lo.Must(loadConfig("testdata/cfg.yaml"))

// ✗ production handler — panic will crash the request
result := lo.Must(svc.DoThing(ctx))  // DON'T
```

## What to use from the stdlib instead

| If you'd reach for… | Use this instead | Notes |
|---|---|---|
| `lo.Contains` | `slices.Contains` | Go 1.21+ stdlib |
| `lo.IndexOf` | `slices.Index` | Go 1.21+ stdlib |
| `lo.Reverse` (in place) | `slices.Reverse` | Go 1.21+ stdlib |
| `lo.Sort` / `lo.SortBy` | `slices.Sort` / `slices.SortFunc` | Go 1.21+ stdlib |
| `lo.Keys` / `lo.Values` | `maps.Keys` / `maps.Values` (Go 1.23 iterators) | Stdlib `maps` package |
| `lo.Min` / `lo.Max` (numeric) | `min(...)` / `max(...)` builtins | Go 1.21+ |
| `lo.Clamp` | `min(max(v, lo), hi)` | One-liner, no dep needed |
| `lo.Sum` (numeric) | manual `for _, v := range s { sum += v }` | Fine without an import |

If `lo` is **only** providing stdlib-covered ops, drop it from the project.

## What earns `lo` its keep

These have no stdlib equivalent and write much cleaner with `lo`:

- `Map`, `MapErr`, `MapKeys`, `MapValues`, `MapToSlice`
- `Filter`, `FilterMap`, `Reject`
- `Reduce`, `ReduceRight`
- `GroupBy`, `Associate`, `KeyBy`
- `Chunk`, `Partition`, `Splice`
- `Flatten`, `FlatMap`, `Interleave`
- `Uniq`, `UniqBy`
- `Find`, `FindOrElse`, `FindIndexOf`, `FindKeyBy`
- `PickBy`, `PickByKeys`, `OmitBy`, `OmitByKeys`
- `Zip2…Zip9`, `Unzip2…Unzip9`
- `Range`, `RangeFrom`, `RangeWithSteps`
- `Debounce`, `Throttle`
- `Attempt`, `AttemptWithDelay` — retry with backoff
- `Async`, `WaitFor`

## Common mistakes (catch in review)

| Mistake | Why it hurts | Fix |
|---|---|---|
| `lo.Contains` where `slices.Contains` works | Unnecessary dep, slower lint, slower compile | Use stdlib |
| `lop.Map` on 10 items | Goroutine overhead > work | Use `lo.Map`; `lop` benefits start ~1000+ |
| Assuming `lo.Filter` modifies input | It's immutable by default — returns new slice | Use `lom.Filter` only if you measured allocation |
| `lo.Must` in handlers / production paths | Panics on error — surfaces as 500s | Use the non-Must variant and handle the error |
| Long chains of eager transforms on big data | Each step allocates an intermediate slice | Switch the chain to `loi` (iterator) |
| Importing `lo` for a single helper | Whole package compiled in | Inline the 5-line for-loop instead |

## Composability with the rest of the samber ecosystem

- **with `mo`**: pipe values through `Option[T]` / `Result[T]` then materialize with `lo.Map`. The Map/Filter chain is more readable than nested Match calls for finite slices.
- **with `oops`**: `lo.MapErr` returns the first error; wrap it with `oops.Wrapf(err, "…")` at the layer boundary.
- **with `ro`**: don't. If data is a finite slice → `lo`. If it's a stream → `ro`. Don't mix.

## When I'd skip `lo` entirely

- Stdlib + a 3-line for-loop covers everything in the project
- The codebase is review-sensitive and Go reviewers push back on functional style
- Compile-time matters (CI on slow hardware) — `lo`'s generic instantiations add to build times in big monorepos

## Quick reference card

| Function | Purpose |
|---|---|
| `lo.Map[T, R]` | Transform `[]T → []R` |
| `lo.Filter[T]` | Keep elements matching predicate |
| `lo.Reject[T]` | Inverse of Filter |
| `lo.Reduce[T, R]` | Fold |
| `lo.GroupBy[T, K]` | `[]T → map[K][]T` |
| `lo.KeyBy[T, K]` | `[]T → map[K]T` (assumes unique keys) |
| `lo.Associate[T, K, V]` | Build map from slice with explicit key+value fn |
| `lo.Chunk[T]` | Split into batches |
| `lo.Flatten[T]` | One level only |
| `lo.Uniq[T]` / `UniqBy` | Dedup |
| `lo.Find` / `FindOrElse` | First match |
| `lo.Partition[T]` | Split by predicate into `(yes, no)` |
| `lo.PickBy[K, V]` / `OmitBy` | Map filtering |
| `lo.ToPtr[T]` / `FromPtr[T]` | Pointer ⇄ value |
| `lo.Coalesce[T]` | First non-zero |
| `lo.Ternary[T]` | Inline conditional |
| `lo.Attempt(n, fn)` | Retry with backoff |
| `lo.Must[T]` | Panic on error — tests/init only |

For the full 500+ catalog, hit [pkg.go.dev](https://pkg.go.dev/github.com/samber/lo).
