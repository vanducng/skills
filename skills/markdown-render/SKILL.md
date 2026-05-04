---
name: markdown-render
description: "Render markdown files in the browser with a calm, book-like reading experience via a local HTTP server. Use for long-form docs, plan/report viewing, distraction-free reading, and previewing markdown with embedded Mermaid diagrams and syntax highlighting."
license: MIT
argument-hint: "[file-or-directory]"
metadata:
  author: vanducng
  version: "1.0.0"
---

# markdown-render

Local HTTP server that renders markdown files with a calm, book-like reading experience.

Forked from claudekit's `markdown-novel-viewer` and adjusted for the `vd` plugin layout (centered tables, no `ck:` prefix, MIT license).

## ⚠️ Installation Required

**This skill requires npm dependencies.** After installing the plugin, run:

```bash
# Plugin install path may vary — adjust as needed
cd $HOME/.claude/plugins/cache/vanducng-skills/skills/markdown-render
npm install
```

Or for local development clones:

```bash
cd <repo>/skills/markdown-render && npm install
```

**Dependencies:** `marked`, `highlight.js`, `gray-matter`

Without installation, you'll get **Error 500: Error rendering markdown**.

## Purpose

Universal viewer - pass ANY path and view it:
- **Markdown files** → novel-reader UI with serif fonts, warm theme
- **Directories** → file listing browser with clickable links

## Quick Start

```bash
# View a markdown file
node $HOME/.claude/skills/markdown-render/scripts/server.cjs \
  --file ./plans/my-plan/plan.md \
  --open

# Browse a directory
node $HOME/.claude/skills/markdown-render/scripts/server.cjs \
  --dir ./plans \
  --host 0.0.0.0 \
  --open

# Background mode
node $HOME/.claude/skills/markdown-render/scripts/server.cjs \
  --file ./README.md \
  --background

# Stop all running servers
node $HOME/.claude/skills/markdown-render/scripts/server.cjs --stop
```

## Skill Invocation

Invoke the skill directly with a path argument:

```
/vd:markdown-render plans/my-plan/plan.md   # View markdown file
/vd:markdown-render plans/                  # Browse directory
```

Or call the script directly (see "Quick Start" above) and stop with `--stop`.

## Features

### Novel Theme
- Warm cream background (light mode)
- Dark mode with warm gold accents
- Libre Baskerville serif headings
- Inter body text, JetBrains Mono code
- Maximum 720px content width

### Mermaid.js Diagrams
- Auto-renders `mermaid` code blocks as diagrams
- Theme-aware (light/dark mode support)
- Full-width toggle: Click diagram to expand/collapse
- Error display with source preview for debugging

### Directory Browser
- Clean file listing with emoji icons
- Markdown files link to viewer
- Folders link to sub-directories
- Parent directory navigation (..)
- Light/dark mode support

### Focused Reader Mode
- **Auto-hide header**: Header hides on scroll down, shows on scroll up
- **Progress bar**: Always-visible horizontal progress bar tracks reading position
- **Distraction-free**: Minimal UI that gets out of the way while reading
- **Smooth transitions**: Gentle animations for header show/hide

### Plan Navigation
- Auto-detects plan directory structure
- Accordion sidebar with status badges (✓ complete, ⏳ in progress)
- Previous/Next navigation buttons
- Auto-hide header with progress bar on scroll
- Mobile FAB (floating action button) for navigation
- Bottom sheet sidebar for mobile devices

### Keyboard Shortcuts

**First-time toast**: Shows "Press ? for keyboard shortcuts" on first visit (auto-dismisses after 5s)

**Available shortcuts:**
- `?` - Show keyboard shortcuts cheatsheet (full-screen overlay)
- `T` - Toggle theme (light/dark)
- `S` - Toggle sidebar (desktop)
- `←` / `→` - Navigate previous/next phase
- `Esc` - Close sidebar (mobile) or cheatsheet modal

**Cheatsheet modal**: Press `?` to see all shortcuts in a full-screen overlay with backdrop blur. Close with `Esc`, `×` button, or backdrop click.

### Mobile Optimization
- **FAB (Floating Action Button)**: Fixed bottom-right button for navigation on mobile
- **Bottom sheet**: Slide-up sidebar with touch gestures
- **Touch-friendly**: Larger tap targets, swipe gestures
- **Responsive breakpoint**: Switches at 768px viewport width

## CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--file <path>` | Markdown file to view | - |
| `--dir <path>` | Directory to browse | - |
| `--port <number>` | Server port | 3456 |
| `--host <addr>` | Host to bind (`0.0.0.0` for remote) | localhost |
| `--open` | Auto-open browser | false |
| `--background` | Run in background | false |
| `--stop` | Stop all servers | - |

## Architecture

