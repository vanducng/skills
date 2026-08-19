# Testing, Linting, Modernization & CI

## Testing

Tests are executable specifications - write them to constrain behavior, not to hit a coverage number.

1. **Table-driven with named subtests** - every case has a `name` field passed to `t.Run`.
2. Tests must be **order-independent** and independently runnable; add `t.Parallel()` when they are.
3. **Test observable behavior and public contracts, not implementation details.**
4. Integration tests behind a build tag (`//go:build integration`), run with `go test -tags=integration ./...`.
5. Keep unit tests fast (<1ms) and dependency-free.
6. Mock **interfaces, not concrete types** - define the interface where consumed.
7. Packages with goroutines: `goleak.VerifyTestMain(m)` in `TestMain` to catch leaks.
8. `ExampleXxx` functions are executable documentation (verified by `go test`).

```go
func TestCalculatePrice(t *testing.T) {
    tests := []struct {
        name              string
        quantity          int
        unitPrice, expect float64
    }{
        {"single item", 1, 10.0, 10.0},
        {"bulk discount", 100, 10.0, 900.0},
        {"zero quantity", 0, 10.0, 0.0},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            if got := CalculatePrice(tt.quantity, tt.unitPrice); got != tt.expect {
                t.Errorf("CalculatePrice(%d, %.2f) = %.2f, want %.2f", tt.quantity, tt.unitPrice, got, tt.expect)
            }
        })
    }
}
```

Use `httptest` for handlers, `t.Context()` (1.24+) for context, fuzzing (`func FuzzX(f *testing.F)`) to find edge cases, `testing/synctest` (1.24+, experimental) for deterministic time in concurrent tests. Coverage: `go test -coverprofile=coverage.out ./... && go tool cover -func=coverage.out`.

**testify** complements (doesn't replace) `testing`. `assert` records and continues; `require` calls `FailNow()` - use `require` for preconditions where continuing would panic, `assert` for verifications. Bind with `is := assert.New(t)` / `must := require.New(t)`. Argument order is always `(expected, actual)`. Use `is.ErrorIs`/`is.ErrorAs` (walks wrapped chains) not `is.Equal` on errors. For mocks embed `mock.Mock` and always call `AssertExpectations(t)`. `suite.Suite` for shared setup/teardown (`SetupTest`/`TearDownTest`), with the required `func TestXSuite(t *testing.T) { suite.Run(t, new(XSuite)) }` launcher. Enforced by `testifylint`, `thelper`, `paralleltest`.

## Linting

`golangci-lint` is the standard - every project has a `.golangci.yml` (source of truth for enabled linters). Run frequently and in CI.

```bash
golangci-lint run ./...          # all configured linters
golangci-lint run --fix ./...    # auto-fix
golangci-lint fmt ./...          # format (v2+)
```

Suppress sparingly - fix the root cause. `//nolint` **must** name the linter and give a reason: `//nolint:errcheck // fire-and-forget logging`. `nolintlint` enforces both. Never blanket-suppress security linters. On legacy code, `issues.new-from-rev: HEAD~1` lints only changed code. Makefile targets: `lint` / `lint-fix` / `fmt`.

## Modernization

Keep code on current Go idioms (covers Go 1.21-1.26). Never do large refactors while the developer is on another task - mention opportunities, let them decide, and record ignored suggestions in a `.modernize` file so they aren't re-suggested. The `modernize` linter (golangci-lint v2.6.0+) auto-detects many of these.

**High priority (safety/correctness):** remove loop-var shadow copies (1.22); `math/rand` → `math/rand/v2` (drop `rand.Seed`); `os.Root` for user paths (1.24); `errors.Is`/`As`; migrate deprecated crypto (`crypto/ecdh`, `crypto/sha3`, etc.); run `govulncheck`.

**Readability:** `interface{}` → `any`; `min`/`max` builtins (1.21); `range` over int (1.22); `slices`/`maps` packages; `cmp.Or` for defaults; `sync.OnceValue`; `t.Context()`/`b.Loop()` (1.24).

**Gradual:** migrate third-party loggers → `slog`; adopt iterators (1.23) where they simplify; `sort.Slice` → `slices.SortFunc`; PGO for prod builds; tool deps as `go.mod` `tool` directives (1.24).

Common deprecations: `reflect.SliceHeader`→`unsafe.Slice`; `runtime.SetFinalizer`→`runtime.AddCleanup` (1.24); `golang.org/x/crypto/{sha3,hkdf,pbkdf2}`→stdlib `crypto/*` (1.24); `httputil.ReverseProxy.Director`→`.Rewrite` (1.26). Reference the version changelog when suggesting a change.

## CI (GitHub Actions)

Production pipeline stages: **test → lint → security → release**. Check the latest action major versions before writing YAML (don't hardcode stale `@vN`); pin to a major version, never `@master`; least-privilege `permissions` per job.

| Stage | Tool |
| --- | --- |
| Test | `go test -race -shuffle=on -coverprofile=…` across a Go-version matrix with `fail-fast: false` |
| Coverage | `codecov/codecov-action` |
| Lint | `golangci/golangci-lint-action` |
| SAST | `gosec`, CodeQL (`security-extended`), Bearer |
| Vuln scan | `govulncheck` (reports only reachable CVEs) |
| Docker | `docker/build-push-action` (`push: false` on PRs), Trivy image scan |
| Deps | Dependabot or Renovate (Renovate: native automerge, `gomodTidy`, monorepo-aware) |
| Release | GoReleaser (CLI: cross-compiled binaries; library: changelog-only) |

Must-haves: `-race` (races are undefined behavior); `-shuffle=on` (catches inter-test coupling); `-count=1` on integration tests (defeats caching); a `go mod tidy && git diff --exit-code` step. Dependabot auto-merge needs branch protection with required checks as the real safety net - the `github.actor` guard alone isn't spoof-proof.
