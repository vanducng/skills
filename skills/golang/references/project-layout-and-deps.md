# Project Layout, Dependencies, DI, CLI & Database

## Project layout

Right-size to the problem - a 100-line CLI needs no layers, no DI, no interfaces. For anything larger, **ask the developer** their preferred architecture (flat / clean / hexagonal / DDD) and DI approach before scaffolding.

| Type | Key directories |
| --- | --- |
| CLI | `cmd/{name}/`, `internal/`, optional `pkg/` |
| Library | `pkg/{name}/`, `internal/` for private code |
| Service | `cmd/{service}/`, `internal/`, `api/`, `web/` |
| Monorepo / workspace | `go.work` + a module per package |

- **All `main` packages live in `cmd/`** with minimal logic - parse flags, wire dependencies, call `Run()`. Business logic goes in `internal/` (private) or `pkg/` (only if external consumers need it).
- Module path in `go.mod` matches the repo URL, lowercase, hyphens: `github.com/user/payment-processor` - not `MyProject`, not `utils`.
- Packages: lowercase, singular, matching the directory name.
- For services, follow 12-factor: config via env vars, logs to stdout, stateless processes, graceful shutdown, admin tasks as one-off commands (`cmd/migrate/`).
- Every project root has a `Makefile`, `.gitignore`, and `.golangci.yml`. Co-locate `_test.go` files; fixtures in `testdata/`.

## Dependency management

**Before `go get` for a *new* dependency, ask the user.** Present: import path, what it does, whether stdlib already covers it, GitHub stars / last commit / maintenance, license, alternatives. `go get -u` to upgrade an existing dep is safe. Prefer stdlib, then `golang.org/x/...` and established orgs over obscure packages.

**Key rules:** `go.sum` is committed (supply-chain integrity); `go mod tidy` before any commit that changes deps; `govulncheck ./...` before every release.

```bash
go get github.com/pkg/errors@v0.9.1   # pin a version
go get -u=patch ./...                  # safest routine upgrade (patch only, no API change)
go get github.com/pkg/errors@none && go mod tidy   # remove
go mod why -m github.com/some/module   # why is this here?
go install golang.org/x/vuln/cmd/govulncheck@latest
```

Pin CLI tools with a `//go:build tools` file (blank imports keep them in `go.mod`). Vendor (`go mod vendor`) only for hermetic/offline builds. Automate updates with Dependabot/Renovate. Semver + Minimal Version Selection means you can't just take "latest" - patch is safe, minor may change behavior, major needs a `/vN` path suffix.

## Dependency injection

DI = pass dependencies in, don't create or find them. Testable, loosely coupled.

1. Inject via **constructors** - never globals or `init()` for service setup.
2. **< 10 services → manual constructor injection**, no library.
3. Accept interfaces (defined where consumed), return concrete structs.
4. No package-level service locators; the container lives only at the composition root (`main()`) - never pass the container as a dependency.
5. Keep the dependency graph shallow; deep chains signal a design problem.

```go
type UserService struct {
    db     UserStore
    mailer Mailer
    logger *slog.Logger
}
func NewUserService(db UserStore, mailer Mailer, logger *slog.Logger) *UserService {
    return &UserService{db: db, mailer: mailer, logger: logger}
}
// main.go wires it explicitly
```

Adopt a library only past ~10-20 services or when you need lifecycle management (health checks, graceful shutdown, lazy init). Options: `google/wire` (compile-time codegen), `uber-go/fx`/`dig` (reflection, built-in lifecycle), `samber/do` v2 (generics, no codegen - see **gostack**). Mock at the interface boundary in tests.

## CLI applications

Default stack: **Cobra + Viper** (powers kubectl, docker, gh). Trivial single-purpose tools can use stdlib `flag`.

- `cmd/myapp/` with one file per command; `main.go` only calls `Execute()`.
- Root command: `SilenceUsage: true` and `SilenceErrors: true` (control error output yourself); init Viper in `PersistentPreRunE`.
- **Bind every configurable flag to Viper** (`viper.BindPFlag`) so precedence is flag → env (`MYAPP_PORT` via `SetEnvPrefix`) → config file → default. Config file is optional (ignore `ConfigFileNotFoundError`).
- **stdout = program output (pipeable), stderr = logs/diagnostics** - never log to stdout. Support `--output table|json|plain` for scripts; `fatih/color` auto-disables off-terminal.
- Never `os.Exit()` inside `RunE` (skips defers/cleanup) - return an error, let `main()` map it to an exit code (0 ok, 1 error, 2 usage, 128+N signal). Use `cmd.OutOrStdout()`/`ErrOrStderr()` so tests can capture output.
- Embed version via `-ldflags` at build time; `signal.NotifyContext` for graceful shutdown.

## Database access

Use `database/sql` with `sqlx` or `pgx` for ergonomics - **never an ORM** (unpredictable queries, hidden N+1, migrations coupled to app code).

| Library | Best for |
| --- | --- |
| `sqlx` | Multi-database, `StructScan` |
| `pgx` | PostgreSQL (30-50% faster, COPY/LISTEN/arrays) |

1. **Parameterized queries always** - never concat user input; allowlist dynamic column names; `sqlx.In` + `Rebind` for `IN (?)`.
2. Pass context to every operation (`QueryContext`, `ExecContext`, `GetContext`).
3. Handle `sql.ErrNoRows` explicitly with `errors.Is` - distinguish "not found" from a real error, translate to a domain error.
4. `defer rows.Close()` immediately after `QueryContext`; check `rows.Err()` after the loop. Use `Exec` (not `Query`) for non-returning statements or the connection leaks.
5. Transactions for multi-statement writes; `SELECT ... FOR UPDATE` when reading rows you'll modify; raise isolation for financial ops.
6. Configure the pool: `SetMaxOpenConns`, `SetMaxIdleConns`, `SetConnMaxLifetime`, `SetConnMaxIdleTime`.
7. NULLable columns → pointer fields (`*string`) or `sql.NullXxx`.
8. **Never generate schemas or migrations by hand/AI** - use golang-migrate/Atlas/Flyway, human-reviewed, versioned, CI-applied. Schema design needs production data-volume and access-pattern knowledge an agent doesn't have. Avoid triggers/views/stored procedures in app logic (invisible side effects).
