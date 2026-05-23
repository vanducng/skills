# samber/do v2 — Dependency injection for Go

**Pinned: v2.0.0 (released 2025-09-21) · MIT · verified 2026-05-23**

Type-safe DI container for Go 1.18+ using generics. Lazy/eager/transient/value service lifecycles, packages (modules), scopes, graceful shutdown, health checks. v2 broke compatibility with v1 — **never use v1**.

Upstream: [github.com/samber/do](https://github.com/samber/do) · [do.samber.dev](https://do.samber.dev) · [pkg.go.dev/v2](https://pkg.go.dev/github.com/samber/do/v2)

## My take

The right answer when the service graph in `main.go` no longer fits on a screen. Wire and Fx are the alternatives — I picked `do` v2 for new projects because:

- **Generic-based API** reads better in PRs than Wire's codegen or Fx's reflection-heavy options
- **Runtime container** means I can introspect, swap services in tests, and add health checks without re-generation cycles
- **Lifecycle + signal handling** built in — `ShutdownOnSignalsWithContext` removes ~30 lines of boilerplate

**Where I deviate from upstream guidance:**

- The README walks through `do.Package()` early — I treat **manual constructor wiring as the default until the graph exceeds ~20 services**. Premature DI containers ossify a small codebase. The win arrives when the wiring itself becomes a documentation problem.
- I prefer **`do.InvokeAs[Interface]`** (implicit aliasing) over explicit alias registration. The point of DI is dependency-on-interfaces; the explicit alias step is ceremony.
- `do.MustInvoke` is fine at the composition root (main.go startup) — the process should die if the container can't resolve. Inside request paths, use `do.Invoke` and propagate the error.

**Hard rule:** v1 is dead. Migrating from v1 → v2 is a full rewrite of registrations, not a path-update.

## Install

```bash
go get github.com/samber/do/v2@v2.0.0
# the /v2 path is mandatory — `github.com/samber/do` (no /v2) installs the dead v1
```

```go
import "github.com/samber/do/v2"
```

## Core concepts

```go
injector := do.New()
```

Service lifecycle types:

| Type | Behavior | Use for |
|---|---|---|
| **Lazy** (default) | Built on first invoke, cached for life of container | Most services |
| **Eager** | Built immediately when container starts | Things that must validate at startup (DB connection check) |
| **Transient** | New instance every `Invoke` | Per-request scoped, stateless utilities |
| **Value** | Pre-built value, no constructor | Config structs, constants |

Provider signature:

```go
type Provider[T any] func(i do.Injector) (T, error)
```

## My patterns

### 1. Register accepting interfaces, returning structs

```go
type Database interface {
    Query(ctx context.Context, sql string, args ...any) (Rows, error)
}

// Concrete type returned, container can resolve to interface via InvokeAs
do.Provide(injector, func(i do.Injector) (*postgres.DB, error) {
    cfg := do.MustInvoke[*Config](i)
    return postgres.Connect(cfg.DatabaseURL)
})
```

### 2. Invoke — error at startup, panic-on-error at composition root

```go
// main.go — composition root, panic on missing service is correct
db := do.MustInvoke[*postgres.DB](injector)
srv := do.MustInvoke[*http.Server](injector)

// inside a handler / service — propagate the error
func (h *Handler) ServeHTTP(...) {
    db, err := do.Invoke[*postgres.DB](h.injector)
    if err != nil {
        return oops.Wrapf(err, "db unavailable")
    }
    // ...
}
```

### 3. Implicit aliasing — invoke as interface

```go
// Register the concrete type
do.Provide(injector, func(i do.Injector) (*postgres.DB, error) {
    return postgres.Connect("…")
})

// Invoke as the interface, no separate alias registration
db := do.MustInvokeAs[Database](injector)
```

### 4. Named services — multiple instances of same type

```go
do.ProvideNamed(injector, "primary-db", func(i do.Injector) (*postgres.DB, error) {
    return postgres.Connect("postgres://primary…")
})
do.ProvideNamed(injector, "replica-db", func(i do.Injector) (*postgres.DB, error) {
    return postgres.Connect("postgres://replica…")
})

primary := do.MustInvokeNamed[*postgres.DB](injector, "primary-db")
replica := do.MustInvokeNamed[*postgres.DB](injector, "replica-db")
```

### 5. Packages — modular registration

```go
// internal/infra/package.go
var Package = do.Package(
    do.Lazy(func(i do.Injector) (*Config, error) {
        return loadConfig()
    }),
    do.Lazy(func(i do.Injector) (*postgres.DB, error) {
        cfg := do.MustInvoke[*Config](i)
        return postgres.Connect(cfg.DatabaseURL)
    }),
)

// internal/service/package.go
var Package = do.Package(
    do.Lazy(NewUserService),
    do.Lazy(NewOrderService),
)

// cmd/server/main.go
injector := do.New(
    infra.Package,
    service.Package,
    transport.Package,
)
```

### 6. Graceful shutdown — built in

```go
func main() {
    injector := do.New(infra.Package, service.Package, transport.Package)

    srv := do.MustInvoke[*http.Server](injector)
    go srv.ListenAndServe()

    // Blocks until SIGINT/SIGTERM, then shuts down all registered services in reverse order
    _ = injector.ShutdownOnSignalsWithContext(context.Background(), os.Interrupt, syscall.SIGTERM)
}
```

Services implementing the `do.Shutdownable` interface (any of `Shutdown()`, `Shutdown() error`, `Shutdown(context.Context)`, `Shutdown(context.Context) error`, `Healthcheck()`, …) get called automatically.

### 7. Health checks

```go
type DB struct { *sql.DB }
func (d *DB) HealthCheck() error { return d.Ping() }

// In transport: aggregate all services' health
status := injector.HealthCheck()  // map[string]error
```

## API quick reference

### Registration

| Function | Purpose |
|---|---|
| `do.Provide[T]` | Lazy service (default) |
| `do.ProvideNamed[T]` | Lazy with name |
| `do.ProvideValue[T]` | Pre-built value |
| `do.ProvideNamedValue[T]` | Named value |
| `do.ProvideTransient[T]` | New instance per invoke |
| `do.ProvideNamedTransient[T]` | Named transient |
| `do.Package(...)` | Group of registrations |
| `do.Lazy(fn)` / `do.Eager(value)` | Helper wrappers inside `do.Package` |

### Invocation

| Function | Returns |
|---|---|
| `do.Invoke[T]` | `(T, error)` |
| `do.InvokeNamed[T]` | `(T, error)` for named |
| `do.InvokeAs[T]` | `(T, error)` resolving by interface match |
| `do.InvokeStruct[T]` | `(T, error)` populating struct fields via tags |
| `do.MustInvoke[T]` | `T` (panics on err) — composition root only |
| `do.MustInvokeNamed[T]` | `T` (panics on err) |
| `do.MustInvokeAs[T]` | `T` (panics on err) |
| `do.MustInvokeStruct[T]` | `T` (panics on err) |

### Container lifecycle

| Method | Purpose |
|---|---|
| `injector.Shutdown()` | Shutdown all services |
| `injector.ShutdownWithContext(ctx)` | Shutdown with context |
| `injector.ShutdownOnSignals(...)` | Block on signals, then shutdown |
| `injector.ShutdownOnSignalsWithContext(ctx, ...)` | Block + context |
| `injector.HealthCheck()` | Aggregate `map[string]error` |
| `injector.ListProvidedServices()` | Debug: what's registered |

## Best practices

1. **Depend on interfaces, return concrete types** — `do.InvokeAs[Database]` resolves the concrete `*postgres.DB` via interface implementation
2. **Composition root only** — only `main.go` (or your equivalent bootstrap) should touch the container directly. Inject what each component needs via constructor args from there
3. **Shallow trees** — chains beyond 3-4 levels make init order fragile. Refactor into packages
4. **Errors in providers are first-class** — a silently failing provider creates a broken service that crashes later in unexpected places. Return the error from the provider
5. **Use scopes for request-scoped state** — `do.NewScope(parent)` gives you a sub-container per request that inherits parent services. Don't put per-request state in the root container
6. **Use packages to mirror your folder layout** — `infra/`, `service/`, `transport/` each export a `Package` and `main.go` composes them. This makes the dep graph visible

## Common mistakes

| Mistake | Why | Fix |
|---|---|---|
| Installing `samber/do` (no /v2) | Pulls dead v1 | Use `samber/do/v2` |
| Container leaks into request handlers | Tight coupling, hard to test | Inject services into the handler at composition root |
| `do.MustInvoke` in request paths | One missing service crashes the process | Use `do.Invoke` and propagate the error |
| Massive root container, all services lazy | First request pays cold-start cost for everything | Mix `Eager` for things that must validate at startup |
| Provider does heavy work inline | Container init blocks startup | Defer expensive init to a `Start()` method called explicitly |
| No `Shutdown()` on services with resources | DB connections, file handles leak | Implement `Shutdown() error` on services that own resources |

## When I'd skip `do`

- Service graph fits on one screen (≤ ~15-20 nodes). Manual wiring in `main.go` is more readable than a container for small programs.
- Library code — DI containers don't belong in libraries. Let your callers wire their own dependencies.
- Single-file CLI tools.
- Performance-critical hot path that allocates per request — measure whether `do.Invoke` is in the budget. Usually fine, but verify.

## Comparison with Wire and Fx (my own ranking)

| Concern | `samber/do` v2 | `google/wire` | `uber-go/fx` |
|---|---|---|---|
| API readability | Generic-based, reads as Go | Codegen — generated file is unreadable | Tag-based options, lots of magic |
| Error timing | Runtime | Compile-time | Runtime |
| Lifecycle hooks | Yes (Shutdown/HealthCheck) | None | Yes, richest |
| Learning curve | Lowest | Medium (codegen workflow) | Highest |
| Best for | New services, small-to-medium graphs | Large monorepos with compile-time correctness needs | Microservice frameworks |

**My pick for new projects: `samber/do` v2.** Wire wins when the team values compile-time DI errors above all. Fx wins when you're already in Uber-style microservice land.

## Cross-refs

- See `oops.md` for error returns from providers
- See `vd:py2go` HTTP playbook — `do` v2 is the default DI when graph grows
- See `vd:cook` review gate for catching container abuse (Invoke called from non-root code)
