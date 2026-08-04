# Stack: C# / .NET

Evidence only. Scope, skippability, skip conditions, floor rules, and the `Fix:` classification for every
signal below live in `../signals.md`; this file says what counts as evidence in this ecosystem. Each row is
additive to that signal's catch-all clause - a stack row never overrides the catch-all, and a signal passes
for the app when any one clause (this file's or the catch-all's) holds.

## Detection

| Field | Value |
|---|---|
| Detect by | `*.csproj`, `*.sln` |
| Manifests / lockfiles | `*.csproj`, `packages.lock.json` |
| First-party sources | `.cs`, `.fs`, `.vb`, `.razor` |
| Notes | Analyzer configuration is spread across `.editorconfig`, `Directory.Build.props`, and the project file; a rule only counts when its severity is set where the build reads it. |

## Stack-heavy signals (all 13, one row each)

| signal_id | Evidence (PASS if any one) | Notes |
|---|---|---|
| test_command_declared | A test project referencing xunit/nunit/mstest | |
| test_command_runnable | `dotnet test --list-tests` | `dotnet build` compiles **without** discovering any test and does not satisfy this signal |
| lint_configured | `.editorconfig` with analyzer severities, or a `Directory.Build.props` enabling analyzers | |
| format_check_available | A declared `dotnet format --verify-no-changes` step | Both halves required: resolved formatter and a non-mutating check command. Plain `dotnet format` rewrites files and does not pass |
| static_analysis_configured | `<Nullable>enable</Nullable>` plus `<TreatWarningsAsErrors>` or analyzer severities at error | |
| coverage_threshold_enforced | coverlet `/p:Threshold=N` | Subject to the floor rule in `../signals.md`: a committed `0`, or any value at or below 1 percent, fails |
| dependencies_locked | `packages.lock.json`, or pinned `PackageReference` versions with `<CentralPackageTransitivePinningEnabled>` | A gitignored lockfile fails even when present locally |
| runtime_version_pinned | `global.json` (the ecosystem SDK selector that pins), `.tool-versions`, or `mise.toml`; or an immutable image reference (digest or exact tag such as `mcr.microsoft.com/dotnet/sdk:8.0.404`) | `<TargetFramework>` is a compatibility declaration and does **not** pin |
| module_boundaries_enforced | A solution-level layering test, or `NetArchTest` | Documentation alone never passes this signal |
| dead_code_detection | Analyzer rules IDE0051/CS0169 at warning or above | |
| duplicate_code_detection | PMD CPD or an equivalent copy-paste detector wired into a command | A committed `.codeclimate.yml`/`sonar-project.properties` with duplication rules on also passes (universal clause) |
| file_size_or_complexity_guard | An analyzer or `.editorconfig` complexity rule | |
| naming_conventions_stated | Automated: `.editorconfig` `dotnet_naming_rule.*` entries with a severity | Otherwise the documentation clause in `../signals.md` (3 of 4 categories) decides it |

## Supplementary detail for universal signals

| signal_id | Per-stack detail |
|---|---|
| env_vars_documented | Env-access API: `Environment.GetEnvironmentVariable` |
| service_dependencies_documented | Driver extractor (.NET row): `appsettings*.json` `ConnectionStrings.*` |
| tech_debt_markers_tracked | No first-party marker lint rule at the required strength; use a committed scanner script or CI step |
