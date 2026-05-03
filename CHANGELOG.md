# Changelog

All notable changes to this repo are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow [SemVer](https://semver.org/).

## [0.2.0] - 2026-05-03

### Changed
- **Restructured as a Claude Code plugin (`vd`).** Skills now install via `/plugin install vd@vanducng-skills` and appear in the catalog as `vd:<skill>` (e.g. `vd:research`, `vd:computer-clean`).
- `marketplace.json` now registers a single plugin `vd` pointing to this repo as source.
- README rewritten around the plugin install flow; symlink `install.sh` retained as a dev-only fallback (skills installed that way appear without the `vd:` prefix).

### Added
- `.claude-plugin/plugin.json` — plugin manifest for `vd`.
- `skills/research/` (skill v2.0.0) — technical research skill, rewritten from `ck:research`:
  - WebSearch only (Gemini path removed).
  - **`--deep` flag** for high-stakes decisions: query budget 5 → 12, expanded report with failure-modes table, migration paths, operational war stories, performance-under-realistic-load, decision reversibility.
  - Multi-option evaluation is mandatory — single-option reports flagged as failure.
  - Comparison matrix non-optional in any mode.
  - Reports save to CWD as `research-{slug}-{YYYYMMDD}.md`.
  - YAGNI/KISS/DRY explicitly overridden in favor of depth, brutal honesty, and answering the user's actual demand.

### Removed
- `skills/hello-world/` — smoke-test skill, no longer needed now that the plugin install path is verified.

## [0.1.0] - 2026-05-03

### Added
- Initial repo scaffold.
- `scripts/install.sh` — per-skill symlink installer (idempotent, conflict-safe).
- `scripts/uninstall.sh` — removes only repo-owned symlinks.
- `scripts/new-skill.sh` — scaffolder for new skills.
- `scripts/validate.sh` — frontmatter linter.
- `.claude-plugin/marketplace.json` — marketplace stub.
- `skills/hello-world/` — smoke-test skill.
- CI: `.github/workflows/validate.yml`.
