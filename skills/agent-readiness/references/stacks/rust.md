# Stack: Rust

Evidence only. Scope, skippability, skip conditions, floor rules, and the `Fix:` classification for every
signal below live in `../signals.md`; this file says what counts as evidence in this ecosystem. Each row is
additive to that signal's catch-all clause - a stack row never overrides the catch-all, and a signal passes
for the app when any one clause (this file's or the catch-all's) holds.

## Detection

| Field | Value |
|---|---|
| Detect by | `Cargo.toml` |
| Manifests / lockfiles | `Cargo.toml`, `Cargo.lock` |
| First-party sources | `.rs` |
| Notes | The compiler covers types and warns on dead code by default, so several signals here score the **gate** rather than the warning. |

## Stack-heavy signals (all 13, one row each)

| signal_id | Evidence (PASS if any one) | Notes |
|---|---|---|
| test_command_declared | `#[test]` or `#[cfg(test)]` in `src/`, or a `tests/` directory | |
| test_command_runnable | `cargo test --no-run` | Builds the test binaries without running them |
| lint_configured | A CI step running `cargo clippy`, or `[lints]` in `Cargo.toml`, or `clippy.toml` | |
| format_check_available | A declared `cargo fmt --check` command or CI step | `rustfmt.toml` alone only configures style and does not pass |
| static_analysis_configured | `cargo clippy -- -D warnings` in CI | The compiler covers types |
| coverage_threshold_enforced | A `cargo tarpaulin --fail-under N` step, or `cargo llvm-cov --fail-under-lines N` | Note the differing flag names per tool. Subject to the floor rule in `../signals.md`: a committed `0`, or any value at or below 1 percent, fails |
| dependencies_locked | `Cargo.lock` committed | An MSRV plus a CI matrix does **not** pass: it constrains the compiler, not the dependency set, and a fresh checkout still resolves new versions |
| runtime_version_pinned | `rust-toolchain.toml`, `.tool-versions`, or `mise.toml`; or an immutable image reference (digest or exact tag such as `rust:1.83.0-slim`) | `rust-version` in `Cargo.toml` is a compatibility declaration and does **not** pin |
| module_boundaries_enforced | A workspace with more than one member crate plus a `cargo-deny`/clippy disallowed-path rule | Documentation alone never passes this signal |
| dead_code_detection | `#![deny(dead_code)]`, or `cargo-udeps` in CI | rustc warns by default; the *gate* is the signal |
| duplicate_code_detection | A committed duplicate-detection config a command or CI step invokes | A committed `.codeclimate.yml`/`sonar-project.properties` with duplication rules on also passes (universal clause) |
| file_size_or_complexity_guard | clippy `cognitive_complexity` or `too_many_lines` enabled | |
| naming_conventions_stated | Automated: rustc's built-in `non_snake_case`/`non_camel_case_types` lints raised to deny, or a clippy naming lint | Otherwise the documentation clause in `../signals.md` (3 of 4 categories) decides it |

## Supplementary detail for universal signals

| signal_id | Per-stack detail |
|---|---|
| env_vars_documented | Env-access API: `std::env::var` |
| service_dependencies_documented | No framework row in the driver extractor table; Rust contributes only through its env keys and compose `image:` entries |
| tech_debt_markers_tracked | No first-party marker lint rule; use a committed scanner script or CI step |
