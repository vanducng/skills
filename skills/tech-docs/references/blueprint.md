# Starlight site blueprint

Use this reference for `init`, Pages configuration, navigation design, and the centered profile. Replace every angle-bracket placeholder from repository evidence.

## Site layout

Prefer the official content layout for a new site:

```text
docs/
├── astro.config.mjs
├── package.json
├── package-lock.json
├── public/
│   └── CNAME
└── src/
    ├── assets/
    │   └── logo.svg
    ├── content/
    │   └── docs/
    │       ├── index.md
    │       ├── start-here/
    │       ├── concepts/
    │       ├── guides/
    │       ├── reference/
    │       └── troubleshooting.md
    └── styles/
        └── theme.css
```

An existing custom content loader is valid. Preserve it if builds and routing already work.

## Fresh setup

Start from the current official scaffold rather than copying old dependency versions:

```bash
npm create astro@latest -- --template starlight
```

Move the generated site under the repository's chosen site root when needed, then commit its lockfile. Use the repository's existing package manager if it has one clear standard.

## Minimal Starlight configuration

```js
import { defineConfig } from 'astro/config'
import starlight from '@astrojs/starlight'

export default defineConfig({
  site: '<canonical-site-url>',
  integrations: [
    starlight({
      title: '<project-title>',
      description: '<one-sentence-description>',
      logo: { src: './src/assets/logo.svg' },
      customCss: ['./src/styles/theme.css'],
      social: [
        {
          icon: 'github',
          label: 'GitHub',
          href: 'https://github.com/<org>/<repo>',
        },
      ],
      sidebar: [
        { label: 'Overview', slug: '' },
        {
          label: 'Start here',
          items: [
            { label: 'Install', slug: 'start-here/install' },
            { label: 'Quick start', slug: 'start-here/quick-start' },
          ],
        },
        {
          label: 'Guides',
          items: [{ autogenerate: { directory: 'guides' } }],
        },
        {
          label: 'Reference',
          items: [{ autogenerate: { directory: 'reference' } }],
        },
        { label: 'Troubleshooting', slug: 'troubleshooting' },
      ],
    }),
  ],
})
```

Omit `base` for a custom domain or root user site. For project Pages at `https://<user>.github.io/<repo>/`, set `site` to the origin and `base` to `/<repo>`.

## Profile setup

For a new `centered` site, copy the bundled asset to the target site:

```bash
cp "<skill-root>/assets/theme.css" "<repo-root>/docs/src/styles/theme.css"
```

Register it in `customCss`. If the site already has a theme, merge the accent and surface variables instead of overwriting project styling. Do not edit the geometry block unless browser measurements prove the target site needs a different contract.

For `native`, use Starlight defaults or keep the site's existing custom CSS. A splash landing page can use:

```yaml
---
title: <project-title>
description: <one-sentence-description>
template: splash
hero:
  tagline: <specific-value-proposition>
  actions:
    - text: Install
      link: ./start-here/install/
      icon: right-arrow
    - text: Reference
      link: ./reference/
      variant: minimal
---
```

## Navigation choice

Use explicit entries when page order teaches a workflow or the site has fewer than roughly 20 stable pages. Use `autogenerate` for large command, API, or provider trees where file structure is the navigation source.

Do not create empty categories. A typical CLI or developer-tool site uses:

| Section | Evidence source |
| --- | --- |
| Overview | README, package metadata, executable help |
| Install | package registry, release artifacts, supported runtimes |
| Quick start | smallest verified success path |
| Concepts | architecture and stable mental models |
| Guides | real operator workflows and recovery paths |
| Reference | command help, schemas, configuration loaders |
| Troubleshooting | tests, known failures, operational docs |
| Project | public architecture, development, release, deployment |

## GitHub Pages workflow

Use the official Astro action for a site rooted at `docs/`:

```yaml
name: GitHub Pages

on:
  push:
    branches: [main]
    paths:
      - "docs/**"
      - ".github/workflows/docs.yml"
  pull_request:
    paths:
      - "docs/**"
      - ".github/workflows/docs.yml"
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: github-pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v7
      - name: Build with Astro
        uses: withastro/action@v6
        with:
          path: ./docs

  deploy:
    if: github.event_name != 'pull_request'
    needs: build
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v5
```

Set GitHub Pages source to GitHub Actions. For a custom domain, store only the hostname in `docs/public/CNAME` and configure DNS separately with explicit authorization.

## Centered profile measurement

Measure the article container, not the first `.sl-container`, which may belong to the table of contents:

```js
const rect = (element) => element.getBoundingClientRect()
const article = rect(
  document.querySelector('.main-pane main > .content-panel .sl-container'),
)
const sidebar = rect(document.querySelector('.sidebar-pane'))
const search = rect(document.querySelector('site-search button'))
const panel = document.querySelector(
  '.main-pane main > .content-panel + .content-panel',
)
const panelRect = rect(panel)
const separator = getComputedStyle(panel, '::before')
const separatorX =
  panelRect.x + parseFloat(separator.insetInlineStart || separator.left)
const separatorWidth = parseFloat(separator.inlineSize || separator.width)

console.assert(Math.abs(search.x + search.width / 2 - (article.x + article.width / 2)) <= 1)
console.assert(Math.abs(separatorX - article.x) <= 1)
console.assert(Math.abs(separatorWidth - article.width) <= 1)
console.assert(article.x - sidebar.right >= 24)
console.assert(document.documentElement.scrollWidth <= window.innerWidth)
```

Run these assertions at 2048, 1584, 1440, and 1272 px. At 900 and 390 px, verify no horizontal overflow and inspect navigation plus content visually.

## Review checklist

- Site root is self-contained and does not mix tooling with application dependencies.
- Package and lockfile agree.
- Every content page has `title` frontmatter.
- Sidebar slugs and links resolve.
- Install commands match current published artifacts.
- Examples run against the current CLI or API.
- Public docs contain no secrets, internal hosts, customer data, or copied project identifiers.
- Pull requests build without deploying.
- Main deploys and the live domain serves the current docs tree.
