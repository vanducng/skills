# Stack: Go

Evidence only. Scope, skippability, skip conditions, floor rules, and the `Fix:` classification for every
signal below live in `../signals.md`; this file says what counts as evidence in this ecosystem. Each row is
additive to that signal's catch-all clause - a stack row never overrides the catch-all, and a signal passes
for the app when any one clause (this file's or the catch-all's) holds.

## Detection

| Field | Value |
|---|---|
| Detect by | `go.mod` |
| Manifests / lockfiles | `go.mod`, `go.sum` |
| First-party sources | `.go` |
| Notes | The compiler covers type checking, and the toolchain ships `gofmt` and `go vet`, so several signals here score the **gate** rather than the tool's existence. |

## Stack-heavy signals (all 13, one row each)

| signal_id | Evidence (PASS if any one) | Notes |
|---|---|---|
| test_command_declared | At least one `*_test.go` file | `go test ./...` is implicit; no script declaration is needed |
| test_command_runnable | `go test -run XXX_none ./...` | Compiles the test binaries without executing any test. Fail on a build error |
| lint_configured | `.golangci.yml`, or a CI step running `go vet ./...` | |
| format_check_available | A CI step asserting `gofmt -l .` is empty | The toolchain provides gofmt, so the *check* is the signal |
| static_analysis_configured | `go vet` in CI, or golangci-lint with `staticcheck`/`govet` enabled | The compiler covers types |
| coverage_threshold_enforced | A CI step comparing `go tool cover` output against a floor | Subject to the floor rule in `../signals.md`: a committed `0`, or any value at or below 1 percent, fails |
| dependencies_locked | `go.sum` committed | A gitignored `go.sum` fails even when present locally |
| runtime_version_pinned | `.tool-versions` or `mise.toml`; or an immutable image reference (digest or exact tag such as `golang:1.23.4-alpine`) | The `go` directive in `go.mod` is a compatibility declaration and does **not** pin |
| module_boundaries_enforced | A `depguard` golangci-lint rule, or an `internal/` directory whose boundary the instruction file or architecture doc states | The compiler enforces `internal/`, which is why the stated boundary counts here. Documentation alone passes for no other clause |
| dead_code_detection | `unused` enabled in golangci-lint | `deadcode` is deactivated and no longer runs; it does not pass |
| duplicate_code_detection | A committed duplicate-detection config a command or CI step invokes (`jscpd` on Go sources, a CPD run) | A committed `.codeclimate.yml`/`sonar-project.properties` with duplication rules on also passes (universal clause) |
| file_size_or_complexity_guard | golangci-lint `funlen`, `gocyclo`, or `cyclop` | |
| naming_conventions_stated | Automated: golangci-lint `revive` naming rules | Otherwise the documentation clause in `../signals.md` (3 of 4 categories) decides it; `*_test.go` is a literal pattern that counts for the tests category |

## Supplementary detail for universal signals

| signal_id | Per-stack detail |
|---|---|
| env_vars_documented | Env-access API: `os.Getenv` |
| service_dependencies_documented | No framework row in the driver extractor table; Go contributes only through its env keys and compose `image:` entries |
| tech_debt_markers_tracked | No first-party marker lint rule; use a committed scanner script or CI step |
