---
title: "Tech Stack"
---

## Documentation

| Layer | Tool | Version / source |
| --- | --- | --- |
| Static site generator | Astro Starlight | `astro@6` + `@astrojs/starlight@0.39` pinned in `docs/package.json`; CI builds via `withastro/action`. |
| Source format | Markdown / MDX | `docs/content/*.{md,mdx}`, `skills/*/SKILL.md`, `README.md`. |
| Agent text entry points | Plain text (served static) | `docs/public/llms.txt`, `llms-full.txt`, `llm.txt`, `robots.txt`. |
| Configuration | JS / TS | `docs/astro.config.mjs`, `docs/src/content.config.ts`; `skills.toml` (catalog). |
| Styling | CSS | `docs/src/styles/theme.css` (teal accent via Starlight `customCss`). |

## Skill Catalog

| Layer | Tool | Source |
| --- | --- | --- |
| Skill package format | Markdown frontmatter plus instructions | `skills/*/SKILL.md` |
| Local validation | Bash plus Python standard library | `scripts/validate.sh`, `scripts/check-release-versions.sh` |
| Claude Code target | Plugin and marketplace JSON | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` |
| Codex target | `.agents/skills` symlinks | `vd install codex --dry-run` |
| Factory Droid target | `.factory/skills` entries | `vd install droid --dry-run` |

## CLI Integration

The standalone `vd` CLI is maintained in `vanducng/vd-cli`, not in this repo. Install its latest release before using the target commands documented here; Factory Droid requires v3.13.0 or newer.

`vd-cli` is a Go module using:

| Dependency | Version |
| --- | --- |
| Go module path | `github.com/vanducng/vd-cli/v2` |
| Go directive | `1.23` |
| Cobra | `v1.10.2` |
| go-toml | `v2.3.1` |
| yaml.v3 | `v3.0.1` |

Source: [`vanducng/vd-cli/go.mod`](https://github.com/vanducng/vd-cli/blob/main/go.mod).

## CI And Release

| Workflow | Purpose |
| --- | --- |
| `.github/workflows/validate.yml` | Skill frontmatter and release-version consistency. |
| `.github/workflows/release.yml` | Release Please for skill-catalog SemVer. |
| `.github/workflows/pages.yml` | Astro Starlight build and GitHub Pages deployment. |
