# Stack: TypeScript / JavaScript

Evidence only. Scope, skippability, skip conditions, floor rules, and the `Fix:` classification for every
signal below live in `../signals.md`; this file says what counts as evidence in this ecosystem. Each row is
additive to that signal's catch-all clause - a stack row never overrides the catch-all, and a signal passes
for the app when any one clause (this file's or the catch-all's) holds.

## Detection

| Field | Value |
|---|---|
| Detect by | `package.json` |
| Manifests / lockfiles | `package.json`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `bun.lock` (or legacy `bun.lockb`) |
| First-party sources | `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.vue`, `.svelte` |
| Notes | A `package.json` that only runs a build tool, with no `.ts`/`.js` source of its own, is **not** code-bearing and does not participate in the multi-stack ALL rule. |

## Stack-heavy signals (all 13, one row each)

| signal_id | Evidence (PASS if any one) | Notes |
|---|---|---|
| test_command_declared | `package.json` has a `test` script that is not a placeholder | `echo "no test specified" && exit 1` fails |
| test_command_runnable | Jest: `npx jest --listTests`. Vitest: `npx vitest list` | `--listTests` is **Jest-only**; `npm test` does not accept it generically. Pick the invocation for the runner the manifest actually declares |
| lint_configured | `eslint.config.*`, `.eslintrc*`, or `biome.json` with rules, plus eslint/biome in devDependencies | Config without the dependency does not pass |
| format_check_available | prettier or biome in devDependencies plus a `format:check`-style script running `prettier --check` or `biome check` | Both halves required: resolved formatter and a non-mutating check command |
| static_analysis_configured | TS: `tsconfig.json` with `"strict": true` (or all strict flags individually), plus a `typecheck`/`tsc --noEmit` command. JS-only: JSDoc-based `checkJs` with a typecheck command, or a documented decision to skip typing plus a runtime schema validator at the boundaries | A type-stub directory is data, not an analysis run |
| coverage_threshold_enforced | `coverageThreshold` in jest config, or vitest `coverage.thresholds` | Subject to the floor rule in `../signals.md`: a committed `0`, or any value at or below 1 percent, fails |
| dependencies_locked | `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `bun.lock`, or legacy `bun.lockb` committed | Both `bun.lock` (modern) and `bun.lockb` (legacy) are accepted. A gitignored lockfile fails even when present locally |
| runtime_version_pinned | `.nvmrc`, `.node-version`, `.tool-versions`, or `mise.toml`; or an immutable image reference (digest or exact tag such as `node:22.11.0-alpine`) | `engines.node` is a compatibility declaration, documented as advisory, and does **not** pin |
| module_boundaries_enforced | eslint `import/no-restricted-paths`, `no-restricted-imports` zones, `boundaries/*`, or a `dependency-cruiser` rule invoked by a command or CI step | Documentation alone never passes this signal |
| dead_code_detection | `knip.json`, `ts-prune`, or `unimported` wired into a command or CI step | |
| duplicate_code_detection | `jscpd` config, `.jscpd.json`, or a `similarity-ts` step invoked by a command or CI step | A committed `.codeclimate.yml`/`sonar-project.properties` with duplication rules on also passes (universal clause) |
| file_size_or_complexity_guard | eslint `max-lines`, `max-lines-per-function`, or `complexity` | A `warn` severity is not advisory under `--max-warnings=0` |
| naming_conventions_stated | Automated: eslint `@typescript-eslint/naming-convention` | Otherwise the documentation clause in `../signals.md` (3 of 4 categories) decides it |

## Supplementary detail for universal signals

| signal_id | Per-stack detail |
|---|---|
| env_vars_documented | Env-access API: `process.env.X`, `import.meta.env.X`. A zod env schema satisfies the typed-config clause |
| service_dependencies_documented | Driver extractor (Node row): a committed ORM/client config - `prisma/schema.prisma` `datasource.provider`, `knexfile.*` `client`, `ormconfig`/`data-source.ts` `type` |
| tech_debt_markers_tracked | eslint `no-warning-comments` has only `terms`/`location`/`decoration`; it flags terms and **cannot** require an owner or an issue link. A link policy needs a dedicated scanner |
