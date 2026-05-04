---
name: file-browser
description: "Local HTTP server that renders markdown, images, video, and audio in the browser. Dispatches by file extension - markdown gets the novel-theme reader (Mermaid, plan nav, ToC); images/video/audio get a gallery + single-view with Range-aware streaming. One server, one port, one CLI."
license: MIT
argument-hint: "[file-or-directory]"
metadata:
  author: vanducng
  version: "0.2.0"
---

# file-browser

One local HTTP server, one port, one CLI — handles markdown, images, video, and audio. Dispatches by file extension at the `/view` route: markdown goes to the novel-theme reader; image/video/audio go to the media viewer.

## Installation

```bash
cd $HOME/skills/skills/file-browser && npm install
```

**Dependencies:** `marked`, `highlight.js`, `gray-matter` (for markdown). Media rendering is zero-dep — browser does the work.

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
| `/view?file=<abs-path>` | **Dispatches by extension.** `.md/.markdown/.mdx` → novel-theme markdown reader (Mermaid, plan nav, ToC). Image/video/audio → media single-view with arrow-key prev/next. |
| `/browse?dir=<abs-path>` | Gallery: folders, Documents (markdown), Media (image/video/audio), Other files. |
| `/file/<abs-path>` | Raw byte streaming with HTTP `Range` support (required for video seeking and Safari audio). |
| `/assets/*` | Static assets (theme CSS, reader JS). |
| `/` | Welcome / route reference. |

## Supported Formats

**Documents:** `.md`, `.markdown`, `.mdx` (rendered with [marked](https://marked.js.org/) + `highlight.js` + Mermaid)
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
│   └── media-renderer.cjs          # Gallery + single-view for images/video/audio
└── tests/
    └── server.test.cjs             # Smoke tests for every dispatch path

assets/
├── styles.css                      # Media gallery + single-view theme
├── novel-theme.css                 # Markdown theme entry (imports modules)
├── styles/                         # Modular markdown CSS (variables, base, content, mermaid, ...)
├── template.html                   # Markdown viewer template
└── reader.js                       # Markdown client-side: Mermaid, sidebar, shortcuts
```

## Integration

### Hammerspoon (Hyper+V → smart route to Arc)

`dotfiles/hammerspoon/.hammerspoon/init.lua` already routes the clipboard:

- `.md/.markdown/.mdx` → calls file-browser `/view` (dispatches to markdown reader)
- image/video/audio extensions → calls file-browser `/view` (dispatches to media viewer)
- code/config files → opens in nvim
- everything else → `open`

### nvim

`<leader>mv` (in `polish.lua`) — open current buffer in file-browser. If the file is renderable (markdown / image / video / audio), opens single-view; otherwise opens the parent directory's gallery.

## Testing

```bash
node $HOME/skills/skills/file-browser/scripts/tests/server.test.cjs
```

Boots on a free port, hits every dispatch path (welcome, gallery, image view, markdown view, file streaming, Range, traversal guard, missing params, 404), cleans up. 11 tests.

## Security

- All `?file=` / `?dir=` / `/file/*` paths must resolve under one of the allow-list directories (`$HOME` + cwd + target dir + assets dir).
- Null-byte and `..` traversal rejected.
- Error messages sanitized to strip absolute paths.
- Server binds to `localhost` by default; `--host 0.0.0.0` opt-in for LAN.

## Open Questions

- HEIC works in Safari only. Should we add ImageMagick on-the-fly conversion for Chrome? (Requires native dep — breaks the zero-runtime-dep posture for media.)
- Should the gallery prefetch markdown front matter (`title`, `status`) so plan dirs render with badges before clicking in? (Adds I/O cost per gallery hit.)
- Worth adding a `/api/files?dir=<path>` JSON endpoint so the gallery could be a SPA later? (YAGNI for now.)
