---
name: zensical
description: "Create, migrate, style, build, and publish Zensical documentation sites, including zensical.toml, docs navigation, custom CSS, GitHub Pages workflows, CNAME domains, and local preview/build validation."
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
---

# Zensical

Use this skill when the user asks for Zensical docs, a Zensical migration, a public docs site, GitHub Pages docs deployment, or a polished docs design built on Markdown.

## Workflow

1. Scout the repo docs state: `find docs -maxdepth 3 -type f`, `rg "zensical|mkdocs|pages|CNAME|site_url"`.
2. Check local tooling: `zensical --version`, `zensical build --help`, and existing `zensical.toml` if present.
3. Create or update `zensical.toml` with:
   - `[project].site_name`
   - `[project].site_url` for public sites
   - `docs_dir = "docs"`
   - `site_dir = "site"`
   - explicit `[[project.nav]]` sections for durable docs
   - `extra_css` when visual polish is requested
4. Keep docs structured for users: install, quick start, architecture, tech stack, development, deployment.
5. For GitHub Pages, build `site/`, write `site/CNAME` when a custom domain exists, upload `site` with `actions/upload-pages-artifact`, and deploy with `actions/deploy-pages`.
6. For agent-friendly docs, publish `/llms.txt` as the canonical curated index. Add `/llms-full.txt` when a single larger context file is useful, and add `/llm.txt` only as a compatibility pointer if requested.
7. Validate locally with `zensical build --clean --strict`.

## Design Rules

- Make the first page identify the product or repo immediately.
- Prefer compact docs navigation over marketing sections.
- Use custom CSS only for durable layout, cards, callouts, and brand accents.
- Keep CSS responsive with fixed breakpoints and stable dimensions.
- Include a real useful visual when it clarifies architecture or workflow.

## Guardrails

- Remove stale generated docs and obsolete workflows that point at deleted sources.
- Do not claim release assets exist until checked against the current release.
- Do not put personal journals or one-off reports under the public docs tree.
- Treat `/llms.txt` as an emerging convention, not a guaranteed crawler contract.
- Keep canonical skill IDs prefix-free in repo docs, for example `vd:docs`.
