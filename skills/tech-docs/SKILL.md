---
name: tech-docs
description: "Create, modernize, validate, and ship a public technical documentation site for any CLI, library, service, or developer tool using Astro Starlight. Use when the user asks to build a docs website, add Starlight, reproduce the shared centered docs style, organize technical docs navigation, migrate an existing docs site, fix responsive docs layout, or verify and deploy developer documentation."
license: MIT
---

# Tech Docs

Build a public developer documentation site from repository evidence. Keep the site self-contained, readable, responsive, and reproducible.

This skill owns the rendered docs website. Use `vd:docs` for canonical internal Markdown, architecture records, and README accuracy when no public site is requested.

## Modes

| Mode | Use |
| --- | --- |
| `init` | Add a new Starlight site without replacing an existing docs tree. |
| `update` | Refresh content, navigation, dependencies, or theme in an existing site. |
| `check` | Run build, content, link, layout, and deployment checks without writing. |

Infer the mode from the request. If `docs/` already contains a site, use `update`. If `docs/` contains unrelated internal Markdown, do not overwrite it. Ask where the rendered site should live.

## Profiles

| Profile | Choose when |
| --- | --- |
| `centered` | Reference-heavy CLI, library, service, or multi-repo docs need the shared centered navigation shell. |
| `native` | A product-style splash page or existing site should retain Starlight's native layout. |

Preserve an existing profile unless the user asks for a redesign. For a new reference-heavy site, default to `centered` and copy `assets/theme.css` into the site's styles directory.

## Workflow

### 1. Inspect before writing

1. Read repository guidance and current working-tree state.
2. Inspect the README, package manifest or module file, lockfile, CLI help, deployment workflows, and existing docs.
3. Identify the audience, supported install paths, real commands, configuration sources, release process, hosting target, and canonical domain.
4. Search for stale product names, old domains, legacy tools, and duplicated navigation labels.
5. Preserve unrelated changes. Use an isolated worktree when the active checkout is dirty.

Do not infer a command, option, environment variable, or architecture claim from memory when the repository can prove it.

### 2. Choose the smallest site shape

For a fresh site, use the official Starlight scaffold and keep it under one project directory such as `docs/`. Commit its lockfile. Prefer Starlight's standard `src/content/docs/` layout.

For an existing site, preserve its working content collection. Do not migrate between `src/content/docs/` and a custom loader solely for consistency.

Read `references/blueprint.md` when initializing a site, configuring GitHub Pages, selecting navigation, or applying the centered profile.

Add integrations only when required:

- Add MDX or React only for real interactive content.
- Add an `llms.txt` plugin only for agent-facing projects that benefit from it.
- Use explicit sidebar items for a small curated set and autogeneration for a large reference tree.
- Keep the site static unless the project requires server rendering.

### 3. Write evidence-backed content

Start with the smallest useful information architecture:

1. Overview
2. Install and quick start
3. Core concepts
4. Task guides
5. Reference
6. Troubleshooting
7. Project development and deployment, when public

Delete empty sections. Every page needs `title` frontmatter. Prefer runnable commands, expected output, and recovery steps over prose. Keep secrets, internal hosts, customer data, and private identifiers out of public docs.

When a stack or product name changes, update all visible surfaces in the same pass: README, overview copy, navigation, cards, quick reference, troubleshooting, related links, metadata, and generated indexes.

### 4. Apply the visual contract

For `centered`, copy `assets/theme.css` to the site and register it with Starlight's `customCss`. Brand through CSS variables and repository-owned logo assets, not by editing the shared geometry rules.

The centered profile must keep these relationships at desktop widths:

- Search center equals article center within 1 px.
- Search dialog controls keep their native size; the clear button is at most 3.5rem wide.
- The separator starts and ends with the article column within 1 px.
- Article-to-sidebar gap is at least 24 px.
- Logo/title moves with the sidebar shell and keeps its native inner inset.
- `document.documentElement.scrollWidth <= window.innerWidth`.

The theme targets Starlight shell markup. Re-run browser geometry checks after every Starlight upgrade.

### 5. Validate at the real boundary

Run from the site directory:

```bash
npm ci
npm run build
```

Then verify:

1. Every authored page has valid frontmatter and all internal links resolve.
2. Public metadata, canonical URLs, CNAME, sidebar links, and repository links are current.
3. No stale product name or domain remains in tracked source or built output.
4. The site works at 2048, 1584, 1440, 1272, 900, and 390 px without overflow.
5. The centered profile passes the geometry contract above at desktop widths.
6. Wide and mobile screenshots look intentional, not merely technically valid.

Use `vd:ego-browser` when available for rendered DOM measurements and screenshots. Otherwise use the repository's existing browser test stack. Do not accept build success as layout proof.

### 6. Ship only to the authorized endpoint

For GitHub Pages, prefer the official Astro Pages action from `references/blueprint.md`. A pull request should build but not deploy. A push to the release branch may deploy.

Before merge, refresh the current head, checks, approvals, and unresolved review threads. After merge, wait for the latest docs deployment and verify the live URL with a cache-busting query. If a release workflow creates another main commit, confirm the deployed docs tree still matches current main.

Do not configure DNS, change Pages settings, merge, or deploy unless the user authorized that endpoint.

## Hard rules

1. Never overwrite a populated non-site `docs/` directory.
2. Never copy another project's name, domain, logo, analytics ID, or repository URL into a reusable site.
3. Never replace working content architecture just to match a template.
4. Never publish unverified commands or configuration.
5. Never declare success from a local build alone when live deployment was requested.
