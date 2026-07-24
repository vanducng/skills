# samber/hot - In-memory cache for read-heavy Go services

**Pinned: v0.13.0 (released 2026-03-11) · MIT · ⚠ PRE-1.0 - API can break between minors · verified 2026-05-23**

Generic, type-safe in-memory cache for Go 1.22+. Nine eviction algorithms (LRU, LFU, TinyLFU, W-TinyLFU, S3FIFO, ARC, TwoQueue, SIEVE, FIFO), TTL, loaders with singleflight, sharding, stale-while-revalidate, Prometheus metrics.

Upstream: [github.com/samber/hot](https://github.com/samber/hot) · [pkg.go.dev](https://pkg.go.dev/github.com/samber/hot)

## My take

The library's headline feature isn't the eviction algorithm zoo - it's the **loader + singleflight combo**. Read-through caching with automatic deduplication of concurrent loads is otherwise 40-50 lines of correct-but-fiddly code. `samber/hot` packages that with type safety in ~5 lines.

**Where I deviate from upstream guidance:**

- Don't shop algorithms. **Use `hot.WTinyLFU`** until profiling proves otherwise. The algorithm zoo is impressive but the W-TinyLFU default is right for >90% of workloads - switching is a profiling-driven decision, not a vibes-driven one.
- The Prometheus metrics integration (`WithPrometheusMetrics`) is **mandatory** in production. A cache without hit-rate monitoring is a cache you don't know is working. Hit rate <80% usually means undersized.
- **Pre-1.0 means pin exact.** No `~0.13.0`, no `^0.x`. Set `github.com/samber/hot v0.13.0` and gate updates through a manual review of the release notes.
- The library shines at **read-through with bounded memory**. For write-heavy caches, look at `bigcache` or Redis instead - `hot`'s value-by-value tracking has overhead that bigcache's chunk-allocator avoids.

**When I'd reach for it:**

- Service repeatedly loads the same medium-to-low-cardinality resources (users, products, feature flags) at high frequency
- Latency matters and the backend is slower than RAM access
- The cache is read-mostly (not constant invalidation)

**When I'd skip it:**

- The data changes faster than TTL - you're caching staleness
- You need distributed cache - use Redis (`go-redis/v9` or `rueidis`)
- A simple `sync.Map` + a per-key TTL goroutine is enough - don't add a dependency for the trivial case
- `patrickmn/go-cache` already in the project and doing fine - don't churn for the algorithm variety

## Install

```bash
go get github.com/samber/hot@v0.13.0
```

```go
import "github.com/samber/hot"
```

## Algorithm cheat sheet

Default `hot.WTinyLFU`. Only switch when profiling shows the miss rate is too high for your SLO.

| Algorithm | Use when | Avoid when |
|---|---|---|
| **W-TinyLFU** (default) | General-purpose, mixed workloads | You need simplicity for debugging |
| LRU | Recency-dominated (sessions, recent queries) | Scan pollution evicts hot items |
| LFU | Frequency-dominated (popular products, DNS) | Access patterns shift, stale popular items never evict |
| TinyLFU | Read-heavy with frequency bias | Write-heavy (admission filter overhead) |
| S3FIFO | High throughput, scan-resistant | Small caches (<1000 items) |
| ARC | Self-tuning, unknown patterns | Memory-constrained (2× tracking overhead) |
| TwoQueue | Mixed with hot/cold split | Tuning complexity unacceptable |
| SIEVE | Simple scan-resistant LRU alternative | Highly skewed access patterns |
| FIFO | Predictable eviction order | Hit rate matters at all |

## My typical production setup

```go
cache := hot.NewHotCache[string, *User](hot.WTinyLFU, 100_000).
    WithTTL(5 * time.Minute).
    WithJitter(0.1, 1*time.Minute).       // spread expirations
    WithJanitor().                         // background expiry cleanup
    WithLoaders(func(ids []string) (map[string]*User, error) {
        return db.GetUsersByIDs(ctx, ids)
    }).
    WithPrometheusMetrics("user_cache").  // mandatory in prod
    Build()
defer cache.StopJanitor()

user, found, err := cache.Get("user-123")
```

What each option earns:

| Option | What you lose without it |
|---|---|
| `WithTTL(...)` | Stale data served indefinitely (no refresh signal) |
| `WithJitter(...)` | Thundering herd when items expire together |
| `WithJanitor()` | Expired items stay until algorithm evicts (memory leak) |
| `WithLoaders(...)` | Hand-rolled singleflight (a known source of subtle races) |
| `WithPrometheusMetrics(...)` | No way to know if cache is actually helping |

## Capacity sizing

You **must** size to the working set, not the data size. A cache holding everything is a map with overhead.

Process:

1. Estimate per-entry size: `sizeof(struct) + heap fields (strings, slices, maps) + key size + ~100 bytes bookkeeping`
2. Ask the developer what memory budget the cache gets (e.g. 256 MB)
3. `capacity = budget / entrySize`, round down

Example: `*User` ~500 B + key ~50 B + overhead ~100 B = ~650 B/entry → 256 MB / 650 B ≈ 393k items.

If unknown, write a sizing test:

```go
func TestUserCacheSizing(t *testing.T) {
    var m runtime.MemStats
    runtime.GC(); runtime.ReadMemStats(&m); before := m.HeapAlloc

    cache := hot.NewHotCache[string, *User](hot.WTinyLFU, 10_000).Build()
    for i := 0; i < 10_000; i++ { cache.Set(fmt.Sprintf("u-%d", i), sampleUser(i)) }

    runtime.GC(); runtime.ReadMemStats(&m); after := m.HeapAlloc
    t.Logf("10k entries ≈ %d bytes ⇒ %d B/entry", after-before, (after-before)/10_000)
}
```

## Loader pattern - the killer feature

Concurrent `Get()` calls for the same missing key share **one** loader invocation:

```go
cache := hot.NewHotCache[int, *Product](hot.WTinyLFU, 10_000).
    WithTTL(10 * time.Minute).
    WithLoaders(func(ids []int) (map[int]*Product, error) {
        return db.GetProductsByIDs(ctx, ids)   // batch query
    }).
    WithJanitor().
    Build()

// 100 goroutines call Get(42) concurrently
// → 1 DB query, 100 cached returns
product, found, err := cache.Get(42)
```

The loader receives a **batch** of missing keys when called from multiple concurrent gets. Implement it as a batch query for free fan-in optimization.

## Stale-while-revalidate

Serve stale data while refreshing in background - useful for hot paths where occasional staleness beats blocking on the loader:

```go
cache := hot.NewHotCache[string, *Config](hot.WTinyLFU, 100).
    WithTTL(1*time.Minute).
    WithRevalidation(30*time.Second).  // serve stale up to 30s past TTL while loader runs
    WithLoaders(...).
    Build()
```

## Mutable values - copy on read/write

Without copies, callers mutate the cached object directly → shared-state corruption:

```go
cache := hot.NewHotCache[string, []byte](hot.WTinyLFU, 1000).
    WithCopyOnRead(func(b []byte) []byte { return slices.Clone(b) }).
    WithCopyOnWrite(func(b []byte) []byte { return slices.Clone(b) }).
    Build()
```

For immutable values (e.g. `*User` where you treat instances as immutable), skip the copies - pay the cost only where mutation could happen.

## Common mistakes

| Mistake | What breaks | Fix |
|---|---|---|
| Forgetting `WithJanitor()` | Expired entries linger until eviction | Always chain, `defer cache.StopJanitor()` |
| `SetMissing()` without missing-cache config | Runtime panic | Enable `WithMissingCache(algo, cap)` first |
| `WithoutLocking()` + `WithJanitor()` | Panics (mutually exclusive) | Drop `WithoutLocking()` |
| Oversized cache | Memory waste, no hit-rate gain | Size to working set, monitor hit rate |
| Ignoring loader errors | Treats failures as cache misses indefinitely | Always check `err`, not just `found` |
| No Prometheus metrics in prod | Can't tell if cache helps | `WithPrometheusMetrics(name)` always |
| Caching mutable values without copies | Shared-state bugs | `WithCopyOnRead/Write` |
| Pre-1.0 version pinning with `^0.x` | Surprise breakage on minor bump | Pin exact in go.mod |

## Sharding for high-concurrency

For caches under heavy concurrent write pressure:

```go
cache := hot.NewHotCache[string, *Session](hot.WTinyLFU, 1_000_000).
    WithTTL(30 * time.Minute).
    WithShardedStorage(32, /* shard count */ func(k string) uint64 {
        h := fnv.New64a(); h.Write([]byte(k)); return h.Sum64()
    }).
    WithJanitor().
    Build()
```

Default is unsharded; reach for sharding only if write contention shows up in `pprof`.

## When the pre-1.0 risk bites

The `v0.x → v0.y` transitions have included:
- Renaming `WithLoader` → `WithLoaders` to support batch loaders
- Builder method ordering changes
- New mandatory options

Mitigation: pin exact + read release notes before bumping + run integration tests against the new version in a feature branch before merging.

## Comparison with alternatives

| Lib | When |
|---|---|
| **`samber/hot`** | Loader + singleflight, TTL with jitter, algorithm choice matters, Prometheus integration |
| `patrickmn/go-cache` | Simple expiring map; no loader, no algorithms |
| `dgraph-io/ristretto` | Comparable performance, more mature (1.x), no built-in loader |
| `coocood/freecache` | Lower concurrency hit-rate, GC-free storage for large value sets |
| `allegro/bigcache` | Massive caches with low GC pressure, no per-item algorithm |
| Redis (`go-redis`/`rueidis`) | Distributed, persistent, when in-mem isn't enough |

**My default in production today:** `dgraph-io/ristretto` for in-mem when stability matters; `samber/hot` when the loader+singleflight combo is the load-bearing requirement and I'm willing to pin the version.

## Cross-refs

- See `oops.md` - wrap loader errors with structured context
- See `vd:py2go` data-pipeline playbook - caching warm reads in the migrated Go service
- See `vd:debug` - Prometheus metrics live here when on-call needs to triage cache effectiveness