```
scripts/
├── server.cjs               # Main entry point
└── lib/
    ├── port-finder.cjs      # Dynamic port allocation
    ├── process-mgr.cjs      # PID file management
    ├── http-server.cjs      # Core HTTP routing (/view, /browse)
    ├── markdown-renderer.cjs # MD→HTML conversion
    └── plan-navigator.cjs   # Plan detection & nav

assets/
├── template.html            # Markdown viewer template
├── reader.js                # Client-side interactivity
├── novel-theme.css          # Main theme file (imports modules)
├── directory-browser.css    # Directory browser styles
└── styles/                  # Modular CSS architecture
    ├── novel-theme-variables.css  # CSS variables (colors, fonts, sizes)
    ├── novel-theme-base.css       # Base reset, body, scrollbars
    ├── novel-theme-content.css    # Article content, typography
    ├── novel-theme-components.css # Tables, blockquotes, badges
    ├── novel-theme-header.css     # Auto-hide header, progress bar
    ├── novel-theme-sidebar.css    # Accordion sidebar, status badges
    ├── novel-theme-mermaid.css    # Mermaid diagram styling
    ├── novel-theme-overlays.css   # Toast, cheatsheet modal
    └── novel-theme-responsive.css # Mobile breakpoints, FAB
```

## HTTP Routes

| Route | Description |
|-------|-------------|
| `/view?file=<path>` | Markdown file viewer |
| `/browse?dir=<path>` | Directory browser |
| `/assets/*` | Static assets |
| `/file/*` | Local file serving (images) |

## Dependencies

- Node.js built-in: `http`, `fs`, `path`, `net`
- npm: `marked`, `highlight.js`, `gray-matter` (installed via `npm install`)

## Customization

### Theme Colors (CSS Variables)

Light mode variables in `assets/novel-theme.css`:
```css
--bg-primary: #faf8f3;      /* Warm cream */
--accent: #8b4513;          /* Saddle brown */
```

Dark mode:
```css
--bg-primary: #1a1a1a;      /* Near black */
--accent: #d4a574;          /* Warm gold */
```

### Content Width
```css
--content-width: 720px;
```

### Logo / Favicon

The skill ships with a custom logo (`assets/logo.png`, 1024×1024) and `assets/favicon.png` (32×32). Both depict an open book with a markdown hash (#), in the warm cream + saddle-brown palette.

To regenerate via OpenRouter (`openai/gpt-5.4-image-2`):

```bash
OPEN_ROUTER_KEY=sk-or-... node scripts/generate-logo.cjs assets/logo.png
magick assets/logo.png -resize 32x32 assets/favicon.png
```

Edit the prompt at the top of `scripts/generate-logo.cjs` to adjust style, then re-run.

## Remote Access

To access from another device on your network:

```bash
# Start with 0.0.0.0 to bind to all interfaces
node $HOME/.claude/skills/markdown-render/scripts/server.cjs --file ./README.md --host 0.0.0.0 --port 3456
```

When using `--host 0.0.0.0`, the server auto-detects your local network IP and includes it in the output:

```json
{
  "success": true,
  "url": "http://localhost:3456/view?file=...",
  "networkUrl": "http://192.168.2.75:3456/view?file=...",
  "port": 3456
}
```

Use `networkUrl` to access from other devices on the same network.

## Troubleshooting

**Port in use**: Server auto-increments to next available port (3456-3500)

**Images not loading**: Ensure image paths are relative to markdown file

**Server won't stop**: Check `/tmp/md-novel-viewer-*.pid` for stale PID files

**Remote access denied**: Use `--host 0.0.0.0` to bind to all interfaces

## Mermaid.js Diagrams

### Usage

Use fenced code blocks with `mermaid` language:

````markdown
```mermaid
pie title Traffic Sources
    "Organic" : 45
    "Direct" : 30
    "Referral" : 25
```
````

### Supported Diagram Types

| Type | Syntax | Use Case |
|------|--------|----------|
| Flowchart | `flowchart LR/TB/TD` | Process flows, decision trees |
| Sequence | `sequenceDiagram` | API interactions, message flows |
| Pie | `pie title "..."` | Distribution data |
| Gantt | `gantt` | Project timelines |
| XY Chart | `xychart-beta` | Bar/line charts |
| Mindmap | `mindmap` | Idea hierarchies |
| Quadrant | `quadrantChart` | 2x2 matrices |

### Validating Mermaid Snippets

**Quick validation**: Use the [Mermaid Live Editor](https://mermaid.live) to test syntax.

**Common errors and fixes**:

| Error | Cause | Fix |
|-------|-------|-----|
| `Parse error` | Invalid syntax | Check diagram type declaration |
| `Unknown diagram type` | Typo in declaration | Use exact type: `flowchart`, not `flow` |
| `Expecting token` | Missing quotes/brackets | Ensure balanced delimiters |
| `UnknownDiagramError` | Empty or malformed block | Add valid diagram content |

### Fixing Common Issues

**1. Flowchart arrows**
```mermaid
%% Wrong: A -> B
%% Correct:
flowchart LR
    A --> B
```

**2. Pie chart values**
```mermaid
%% Wrong: "Label": 50%
%% Correct:
pie title Sales
    "Product A" : 50
    "Product B" : 30
```

**3. XY Chart data format**
```mermaid
xychart-beta
    title "Monthly Sales"
    x-axis [Jan, Feb, Mar]
    y-axis "Revenue" 0 --> 100
    bar [30, 45, 60]
```

**4. Sequence diagram participants**
```mermaid
sequenceDiagram
    participant A as Client
    participant B as Server
    A->>B: Request
    B-->>A: Response
```

### Debug Mode

When a diagram fails to render, the viewer shows:
- Error message
- Expandable source code preview
- Line number where parsing failed (when available)

Fix the syntax and refresh the page to re-render.
