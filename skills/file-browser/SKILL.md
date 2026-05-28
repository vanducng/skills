---
name: file-browser
description: "Local HTTP server that renders markdown, code, text, JSON, CSV/TSV/XLSX tables, HTML, PDF, images, video, and audio in the browser. Persistent left tree sidebar with vim keybindings (j/k/h/l/gg/G/Enter/o), filter (/), theme toggle (T), and folder open/collapse persistence per tab. Markdown dispatches to a novel-theme reader (Mermaid, plan nav, ToC scroll-spy); code/text dispatches to a highlight.js view with line numbers + copy button; CSV/TSV/XLSX dispatches to a tabular view; HTML renders in a sandboxed iframe; PDF dispatches to a custom minimal viewer built on the pdfjs-dist PDFViewer component (toolbar: prev/next, page input, zoom, search, download); images/video/audio get a gallery + single-view with Range-aware streaming. One server, one port, one CLI."
license: MIT
argument-hint: "[file-or-directory]"
metadata:
  author: vanducng
  version: "0.5.1"
---

# file-browser

One local HTTP server, one port, one CLI — handles markdown, images, video, and audio. Dispatches by file extension at the `/view` route: markdown goes to the novel-theme reader; image/video/audio go to the media viewer.

## Installation

```bash
cd $HOME/skills/skills/file-browser && npm install
```

**Dependencies:** `marked`, `highlight.js`, `gray-matter` (markdown), `pdfjs-dist` (PDF viewer), `read-excel-file` (XLSX tables). Media rendering is zero-dep — browser does the work.

`npm install` runs a `postinstall` hook that copies pdfjs-dist runtime deps (worker, cmaps, fonts, wasm helpers) from `node_modules/pdfjs-dist/` into `assets/pdfjs-viewer/`. If you ran `npm install --ignore-scripts`, populate the assets manually:

```bash
node $HOME/skills/skills/file-browser/scripts/install-pdfjs-assets.cjs
```

## Quick Start

```bash
# Single file (auto-detects markdown vs media)
node $HOME/skills/skills/file-browser/scripts/server.cjs --file ./plan.md --open
node $HOME/skills/skills/file-browser/scripts/server.cjs --file ./photo.png --open
node $HOME/skills/skills/file-browser/scripts/server.cjs --file ./demo.mp4 --open

# Folder (gallery + Documents section)
node $HOME/skills/skills/file-browser/scripts/server.cjs --dir ~/plans --open

# Background mode (returns JSON envelope on stdout)
node $HOME/skills/skills/file-browser/scripts/server.cjs --file ./README.md --background

# Stop all running file-browser servers
node $HOME/skills/skills/file-browser/scripts/server.cjs --stop
```

## CLI Options

| Option | Description | Default |
|---|---|---|
| `--file <path>` | Single file (markdown / image / video / audio) | - |
| `--dir <path>` | Folder gallery | - |
| `--port <n>` | Server port (auto-increments if busy) | 3556 |
| `--host <addr>` | Bind host (`0.0.0.0` for LAN) | localhost |
| `--open` / `--no-open` | Auto-open browser | open by default |
| `--background` | Detach as child, print JSON | false |
| `--foreground` | Stay foreground (Claude Code bg tasks) | false |
| `--stop` | Stop all file-browser servers | - |

## HTTP Routes

| Route | Description |
|---|---|
| `/view?file=<abs-path>` | **Dispatches by extension.** `.md/.markdown/.mdx` → novel-theme markdown reader (Mermaid, plan nav, ToC). `.csv/.tsv/.xlsx` → tabular data view. `.pdf` → custom PDF.js viewer iframe. Image/video/audio → media single-view with arrow-key prev/next. Append `?raw=1` to fall through to source view. |
| `/browse?dir=<abs-path>` | Gallery: folders, Documents (markdown + PDF + CSV/TSV/XLSX), Media (image/video/audio), Other files. |
| `/file/<abs-path>` | Raw byte streaming with HTTP `Range` support (required for video seeking and Safari audio). |
| `/api/tree?dir=<abs-path>` | Lazy directory listing (one level) for the sidebar tree. Returns JSON `{path, entries[]}` where each entry has `{name, path, kind: dir\|file, fileType?: markdown\|pdf\|table\|image\|video\|audio\|other}`. |
| `/assets/*` | Static assets (theme CSS, reader JS, sidebar JS). |
| `/assets/pdfjs-viewer/*` | Custom PDF viewer + pdfjs-dist runtime deps (populated by `postinstall`). |
| `/` | Welcome / route reference. |

## Supported Formats

