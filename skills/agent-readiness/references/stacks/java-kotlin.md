# Stack: Java / Kotlin

Evidence only. Scope, skippability, skip conditions, floor rules, and the `Fix:` classification for every
signal below live in `../signals.md`; this file says what counts as evidence in this ecosystem. Each row is
additive to that signal's catch-all clause - a stack row never overrides the catch-all, and a signal passes
for the app when any one clause (this file's or the catch-all's) holds.

## Detection

| Field | Value |
|---|---|
| Detect by | `pom.xml`, `build.gradle{,.kts}` |
| Manifests / lockfiles | `pom.xml`, `build.gradle{,.kts}`, plus `gradle.lockfile` |
| First-party sources | `.java`, `.kt`, `.kts` |
| Notes | Almost every check is a build-wired plugin here, so "wired into the build" means a goal, task, or `check` binding the build actually executes - not a dependency sitting unused in the manifest. |

## Stack-heavy signals (all 13, one row each)

| signal_id | Evidence (PASS if any one) | Notes |
|---|---|---|
| test_command_declared | surefire/junit dependency in `pom.xml`, or a `test` task in `build.gradle{,.kts}` | |
| test_command_runnable | Maven: `mvn -q -DskipTests test-compile`. Gradle: `gradle test --dry-run` | Compilation or dry-run only, never the full suite |
| lint_configured | checkstyle/spotbugs/detekt/ktlint config wired into the build | |
| format_check_available | spotless or ktlint wired into the build with a `check` goal/task | Both halves required: resolved formatter and a non-mutating check command. `spotlessApply` is mutating and does not pass |
| static_analysis_configured | errorprone, nullaway, or spotbugs wired into the build | |
| coverage_threshold_enforced | jacoco `check` rules with a `minimum` limit | Subject to the floor rule in `../signals.md`: a committed `0`, or any value at or below 1 percent, fails |
| dependencies_locked | `gradle.lockfile` committed, or fully pinned Maven versions with no ranges | `gradle/verification-metadata.xml` verifies checksums of whatever was resolved; it does **not** lock resolution and does not pass on its own |
| runtime_version_pinned | `.tool-versions`, `mise.toml`, or an SDKMAN `.sdkmanrc`; or an immutable image reference (digest or exact tag such as `eclipse-temurin:21.0.5_11-jdk`) | Gradle toolchain and Maven `maven.compiler.release` express a target level, not the JDK that runs, and do **not** pin |
| module_boundaries_enforced | ArchUnit tests, or the Java module system (`module-info.java`) | Documentation alone never passes this signal |
| dead_code_detection | spotbugs/detekt unused-code detectors enabled | |
| duplicate_code_detection | PMD CPD or an equivalent copy-paste detector wired into a command | A committed `.codeclimate.yml`/`sonar-project.properties` with duplication rules on also passes (universal clause) |
| file_size_or_complexity_guard | checkstyle `FileLength`/`CyclomaticComplexity`, or detekt `LongMethod` | |
| naming_conventions_stated | Automated: checkstyle naming rules, or detekt/ktlint naming rules | Otherwise the documentation clause in `../signals.md` (3 of 4 categories) decides it |

## Supplementary detail for universal signals

| signal_id | Per-stack detail |
|---|---|
| env_vars_documented | Env-access API: `System.getenv` |
| service_dependencies_documented | Driver extractor (Spring row): `application.{yml,yaml,properties}` `spring.datasource.*`, `spring.data.redis.*`, `spring.rabbitmq.*`, `spring.kafka.*`, `spring.mail.*` |
| tech_debt_markers_tracked | checkstyle `TodoComment` flags the terms only; an owner-or-link policy needs a dedicated scanner |
