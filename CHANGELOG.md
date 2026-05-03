# Changelog

All notable changes to this repo are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow [SemVer](https://semver.org/).

## [0.3.0] - 2026-05-04

### Added
- `skills/excalidraw/` (v1.0.0) — Excalidraw MCP diagram skill for technical diagrams:
  - Domain styling presets with hex palettes for **software architecture (C4 / microservices)**, **cloud architecture (AWS / GCP / Azure)**, **data pipelines / ETL / lakehouse**, **UML (sequence / ER / state / class)**, and **deployment (Kubernetes / Docker)**.
  - Sizing formulas (rectangle / diamond / ellipse) accounting for Excalidraw font width, arrow visibility rules (≥120px gap), two-batch ordering (shapes → arrows), and the mandatory write-check-review verification loop.
  - Quality checklist, anti-patterns table, MCP tool quick reference (32 tools), and edge-style conventions (batch / stream / async / lineage).
  - `references/styling-presets.md` — full color tables, layout templates (3-tier, event-driven, Lambda architecture, ELT lakehouse, microservice mesh, C4 skeleton), accessibility palette, implementation checklist.
  - `references/cheatsheet.md` — MCP vs REST format differences, element property reference, common recipes (arrow binding, translucent zones, cylinder approximation), verification loop.

## [0.2.0] - 2026-05-03

### Changed
- **Restructured as a Claude Code plugin (`vd`).** Skills now install via `/plugin install vd@vanducng-skills` and appear in the catalog as `vd:<skill>` (e.g. `vd:research`, `vd:computer-clean`).
- `marketplace.json` now registers a single plugin `vd` pointing to this repo as source.
- README rewritten around the plugin install flow; symlink `install.sh` retained as a dev-only fallback (skills installed that way appear without the `vd:` prefix).

### Added
- `.claude-plugin/plugin.json` — plugin manifest for `vd`.
- `skills/research/` (skill v2.0.0) — deep technical research skill:
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