**Documents:** `.md`, `.markdown`, `.mdx` (rendered with [marked](https://marked.js.org/) + `highlight.js` + Mermaid), `.csv`, `.tsv`, `.xlsx` (tabular data view; XLSX renders the first worksheet), `.pdf` (custom minimal viewer wrapping the pdfjs-dist `PDFViewer` component)
**Images:** PNG, JPEG, GIF, WebP, AVIF, SVG, BMP, ICO, HEIC/HEIF (Safari only), JPEG XL, APNG
**Video:** MP4, WebM, MOV, M4V, MKV*, OGV
**Audio:** MP3, M4A, AAC, OGG, Opus, WAV, FLAC

\* MKV codec support depends on browser. For codec-difficult video, fall back to IINA.

## Markdown Features (inherited from markdown-render)

- Novel-theme reader (warm cream / dark gold), Libre Baskerville headings, max 720px width
- Mermaid v11 diagrams, theme-aware light/dark, click to expand
- Plan navigation: detects `plan.md` + `phase-XX-*.md` siblings, builds accordion sidebar with status badges, prev/next buttons
- Cross-file links: relative `.md` links re-route through `/view`; relative non-md paths through `/file/`
- Keyboard shortcuts: `?` cheatsheet, `T` theme, `S` sidebar, `←`/`→` phase nav, `Esc` close
- Auto-hide header, progress bar, mobile FAB

## Media Features

- Gallery grid with lazy-loaded image thumbs, video first-frame previews, audio cards
- Single-view: arrow keys (`←` `→`) for prev/next sibling, `Esc` back to folder
- HTTP Range support — required for `<video>` scrubbing and Safari audio playback
- Mixed media in same folder, sorted alphabetically

## Sidebar Tree (gallery + single-view)

A persistent left sidebar shows the directory tree anchored at the launch folder (`--dir`) or the file's parent (`--file`). Lazy-loaded — only the root level loads up front; folders fetch their children on expand.

### Vim keybindings

| Key | Action |
| --- | --- |
| `j` / `k` | Move cursor down / up |
| `h` | Collapse open folder, or jump to parent |
| `l` | Expand folder under cursor |
| `Enter` / `o` | Open file or folder under cursor |
| `O` | Open in a new tab |
| `gg` / `G` | Jump to first / last visible node |
| `/` | Focus filter input (substring match on visible names) |
| `n` / `N` | Next / previous filter match |
| `r` | Reload current folder's children |
| `\` | Toggle sidebar visibility (state persisted in localStorage) |
| `?` | Toggle keybinding cheatsheet overlay |
| `Esc` | Clear filter / close help |

Click also works — clicking a folder toggles expand, clicking a file opens it. The currently-viewed file is highlighted; on page load, the sidebar auto-expands ancestors of the active path so the file is always visible.

The markdown reader has its own ToC + plan-nav sidebar, so the file-browser sidebar is intentionally NOT injected there. Press `← Folder` (or browser back) to return to the gallery and use the tree.

### Root persistence

The current tree root is saved to `localStorage['fb-tree-root']` on every page load. URL `?root=<path>` is the canonical setter — when present, the server validates against the allow-list and the rendered value is written to storage. When absent, the client redirects once via `location.replace` to the same URL with the stored root appended, so refresh keeps the tree where you left it. A stale stored root that the server rejects is automatically replaced with the rendered (safe) value, so storage self-heals. The `↑` rebase button keeps working — it updates the URL `?root=`, which then flows through the same save path.

### Customizing / extending

- `assets/sidebar.js` — keybinding map and tree behavior. Add a binding by extending the `keydown` switch.
- `assets/sidebar.css` — layout (CSS grid: `var(--sidebar-width) 1fr`), colors via `--sidebar-*` tokens.
- `lib/sidebar.cjs` — HTML stub including filter input + cheatsheet markup.
- `lib/tree-api.cjs` — server-side directory listing. Add a new file classification by extending `classifyFile`.

## Architecture

```
scripts/
├── server.cjs                      # CLI entry
├── lib/
│   ├── port-finder.cjs             # 3556-3600 range
│   ├── process-mgr.cjs             # PID prefix file-browser-*
│   ├── http-server.cjs             # Routing + dispatch by extension
│   ├── markdown-page.cjs           # Composes novel-theme HTML for .md
│   ├── markdown-renderer.cjs       # marked + highlight.js + gray-matter
│   ├── plan-navigator.cjs          # Plan detection, sidebar, prev/next
│   ├── plan-table-parser.cjs       # plan.md table → phases
│   ├── media-renderer.cjs          # Gallery + single-view for images/video/audio
│   ├── sidebar.cjs                 # Sidebar HTML stub injected into gallery + single-view
│   └── tree-api.cjs                # /api/tree directory listing (lazy)
└── tests/
    └── server.test.cjs             # Smoke tests for every dispatch path

assets/
├── styles.css                      # Media gallery + single-view theme
├── sidebar.css                     # Sidebar layout + tree styling
├── sidebar.js                      # Sidebar tree + vim keybindings
├── novel-theme.css                 # Markdown theme entry (imports modules)
├── styles/                         # Modular markdown CSS (variables, base, content, mermaid, ...)
├── template.html                   # Markdown viewer template
├── reader.js                       # Markdown client-side: Mermaid, sidebar, shortcuts
└── pdfjs-viewer/                   # Custom viewer.html + viewer.js + viewer.css; pdfjs-dist
                                    # runtime deps (build/, web/, cmaps/, standard_fonts/, wasm/)
                                    # populated by `postinstall` from node_modules/pdfjs-dist
```

### Custom PDF viewer architecture

`/assets/pdfjs-viewer/viewer.html` is custom — pdfjs-dist (npm) does NOT ship Mozilla's standalone `web/viewer.html`, only the embeddable `PDFViewer` component. Our viewer wraps that component with a minimal toolbar (~250 LOC across viewer.html / viewer.js / viewer.css). Settings: `enableScripting: false`, `isEvalSupported: false` (defense-in-depth against CVE-2024-4367; pdfjs-dist ≥4.2.67 already disables `isEvalSupported` at the component level). To extend: edit `viewer.html` (toolbar markup), `viewer.js` (component wiring), or `viewer.css` (styling). Component API: https://github.com/mozilla/pdf.js/wiki/Viewer-options

### Upgrading pdfjs-dist

1. Bump `pdfjs-dist` in `package.json`.
2. Re-run `npm install` (postinstall repopulates `assets/pdfjs-viewer/`).
3. Run tests (`node scripts/tests/server.test.cjs`).
4. Re-read exports of `assets/pdfjs-viewer/web/pdf_viewer.mjs` — verify `PDFViewer`, `EventBus`, `PDFLinkService`, `PDFFindController`, `PDFHistory`, `DownloadManager`, `parseQueryString` are still present with compatible signatures vs `viewer.js`.
5. Manual smoke: open a real multi-page PDF and exercise every toolbar control (prev/next, page input, zoom, search, download).
6. Check the changelog for security advisories — pin minimum to ≥4.2.67 (CVE-2024-4367).

## Integration

### Hammerspoon (Hyper+V → smart route to Arc)

`dotfiles/hammerspoon/.hammerspoon/init.lua` already routes the clipboard:

- `.md/.markdown/.mdx` → calls file-browser `/view` (dispatches to markdown reader)
- image/video/audio extensions → calls file-browser `/view` (dispatches to media viewer)
- code/config files → opens in nvim
- everything else → `open`

The Hammerspoon URL always appends `&root=<computed>` (file's parent dir, or the dir itself when launched on a folder) so each fresh launch overrides any `localStorage`-saved root from the previous session. Without this, the persistence layer would keep the sidebar anchored at whatever path the server was first started with.

### nvim

`<leader>mv` (in `polish.lua`) — open current buffer in file-browser. If the file is renderable (markdown / image / video / audio), opens single-view; otherwise opens the parent directory's gallery.

## Testing

```bash
node $HOME/skills/skills/file-browser/scripts/tests/server.test.cjs
```

Boots on a free port, hits every dispatch path (welcome, gallery, image view, markdown view, PDF viewer iframe, raw passthrough, file streaming, Range, traversal guard, missing params, 404, tree API, sidebar injection), cleans up. 38 tests.

## Security

- All `?file=` / `?dir=` / `/file/*` paths must resolve under one of the allow-list directories (`$HOME` + cwd + target dir + assets dir).
- Null-byte and `..` traversal rejected.
- Error messages sanitized to strip absolute paths.
- Server binds to `localhost` by default; `--host 0.0.0.0` opt-in for LAN.

## Open Questions

- HEIC works in Safari only. Should we add ImageMagick on-the-fly conversion for Chrome? (Requires native dep — breaks the zero-runtime-dep posture for media.)
- Should the gallery prefetch markdown front matter (`title`, `status`) so plan dirs render with badges before clicking in? (Adds I/O cost per gallery hit.)
- Worth adding a `/api/files?dir=<path>` JSON endpoint so the gallery could be a SPA later? (YAGNI for now.)
- Should we render gallery thumbnails for PDFs (page-1 canvas, client-side, lazy via PDF.js)?
- Should we add custom vim keybindings inside the PDF viewer iframe (postMessage bridge)?
- Should we add an outline/bookmarks panel to the PDF viewer? (`PDFOutlineViewer` would need to be added to the component import set.)
- Should we re-add a thumbnails sidebar to the PDF viewer? (`PDFThumbnailViewer` is not exported from `pdfjs-dist@5.7.0`'s `pdf_viewer.mjs`; would require re-implementing or upgrading to a future major.)
