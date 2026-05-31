# samber/mo — Monads and FP abstractions for Go

**Pinned: v1.16.0 (released 2025-09-25) · MIT · verified 2026-05-23**

Generics-first Option, Result, Either, Future, IO, Task, and State types for Go 1.18+. Inspired by Scala, Rust, fp-ts. Zero dependencies.

Upstream: [github.com/samber/mo](https://github.com/samber/mo) · [pkg.go.dev](https://pkg.go.dev/github.com/samber/mo)

## My take

Skeptical adoption. Go is not an FP language; pretending it is creates code Go reviewers don't want to maintain. The library is well-built — my objection is sociological, not technical.

**What I actually keep from `mo`:**

- **`Option[T]`** for JSON nullable fields. It implements `json.Marshaler/Unmarshaler`, `sql.Scanner`, `driver.Valuer` — drop-in for `*string` / `sql.NullString` and reads cleaner. **This is the only `mo` type I'd reach for in a typical service.**

**What I skip:**

- **`Result[T]`** chains read worse than `if err != nil` to a Go-trained reviewer. The pattern wins in Rust because the compiler enforces it; in Go, you're just adopting a style. I leave Result for codebases where the whole team is on board with FP.
- **`Either[L, R]`** — useful in theory (cached vs fresh, strategy A vs B). In practice, Go's pattern is two-return-value with an enum tag, which is fine and idiomatic. I haven't found a place where `Either` was a clear win.
- **`Future`, `IO`, `Task`, `State`** — niche. Go has goroutines and channels; lazy effect monads layered on top are cognitive overhead without payoff.

**Where I deviate from upstream guidance:**

- The README presents the full menu equally. I think `Option[T]` for JSON nullables is the 95% case for adoption; everything else is a discretionary FP choice for FP-friendly teams.
- The Go limitation around method type parameters (can't change `Result[T]` to `Result[U]` via `.Map`) is real. The sub-package + Pipe approach works but feels heavier than just writing the imperative version. I default to `mo.Do` when I do need monadic chaining — at least the inner code reads imperatively.

## Install

```bash
go get github.com/samber/mo@v1.16.0
```

## Core types at a glance

| Type | Purpose | Mental model |
|---|---|---|
| `Option[T]` | Value may be absent | Rust `Option`, Java `Optional` |
| `Result[T]` | Operation may fail | Rust `Result<T, E>`, replaces `(T, error)` |
| `Either[L, R]` | Value of one of two types | Scala `Either`, TS discriminated union |
| `Either3…Either5` | One of 3–5 types | Same, wider |
| `Future[T]` | Async value not yet available | JS `Promise` |
| `IO[T]` | Lazy synchronous effect | Haskell `IO` |
| `Task[T]` | Lazy async computation | fp-ts `Task` |
| `State[S, A]` | Stateful computation | Haskell `State` |

## `Option[T]` — the one I actually adopt

```go
import "github.com/samber/mo"

name := mo.Some("Alice")
absent := mo.None[string]()

name.OrElse("Anonymous")        // "Alice"
absent.OrElse("Anonymous")      // "Anonymous"
name.IsPresent()                // true
name.MustGet()                  // "Alice" — panics if None

// from a (T, bool) tuple — common Go idiom
val := mo.TupleToOption(m["key"])  // map[string]V lookup → Option[V]

// from a pointer
ptr := mo.PointerToOption(maybePtr)
```

### JSON nullable fields — drop-in, no `omitempty` games

```go
type UserResponse struct {
    Name     string             `json:"name"`
    Nickname mo.Option[string]  `json:"nickname"`  // None → JSON null
    Bio      mo.Option[string]  `json:"bio"`
}
```

vs the alternatives:

- `*string` — works but pointers leak into business logic
- `sql.NullString` — DB-flavored, doesn't marshal cleanly to JSON

### Database nullable columns

```go
type User struct {
    ID    int
    Email string
    Phone mo.Option[string]   // implements sql.Scanner + driver.Valuer
}

row.Scan(&u.ID, &u.Email, &u.Phone)
```

## `Result[T]` — when I'd use it

```go
import "github.com/samber/mo"

// Wrap Go's (T, error) at the boundary
result := mo.TupleToResult(os.ReadFile("config.yaml"))

// Same-type chain (works with method-style)
upper := mo.Ok("hello").Map(func(s string) (string, error) {
    return strings.ToUpper(s), nil
})

// Extract with fallback
val := upper.OrElse("default")
```

**The Go method limitation:** `Result[T].Map` returns `Result[T]`, not `Result[U]`. To change the type, use sub-package functions or `mo.Do`:

```go
import "github.com/samber/mo/result"

parsed := result.Pipe2(
    mo.TupleToResult(os.ReadFile("config.yaml")),
    result.Map(func(data []byte) Config { return parseConfig(data) }),
    result.FlatMap(func(cfg Config) mo.Result[ValidConfig] { return validate(cfg) }),
)
```

I generally find this less readable than:

```go
data, err := os.ReadFile("config.yaml")
if err != nil {
    return ValidConfig{}, oops.Wrapf(err, "read config")
}
cfg := parseConfig(data)
return validate(cfg)
```

The imperative version wins for Go reviewers nine times out of ten.

## `mo.Do` — imperative-style with monadic safety

The one Result feature I find genuinely interesting. `mo.Do` wraps imperative code; `MustGet()` panics inside, `Do` catches the panic and returns `Result`.

```go
result := mo.Do(func() int {
    a := mo.Some(21).MustGet()    // would panic if None
    b := mo.Ok(2).MustGet()       // would panic if Err
    return a * b                  // 42
})
// Result is Ok(42)

result := mo.Do(func() int {
    val := mo.None[int]().MustGet()  // panics → caught by Do
    return val
})
// Result is Err("no such element")
```

Use case: when you have several monadic values and want straight-line code instead of nested `FlatMap` calls.

## Pipelines — direct methods vs sub-package functions

```go
// Direct method: same-type transform — fine
mo.Some(42).Map(func(v int) (int, bool) {
    return v * 2, true
})  // Option[int]
```

```go
// Type-changing transform: needs sub-package
import "github.com/samber/mo/option"

option.Map(func(v int) string {
    return fmt.Sprintf("value: %d", v)
})(mo.Some(42))  // Option[string]
```

```go
// Multi-step pipeline
import "github.com/samber/mo/option"

result := option.Pipe3(
    mo.Some(42),
    option.Map(func(v int) string { return strconv.Itoa(v) }),
    option.Map(func(s string) []byte { return []byte(s) }),
    option.FlatMap(func(b []byte) mo.Option[string] {
        if len(b) > 0 { return mo.Some(string(b)) }
        return mo.None[string]()
    }),
)
```

**Rule of thumb:** direct methods for same-type, sub-package + Pipe when types change across steps.

## `Either[L, R]` — when both sides are valid

```go
func fetchUser(id string) mo.Either[CachedUser, FreshUser] {
    if c, ok := cache.Get(id); ok {
        return mo.Left[CachedUser, FreshUser](c)
    }
    return mo.Right[CachedUser, FreshUser](db.Fetch(id))
}
```

Use `Result[T]` for success/failure. Use `Either[L, R]` only when both sides are valid alternatives (cached vs fresh, strategy A vs B). In my experience this distinction rarely shows up in API design — most "either or" cases are really success/failure in disguise.

## Best practices (mine)

1. **Default to `Option[T]` for JSON nullables.** Replaces `*T` / `sql.NullString` cleanly.
2. **Use `TupleToOption` / `TupleToResult` at API boundaries** — convert Go's idiomatic returns to monadic values at the edge, then either chain (if your team likes that style) or unwrap immediately.
3. **`MustGet` is panic-on-error** — fine in tests, init, and inside `mo.Do`. Avoid in handlers.
4. **`Result[T]` for errors, `Either[L, R]` for alternatives** — don't mix them up.
5. **Pipes for 3+ type-changing steps** — `option.Pipe3` is more readable than nested function calls only when types actually change at each step.

## Common mistakes

| Mistake | Why | Fix |
|---|---|---|
| Using `mo.None` where empty string is valid | Loses the "absent" semantics | Use plain `string` if "" is a valid value |
| `Result[T].Map` for type-changing transform | Methods can't change type param | Use sub-package `result.Map` or `mo.Do` |
| `MustGet` in request paths | Panic surfaces as 500 | Use `OrElse`, `Match`, or `mo.Do` block |
| Adopting `Result[T]` codebase-wide on an unfamiliar team | Friction, bad PRs, churn | Keep it localized, or skip entirely |
| `Either` where `Result` fits | "Failure" is not a "valid alternative" | Use `Result` for ok/err semantics |

## When I'd skip `mo` entirely

- Codebase is unfamiliar with FP and team velocity matters more than purity
- Performance-critical code — wrapper types add allocation; benchmark before adopting in hot paths
- Public library API — don't impose `mo.Option`/`mo.Result` on your callers; return idiomatic Go types

## When the team is already FP-leaning

Then go all in — the chaining-style payoff compounds. Pair with `samber/lo` for the slice-side operations; the two libraries compose naturally.

## Cross-refs

- See `lo.md` for slice transforms that compose with `Option`/`Result` outputs
- See `oops.md` for error context when you do unwrap to Go's `(T, error)` at boundaries
- See `vd:py2go` translation rules — Python `Optional[T]` maps to `mo.Option[T]` for JSON-bound structs
