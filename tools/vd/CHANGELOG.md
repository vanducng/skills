# Changelog

All notable changes to the `vd` CLI will be documented here.
Repo-root `CHANGELOG.md` covers skill-bundle versioning.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow [SemVer](https://semver.org/).

## [1.1.0](https://github.com/vanducng/skills/compare/v1.0.0...v1.1.0) (2026-05-05)


### Features

* **vd:** passive upstream version check with one-line stderr nudge ([db883de](https://github.com/vanducng/skills/commit/db883deaa589c2def5494fdf7a5ac9bf377fb2e5))
* **vd:** support VD_ROOT env var for repo root resolution ([8308e06](https://github.com/vanducng/skills/commit/8308e069f3739d423dfc6bdccd08d4aadc13bef1))


### Bug Fixes

* **ci:** skip github-release in release-please; document manual tag step ([05d3e87](https://github.com/vanducng/skills/commit/05d3e8703cfc12650dd5e4f5a4bd36a8fc34c61f))

## 1.0.0 (2026-05-05)


### Features

* **vd:** add CLI for vendoring + syncing skills ([#10](https://github.com/vanducng/skills/issues/10)) ([800da42](https://github.com/vanducng/skills/commit/800da420f110381ef310fdea72794ce5ce0423e2))

## [Unreleased]

### Added
- `VD_ROOT` env var as a repo-root source (between the `--root` flag and the `.git` walk-up). Both override sources validate that the path exists and is a directory; invalid values fail fast.
- Passive upstream version check on every command — prints a one-line stderr nudge when a newer release is available. Cached 24h under `$XDG_CACHE_HOME/vd/version-check.json`. Gated by `VD_NO_UPDATE_CHECK`, `CI`, `--quiet`, `dev` builds, and non-TTY stderr. No telemetry, no opt-in, fully offline-safe.
- Initial CLI: `init`, `add`, `list`, `sync`, `update`, `diff`, `doctor`, `pin`, `detach`, `remove`, `build`, `cache clean`.
- Bundle and per-skill emitter modes for `marketplace.json` and `plugin.json`.
- `.agents/` symlink emitter (relative symlinks; Windows falls back to directory copy).
- `skills.toml` manifest schema (version 1) with `[meta]`, `[sources.*]`, `[skills.*]`, `[targets.claude]`, `[targets.claude.bundle]`, `[plugin.*]` blocks.
- `skills.lock` for reproducible installs (SHA + TreeHash per skill).
- Dirty-check ("refuse-on-dirty"): `vd sync` refuses to overwrite locally modified skills without `--force`.
- Bundle emitter seeds defaults from live `marketplace.json` so first-run output is byte-equal to the existing file.
- GoReleaser monorepo distribution with tag pattern `v*`.
- GitHub Actions path-filtered CI: `vd-test.yml` (test + lint on `tools/vd/**` changes), `vd-release.yml` (GoReleaser on `v*` tags), `vd-release-please.yml` (automated release PR).
- Dogfood: `browserbase/skills/browser` and `browserbase/skills/browser-trace` onboarded via `vd add` + `vd sync` with zero diff on `.claude-plugin/`.
