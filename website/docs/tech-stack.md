---
title: "Tech Stack"
---

## Documentation

| Layer | Tool | Version / source |
| --- | --- | --- |
| Static site generator | Zensical | Local `zensical --version` reports `0.0.43`; CI installs `zensical==0.0.43` in `.github/workflows/pages.yml`. |
| Source format | Markdown | `docs/*.md`, `skills/*/SKILL.md`, `README.md`. |
| Agent text entry points | Markdown/plain text | `docs/llms.txt`, `docs/llms-full.txt`, `docs/llm.txt`, `docs/robots.txt`. |
| Configuration | TOML | `zensical.toml`, `skills.toml`. |
| Styling | CSS | `docs/stylesheets/skills.css`, configured by `zensical.toml`. |

## Skill Catalog

| Layer | Tool | Source |
| --- | --- | --- |
| Skill package format | Markdown frontmatter plus instructions | `skills/*/SKILL.md` |
| Local validation | Bash plus Python standard library | `scripts/validate.sh`, `scripts/check-release-versions.sh` |
| Claude Code target | Plugin and marketplace JSON | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` |
| Codex target | `.agents/skills` symlinks | `vd install codex --dry-run` |

## CLI Integration

The standalone `vd` CLI is maintained in `vanducng/vd-cli`, not in this repo. Its current public release is `v2.1.0`, and the local installed binary reports `vd 2.1.0`.

`vd-cli` is a Go module using:

| Dependency | Version |
| --- | --- |
| Go module path | `github.com/vanducng/vd-cli/v2` |
| Go directive | `1.23` |
| Cobra | `v1.10.2` |
| go-toml | `v2.3.1` |
| yaml.v3 | `v3.0.1` |

Source: `/Users/vanducng/git/personal/agents/vd-cli/go.mod`.

## CI And Release

| Workflow | Purpose |
| --- | --- |
| `.github/workflows/validate.yml` | Skill frontmatter and release-version consistency. |
| `.github/workflows/release.yml` | Release Please for skill-catalog SemVer. |
| `.github/workflows/pages.yml` | Zensical build and GitHub Pages deployment. |
