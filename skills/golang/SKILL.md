---
name: golang
description: "Idiomatic Go guidance for writing and reviewing Go code - style, naming, MixedCaps, GoDoc comments, error handling (%w, errors.Is/As, sentinel errors), goroutines/channels/select/context, safety (nil maps, append aliasing, type assertions), structs/interfaces, generics, table-driven tests, testify, golangci-lint, go.mod dependency management, project layout, slog/Prometheus/OpenTelemetry observability, and gRPC. Use when writing, reviewing, or refactoring Go (.go) code, editing go.mod/go.sum, running go test or golangci-lint, debugging goroutine leaks or races, or making Go design decisions. For the samber/* library stack (lo, oops, do, mo, slog-*, hot, ro) use gostack instead."
license: MIT
metadata:
  author: vanducng
  version: "1.0.0"
---

# Go

Opinionated, idiomatic Go for AI coding agents - the rules that change what code you write. SKILL.md is the dispatcher: apply the always-on rules below, then open **exactly one** reference file for the task at hand. Distilled guidance, not exhaustive docs; when an API signature matters, verify against the current stdlib/library docs.

## When to open which reference

| Task involves… | Open |
| --- | --- |
| Writing/reviewing code, formatting, naming, doc comments, structs, interfaces, generics, design patterns (functional options, constructors), choosing a data structure | [references/style-and-naming.md](references/style-and-naming.md) |
| Creating/wrapping/inspecting errors, nil/panic pitfalls, defensive copying, numeric conversions, injection/crypto/secrets security | [references/errors-and-safety.md](references/errors-and-safety.md) |
| Goroutines, channels, select, sync primitives, errgroup, context propagation, cancellation, profiling, pprof, benchmarks, optimization, debugging leaks/races | [references/concurrency-and-performance.md](references/concurrency-and-performance.md) |
| Writing tests, table tests, testify, mocks, fuzzing, coverage, golangci-lint config, modernizing to new Go idioms, GitHub Actions CI | [references/testing-and-ci.md](references/testing-and-ci.md) |
| New project layout, `cmd/`/`internal/`/`pkg/`, go.mod dependency management, DI, CLI (cobra/viper), database access (sqlx/pgx) | [references/project-layout-and-deps.md](references/project-layout-and-deps.md) |
| slog structured logging, Prometheus metrics, OpenTelemetry tracing, gRPC servers/clients, interceptors, status codes | [references/observability-and-grpc.md](references/observability-and-grpc.md) |

For the `github.com/samber/*` ecosystem (lo, oops, do v2, mo, slog-*, hot, ro), use **gostack** - this skill defers all samber-library decisions there.

## Always-on rules (apply without opening a reference)

Load-bearing enough to enforce on every Go change:

1. **Handle errors first, early-return.** Keep the happy path at minimal indent; drop `else` after a `return`/`break`/`continue`.
2. **Never discard returned errors** with `_`. Wrap with context: `fmt.Errorf("doing x: %w", err)`. Error strings are lowercase, no trailing punctuation.
3. **Log OR return an error, never both** - duplicate logs pollute aggregators. Log once, at the top.
4. **`errors.Is`/`errors.As`, never `==` / type-assert** to inspect wrapped errors.
5. **MixedCaps, never snake_case or ALL_CAPS.** Constants are `MaxRetries`, not `MAX_RETRIES`. No stuttering: `http.Client`, not `http.HTTPClient`.
6. **`ctx context.Context` is the first parameter**; propagate the same ctx through the whole call chain; never store it in a struct; never pass `nil`.
7. **Comma-ok every type assertion** (`v, ok := x.(T)`) and initialize maps before writing (`make(map[K]V)`) - bare forms panic.
8. **Every goroutine needs a defined exit** (context, done channel, or WaitGroup) and every `select` includes `ctx.Done()`. Only the sender closes a channel.
9. **Accept interfaces, return concrete types.** Keep interfaces 1–3 methods and define them where consumed, not where implemented. Don't create an interface until a second implementation or a test mock needs it.
10. **Prefer generics over `any`** when the type set is known; prefer stdlib `slices`/`maps` over reaching for a dependency.
11. **`defer Close()` immediately after acquiring a resource** - but never `defer` inside a loop (extract the body to a function).
12. **Doc-comment every exported symbol**, starting with its name; say *why/when*, not what the signature already shows. Package comment (`// Package foo …`) is mandatory.
13. **Table-driven tests with named subtests** (`name` field → `t.Run`); run CI with `go test -race -shuffle=on`.
14. **Before adding a dependency, ask.** Check stdlib first, then maintenance/license. `go.sum` is committed; `go mod tidy` before committing dep changes; `govulncheck ./...` before release.
15. **Don't over-structure.** A 100-line CLI needs no layers, no DI container, no interfaces. Right-size to the problem.

## Verify with tooling

Every project has a `.golangci.yml`. Run `golangci-lint run --fix ./...` and `golangci-lint fmt ./...` after changes; `go vet ./...` and `go test -race ./...` before pushing. Many rules here (errcheck, revive, gofumpt, nilerr, testifylint, forcetypeassert) are machine-enforced - see [references/testing-and-ci.md](references/testing-and-ci.md).
