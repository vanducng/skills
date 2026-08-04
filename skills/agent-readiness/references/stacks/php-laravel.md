# Stack: PHP / Laravel

Evidence only. Scope, skippability, skip conditions, floor rules, and the `Fix:` classification for every
signal below live in `../signals.md`; this file says what counts as evidence in this ecosystem. Each row is
additive to that signal's catch-all clause - a stack row never overrides the catch-all, and a signal passes
for the app when any one clause (this file's or the catch-all's) holds.

## Detection

| Field | Value |
|---|---|
| Detect by | `composer.json` |
| Manifests / lockfiles | `composer.json`, `composer.lock` |
| First-party sources | `.php` |
| Notes | A Laravel app very often detects TS/JS as well. When both are code-bearing the multi-stack ALL rule applies: a `pint.json` alone scores `lint_configured` 0 for that app because the TS half has no lint feedback loop. |

## Stack-heavy signals (all 13, one row each)

| signal_id | Evidence (PASS if any one) | Notes |
|---|---|---|
| test_command_declared | `composer.json` has a `test` script, or `phpunit.xml`/`tests/Pest.php` exists with tests present | `tests/Pest.php` is **case-sensitive** and lives under `tests/`; there is no root `pest.php` |
| test_command_runnable | Pest: `vendor/bin/pest --list-tests`. PHPUnit: `vendor/bin/phpunit --list-tests` | Collection-only, never the full suite. Note the hyphenated `--list-tests` here; `--listTests` is Jest-only |
| lint_configured | `pint.json`, or Pint in `composer.json` require-dev, or `phpcs.xml` | |
| format_check_available | Pint in require-dev plus a declared `pint --test` command | Both halves required. A default Pint install with no check command fails, because plain `pint` rewrites files |
| static_analysis_configured | `phpstan.neon`/`phpstan.neon.dist` (or Larastan) with a declared level and phpstan in require-dev | |
| coverage_threshold_enforced | `--min` on Pest coverage, or a phpunit coverage check in CI | Subject to the floor rule in `../signals.md`: a committed `0`, or any value at or below 1 percent, fails |
| dependencies_locked | `composer.lock` committed | A gitignored lockfile fails even when present locally |
| runtime_version_pinned | `.tool-versions` or `mise.toml`; or an immutable image reference (digest or exact tag such as `php:8.3.14-fpm-alpine`) | Composer `require.php` is a compatibility declaration. Composer `config.platform` only **emulates** a platform during resolution and does not choose the PHP that runs. Neither pins |
| module_boundaries_enforced | deptrac, or an architecture test (Pest `arch()`) asserting a layering rule | Documentation alone never passes this signal |
| dead_code_detection | `composer-unused`, `phpstan` deadCode rules, or a documented unused-code pass | |
| duplicate_code_detection | `phpcpd`, PMD CPD, or an equivalent copy-paste detector wired into a command | A committed `.codeclimate.yml`/`sonar-project.properties` with duplication rules on also passes (universal clause) |
| file_size_or_complexity_guard | phpstan/phpmd complexity rules, or a documented size budget checked in CI | |
| naming_conventions_stated | Automated: phpstan/Pint naming rules | Otherwise the documentation clause in `../signals.md` (3 of 4 categories) decides it |

## Supplementary detail for universal signals

| signal_id | Per-stack detail |
|---|---|
| env_vars_documented | Env-access API: `env('X')`, `getenv('X')`. A `config/*.php` file reading those keys satisfies the typed-config clause |
| service_dependencies_documented | Driver extractor (Laravel row): `config/database.php` `connections.*.driver` and `redis.*` client, `config/queue.php` `connections.*.driver`, `config/cache.php` `stores.*.driver`, `config/mail.php` `mailers.*.transport`, `config/filesystems.php` `disks.*.driver`, `config/session.php` `driver` |
| tech_debt_markers_tracked | No first-party marker lint rule at the required strength; use a committed scanner script or CI step |
