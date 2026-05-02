# Changelog

All notable changes to this repo are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow [SemVer](https://semver.org/).

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
