# samber/oops — Structured error handling for Go

**Pinned: v1.21.0 (released 2026-01-18) · MIT · verified 2026-05-23**

A drop-in replacement for Go's standard `error` that adds structured context, stack traces, error codes, public messages, and panic recovery. Variable data goes in `.With("key", value)` attributes, **not** the message string — so APM tools (Datadog, Sentry, Loki) group errors properly.

Upstream: [github.com/samber/oops](https://github.com/samber/oops) · [pkg.go.dev](https://pkg.go.dev/github.com/samber/oops)

## My take

Highest-leverage library in the samber ecosystem for any service that gets on-call rotations. Three problems it solves at once:

1. **APM grouping breaks when error messages embed variable data** — `oops` forces the low-cardinality discipline by giving you `.With()` for the variable stuff.
2. **Stack traces are auto-captured** — no `pkg/errors`-style boilerplate.
3. **Public vs technical messages separate cleanly** — `.Public()` carries the user-safe string; `.Error()` carries the developer-grade detail.

**Where I deviate from upstream guidance:**

- The upstream README implies "use everywhere" — I don't. I adopt `oops` at **architectural boundaries** (HTTP handlers, repository methods, worker entrypoints, package edges) and leave plain `fmt.Errorf("…: %w", err)` inside leaf functions. The cost/benefit of `.In().Tags().With().Code().Wrap()` only pays off where errors cross layers.
- `.Recover()` for panic-to-error conversion is **mandatory** at goroutine boundaries. Non-negotiable.
- I keep the builder reusable per request — build it once in middleware (`builder := oops.In("http").Trace(traceID)`), stash it in the context with `oops.WithBuilder(ctx, b)`, retrieve in handlers via `oops.FromContext(ctx)`. Avoid re-declaring the prefix attributes at every error site.

## Install

```bash
go get github.com/samber/oops@v1.21.0
```

## The builder chain

Every `oops` error is built fluently. Terminal methods produce the actual `error`:

```go
err := oops.
    In("user-service").                    // domain/feature
    Tags("database", "postgres").          // categorization
    Code("user_fetch_timeout").            // machine-readable id
    User("user-123").                      // user context
    With("query", query).                  // attribute (low-cardinality message safe)
    Wrapf(rootErr, "failed to fetch user")
```

Terminal methods:

| Method | Purpose |
|---|---|
| `.Errorf(fmt, args...)` | Create new error |
| `.Wrap(err)` | Wrap existing error (returns nil if err is nil) |
| `.Wrapf(err, fmt, args...)` | Wrap with message |
| `.Join(errs...)` | Combine multiple errors |
| `.Recover(fn)` / `.Recoverf(fn, fmt, args...)` | Convert panic to error |

Builder methods (most-used):

| Method | Use |
|---|---|
| `.With("key", v)` | Attribute — low-cardinality grouping safe |
| `.WithContext(ctx, "k1", "k2")` | Pull keys out of `context.Context` |
| `.In("domain")` | Service/feature name |
| `.Tags("auth", "sql")` | Categorization (queryable via `err.HasTag(...)`) |
| `.Code("iam_missing_perm")` | Machine-readable slug |
| `.Public("Could not fetch user.")` | User-safe message |
| `.Hint("See runbook at …")` | Dev-facing hint |
| `.Owner("team-name")` | Who pages on this |
| `.User(id, "k", "v")` | User context |
| `.Tenant(id, "k", "v")` | Tenant/org context |
| `.Trace(id)` | Correlation ID |
| `.Request(req, includeBody)` | Attach `*http.Request` |
| `.Response(res, includeBody)` | Attach `*http.Response` |

## My patterns

### HTTP middleware that builds the prefix

```go
func ContextErrorBuilder(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        b := oops.
            In("http").
            Request(r, false).
            Trace(r.Header.Get("X-Trace-ID"))
        ctx := oops.WithBuilder(r.Context(), b)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}

func handler(ctx context.Context) error {
    // pulls the request-scoped builder, adds handler-specific attrs
    return oops.FromContext(ctx).
        Tags("endpoint", "/users").
        Wrapf(svc.CreateUser(ctx), "create user failed")
}
```

### Repository — domain + tags + query attribute

```go
func (r *UserRepo) Fetch(ctx context.Context, id string) (*User, error) {
    q := `SELECT * FROM users WHERE id = $1`
    row, err := r.db.QueryRow(ctx, q, id)
    if err != nil {
        return nil, oops.
            In("user-repo").
            Tags("database", "postgres").
            With("query", q).
            With("user_id", id).
            Wrapf(err, "user fetch failed")
    }
    // …
}
```

### Goroutine boundary — `Recover` is non-optional

```go
go func() {
    err := oops.
        In("worker").
        Code("panic_recovered").
        Recover(func() {
            riskyOperation()
        })
    if err != nil {
        log.Error("worker panic", slog.Any("error", err))
    }
}()
```

### Reading the error back

```go
if oe, ok := err.(oops.OopsError); ok {
    fmt.Println(oe.Code())        // "user_fetch_timeout"
    fmt.Println(oe.Domain())      // "user-service"
    fmt.Println(oe.Tags())        // ["database", "postgres"]
    fmt.Println(oe.Context())     // map[string]any
    fmt.Println(oe.Stacktrace())  // full stack
}

publicMsg := oops.GetPublic(err, "Something went wrong")
```

Output:

```go
fmt.Printf("%+v\n", err)                              // verbose w/ stack
bytes, _ := json.Marshal(err)                         // for logs
slog.Error(err.Error(), slog.Any("error", err))       // slog integration
```

## The cardinality rule (most important)

```go
// ✗ HIGH cardinality — breaks APM grouping
oops.Errorf("failed to fetch user %s in tenant %s", userID, tenantID)

// ✓ LOW cardinality — variable data in attributes
oops.
    With("user_id", userID).
    With("tenant_id", tenantID).
    Errorf("failed to fetch user")
```

Datadog, Sentry, and Loki group errors by message — if every error has unique IDs in the message, you get 10,000 "incidents" instead of 1 incident with 10,000 occurrences. This rule is what makes `oops` worth adopting at all.

## Wrap directly — no nil check needed

```go
// ✓ Wrap returns nil if err is nil
return oops.In("svc").Wrapf(err, "operation failed")

// ✗ Verbose, unnecessary
if err != nil {
    return oops.In("svc").Wrapf(err, "operation failed")
}
return nil
```

## Common mistakes

| Mistake | Why | Fix |
|---|---|---|
| Variable data in message string | Breaks APM grouping | Move to `.With(k, v)` |
| Wrapping at every function call | Noise; stack trace already there | Wrap at package/layer boundaries |
| Forgetting `.Recover()` at goroutine entry | Panics crash process silently | Wrap goroutine body in `.Recover(fn)` |
| `.Public()` not set on user-visible errors | Tech details leak to API consumer | Set `.Public("…")` on errors returned to clients |
| Using `oops.Errorf` where you should `Wrap` | Loses root cause and stack | Use `.Wrap(err)` / `.Wrapf(err, ...)` to preserve chain |
| Re-declaring `.In().Trace()` at every site | Builder duplication | Stash in context via `oops.WithBuilder` |

## When I'd skip `oops`

- Tiny CLI tool with no on-call burden — plain errors are fine
- Library code intended for broad adoption — don't impose `oops.OopsError` on your callers; return wrapped stdlib errors and let app code add structure
- Code path where you can prove latency budget is too tight for the builder overhead (rare; measure first)

## Integration with the rest of the stack

- **`slog`**: `slog.Error(err.Error(), slog.Any("error", err))` — `oops.OopsError` implements `slog.LogValuer`, so attributes flatten into the log record automatically
- **`samber/slog-formatter`**: the upstream `slog-formatter` includes an `ErrorFormatter` that extracts `oops` attributes — pipe it into your log handler
- **OpenTelemetry**: stash the trace ID in `.Trace()`; `oops` doesn't auto-link, but you can read it back and attach to spans
- **`/vd:py2go`**: Python `loguru`/`logging` errors with `extra={}` map cleanly to `oops` `.With()` attributes during migration

## Cross-refs

- See `slog.md` reference for the logging pipeline that consumes `oops` errors
- See `/vd:debug` skill for the on-call workflow these attributes power
