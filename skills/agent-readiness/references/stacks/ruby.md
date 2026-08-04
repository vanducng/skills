# Stack: Ruby

Evidence only. Scope, skippability, skip conditions, floor rules, and the `Fix:` classification for every
signal below live in `../signals.md`; this file says what counts as evidence in this ecosystem. Each row is
additive to that signal's catch-all clause - a stack row never overrides the catch-all, and a signal passes
for the app when any one clause (this file's or the catch-all's) holds.

## Detection

| Field | Value |
|---|---|
| Detect by | `Gemfile` |
| Manifests / lockfiles | `Gemfile`, `Gemfile.lock` |
| First-party sources | `.rb`, `.rake`, `.erb` |
| Notes | RuboCop covers lint, formatting, complexity, and naming, so the same gem appears in several rows - each row still needs its own cop family enabled plus a declared run command. |

## Stack-heavy signals (all 13, one row each)

| signal_id | Evidence (PASS if any one) | Notes |
|---|---|---|
| test_command_declared | `rspec`/`minitest` in the `Gemfile` plus `spec/` or `test/` | |
| test_command_runnable | `rspec --dry-run`, or a rake test task listed via `rake -T` and resolving | Collection or dry-run only, never the full suite |
| lint_configured | `.rubocop.yml` plus rubocop in the `Gemfile` | Config without the gem does not pass |
| format_check_available | rubocop in the `Gemfile` with `Layout` cops enabled and a declared run command, or `standardrb` | Both halves required: resolved formatter and a non-mutating check command |
| static_analysis_configured | sorbet (`sorbet/config`) plus `srb tc`, or RBS signatures plus a declared `steep check` command | An RBS directory on its own runs nothing and fails |
| coverage_threshold_enforced | `SimpleCov.minimum_coverage N` | Subject to the floor rule in `../signals.md`: a committed `0`, or any value at or below 1 percent, fails |
| dependencies_locked | `Gemfile.lock` committed | A gitignored lockfile fails even when present locally |
| runtime_version_pinned | `.ruby-version`, `.tool-versions`, or `mise.toml`; or an immutable image reference (digest or exact tag such as `ruby:3.3.6-slim`) | A `ruby` directive in the `Gemfile` is a compatibility declaration and does **not** pin |
| module_boundaries_enforced | packwerk | Documentation alone never passes this signal |
| dead_code_detection | `debride`, or rubocop `Lint/UselessAssignment` plus a documented unused-code pass | |
| duplicate_code_detection | A committed duplicate-detection config a command or CI step invokes (`flay`, a CPD run) | A committed `.codeclimate.yml`/`sonar-project.properties` with duplication rules on also passes (universal clause) |
| file_size_or_complexity_guard | rubocop `Metrics/*` cops left enabled | Disabling the whole `Metrics` department fails the signal |
| naming_conventions_stated | Automated: rubocop `Naming/*` cops | Otherwise the documentation clause in `../signals.md` (3 of 4 categories) decides it |

## Supplementary detail for universal signals

| signal_id | Per-stack detail |
|---|---|
| env_vars_documented | Env-access API: `ENV['X']` |
| service_dependencies_documented | Driver extractor (Rails row): `config/database.yml` `*.adapter`, `config/cable.yml` `*.adapter`, `config/storage.yml` `*.service`, `config/environments/*.rb` `cache_store` and `active_job.queue_adapter` |
| tech_debt_markers_tracked | RuboCop `Style/CommentAnnotation` checks annotation *formatting* only and does **not** pass an owner-or-link policy on its own; use a dedicated scanner for the link policy |
