---
title: "Workflows"
---

The repo is intentionally file-based. Commands are short, checks are local, and generated agent surfaces are committed only when they are part of the catalog release.

## Local Validation

```sh
bash scripts/validate.sh
bash scripts/check-release-versions.sh
vd doctor
```

`scripts/validate.sh` checks every `skills/*/SKILL.md` frontmatter block and rejects runtime-prefixed skill IDs in the root docs it validates. `scripts/check-release-versions.sh` checks SemVer consistency across the skill-catalog release surfaces.

Source: `scripts/validate.sh`, `scripts/check-release-versions.sh`.

## Build Agent Surfaces

```sh
vd build
```

`vd build` reads `skills.toml` and emits Claude Code plugin metadata plus Codex repo-scope skill links. The `vd` CLI itself lives in `vanducng/vd-cli` and versions independently from this skill catalog.

Source: `skills.toml`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`.

## Publish Docs

```sh
cd docs
npm install
npm run build      # astro build -> docs/dist/
```

The Pages workflow builds `docs/` with `withastro/action` and deploys `docs/dist/` to GitHub Pages; the custom domain comes from `docs/public/CNAME`. Agent-facing files are served from `docs/public/` (`/llms.txt`, `/llms-full.txt`, `/llm.txt`, `/robots.txt`).

Source: `docs/astro.config.mjs`, `.github/workflows/pages.yml`.

## Release The Skill Catalog

Release Please opens a release PR after Conventional Commits land on `main`. The release PR updates:

```text
CHANGELOG.md
version.txt
skills.toml
.claude-plugin/plugin.json
.claude-plugin/marketplace.json
```

Merging that release PR creates the GitHub release for the skill catalog.

Source: `.github/workflows/release.yml`, `.release-please-config.json`, `.release-please-manifest.json`.
