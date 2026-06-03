---
title: "Deployment"
---

## GitHub Pages

The public documentation site deploys to:

```text
https://skills.vanducng.dev/
```

`.github/workflows/pages.yml` builds on pushes to `main` when docs, `zensical.toml`, `README.md`, or the Pages workflow changes. Pull requests run the same Zensical build without deploying.

Deployment steps:

1. Checkout the repo.
2. Install Python and `zensical==0.0.43`.
3. Run `zensical build --clean --strict`.
4. Write `site/CNAME` with `skills.vanducng.dev`.
5. Upload `site/` as the Pages artifact.
6. Deploy with `actions/deploy-pages`.

Source: `.github/workflows/pages.yml`, `zensical.toml`.

## Agent-Facing Files

The docs build publishes:

```text
/llms.txt
/llms-full.txt
/llm.txt
/robots.txt
/sitemap.xml
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

For docs, revert the bad docs commit and let the Pages workflow redeploy. For skill-catalog releases, create a follow-up fix commit and let Release Please issue the next patch. Avoid force-pushing `main`; release state is derived from GitHub releases, tags, and changelog history.
