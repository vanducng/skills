# Workflows

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
zensical build --clean --strict
```

The Pages workflow installs `zensical==0.0.43`, builds the site into `site/`, writes `site/CNAME` with `skills.vanducng.dev`, and deploys through GitHub Pages. Agent-facing files are published from `docs/llms.txt`, `docs/llms-full.txt`, `docs/llm.txt`, and `docs/robots.txt`.

Source: `zensical.toml`, `.github/workflows/pages.yml`.

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
