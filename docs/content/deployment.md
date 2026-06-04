---
title: "Deployment"
---

## GitHub Pages

The public documentation site deploys to:

```text
https://skills.vanducng.dev/
```

`.github/workflows/pages.yml` builds on pushes to `main` when anything under `docs/` (or the Pages workflow) changes. Pull requests run the same Astro build without deploying.

Deployment steps:

1. Checkout the repo.
2. Build with `withastro/action@v6` (`path: ./docs`) — installs deps and runs `astro build`.
3. Upload `docs/dist/` as the Pages artifact (the custom domain comes from `docs/public/CNAME`).
4. Deploy with `actions/deploy-pages@v5`.

Source: `.github/workflows/pages.yml`, `docs/astro.config.mjs`.

## Agent-Facing Files

The site serves these static files from `docs/public/` (plus an Astro-generated sitemap):

```text
/llms.txt
/llms-full.txt
/llm.txt
/robots.txt
/sitemap-index.xml
```

`/llms.txt` is the canonical curated index. `/llms-full.txt` is a larger single-file context. `/llm.txt` exists only as a compatibility pointer for the singular spelling.

## Skill Catalog Validation

`.github/workflows/validate.yml` runs on push and pull request:

```sh
bash scripts/validate.sh
bash scripts/check-release-versions.sh
```

This catches malformed skill frontmatter and SemVer drift before merge.

## Skill Catalog Release

`.github/workflows/release.yml` runs Release Please on `main`. Conventional Commits determine the next SemVer bump:

| Commit type | Bump |
| --- | --- |
| `fix:` | Patch |
| `feat:` | Minor |
| Breaking change | Major |

Release Please updates `CHANGELOG.md`, `version.txt`, `skills.toml`, `.claude-plugin/plugin.json`, and `.claude-plugin/marketplace.json`.

## Rollback

For docs, revert the bad docs commit and let the Pages workflow redeploy. For skill-catalog releases, create a follow-up fix commit and let Release Please issue the next patch.

:::caution
Avoid force-pushing `main`. Release state is derived from GitHub releases, tags, and changelog history.
:::
