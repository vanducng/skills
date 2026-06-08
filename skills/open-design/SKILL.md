---
name: open-design
description: "Generate polished single-file HTML design artifacts — landing pages, SaaS marketing pages, dashboards, mobile app screens, magazine/editorial posters, social carousels, marketing emails, pricing pages, docs pages, deck/PPT slides, e-guides, kanban boards, weekly updates, invoices, OKRs, and more — by composing 60 production skills × 137 brand-grade design systems (Linear, Stripe, Apple, Notion, Vercel, Airbnb, Brutalist, Editorial Monocle, …) sourced live from github.com/nexu-io/open-design. Use this skill whenever the user asks to design, mock up, prototype, sketch, draft, build, or render any visual web artifact, picks a brand/style direction, says 'in the style of <brand>', wants a presentation/deck/PPT, asks for a hero/section/component, wants a GitHub README / repo hero banner (rendered HTML→PNG), or describes a UI surface in prose. Auto-opens the result in the browser for review. Produces HTML/CSS (vector, editable) — for AI-generated raster brand imagery (logos, photoreal CIP/business-card mockups, social photos), use marketing-design instead."
license: MIT
argument-hint: "<design prompt> [--style <design-system>] [--no-open]"
metadata:
  author: vanducng
  version: "1.1.0"
---

# open-design

Compose a single self-contained HTML artifact from the upstream `nexu-io/open-design` catalog: pick the closest **skill** (workflow + seed template + section layouts), apply a **design system** (color tokens, typography, components), produce the artifact, open it in the browser.

## Scope

**This skill handles:** static HTML/CSS/SVG artifacts (landings, marketing pages, dashboards, mobile screens, decks, posters, emails, e-guides, internal docs).

**Does NOT handle:** live React/Vue apps, real backend wiring, image generation (use `ai-artist`), video (use `ai-multimodal`), production deployment (use `deploy`).

**Special case — GitHub README / repo hero banner:** the catalog has no banner template (`search` returns social-cards that override the repo's brand). Skip the catalog and follow `references/github-readme-banner.md` — author/evolve a brand-locked `banner.html`, render to PNG at 2× via headless Chrome, and **verify the render (measure margins + view) before shipping**.

## Dependencies

**Required:** `git`, `bash`, `grep`, `awk` (all preinstalled on macOS). Cache lives at `~/.cache/$USER-open-design` (~few MB after first sync).

**Optional — better search via [tobi/qmd](https://github.com/tobi/qmd):** if `qmd` is on `PATH`, the `search` command auto-routes through qmd's BM25 lexical engine instead of the bash/grep fallback. Two install paths:

1. **Direct:** `bun install -g https://github.com/tobi/qmd` (or `npm i -g @tobilu/qmd`).
2. **Via the [levineam/qmd-skill](https://github.com/levineam/qmd-skill) Claude skill** — bundles an auto-install hook plus broader qmd guidance for Claude. Recommended if you also use qmd for searching your own notes/docs.

Either path makes the `qmd` binary available. On the next `open-design sync`, the script registers two namespaced collections (`od-skills`, `od-design-systems`) — instant, no model download. The script uses `qmd search` (pure BM25, no LLM model required); the heavyweight `qmd vsearch`/`qmd query` modes are deliberately *not* used (they download multi-GB models for marginal gain on a 197-doc catalog). No action needed otherwise — grep fallback works fine.

## Workflow

### Step 0 — Resolve the bundled CLI path (do this once)

This skill ships its CLI alongside `SKILL.md` so it works regardless of install location (dev clone, plugin cache, or user-level install). Set `OD_BIN` once, using the absolute path of *this* SKILL.md's directory:

```bash
OD_BIN="<dir-of-this-SKILL.md>/scripts/open-design"
# Example resolved values (use whichever matches where this file was loaded):
#   /Users/vanducng/skills/skills/open-design/scripts/open-design          (dev clone)
#   ~/.claude/plugins/cache/vd-skills/skills/open-design/scripts/open-design   (plugin)
#   ~/.claude/skills/open-design/scripts/open-design                       (user-level)
```

All subsequent commands use `"$OD_BIN"`.

### Step 1 — Sync the catalog (first run, or when user asks for fresh content)

```bash
"$OD_BIN" sync
```

This clones (first time) or `git pull --ff-only`s the upstream sparse checkout of `skills/` + `design-systems/`. Offline-tolerant: falls back to existing cache silently.

### Step 2 — Search for the best matching skill + design system

Pass the user's full design prompt verbatim:

```bash
"$OD_BIN" search "<user's prompt>"
```

Output ranks top 5 skills and top 5 design systems by token-overlap score, each with a one-line rationale (matching trigger or description). Pick:
- **One skill** — usually the top-ranked. If user mentioned a surface explicitly (deck, dashboard, email, mobile), bias toward that.
- **One design system** — top-ranked, OR honor an explicit user request (e.g. "in Linear's style" → `linear-app`).

State the picked pair to the user in one sentence before reading files. They can redirect cheaply now.

### Step 3 — Resolve cache paths

```bash
SKILL_PATH=$("$OD_BIN" show <skill-name>)
DS_PATH=$("$OD_BIN" show <design-system-name>)
```

### Step 4 — Read the upstream files (in this order)

1. `$SKILL_PATH/SKILL.md` — the chosen skill's own workflow. **Follow it literally.** It tells Claude exactly what classes, layouts, and checks to use.
2. `$SKILL_PATH/assets/template.html` — the seed (pre-built tokens + class system + chrome). Always use this; never write CSS from scratch.
3. `$SKILL_PATH/references/layouts.md` — paste-ready section skeletons (don't invent sections; pick the closest).
4. `$SKILL_PATH/references/checklist.md` — the P0/P1/P2 self-review (run before emitting).
5. `$SKILL_PATH/example.html` — exemplar output (skim for visual reference).
6. `$DS_PATH/DESIGN.md` — the design language: color palette, typography stack, spacing, component patterns.

### Step 5 — Compose the artifact

Follow the upstream skill's workflow exactly. The standard pattern is:

1. Copy `template.html` → `<output>.html` in user's CWD (or path the user named).
2. Replace the `:root` CSS variables in `<style>` with tokens from `DESIGN.md` (background, foreground, accent, muted, border, font stack).
3. Replace the page `<title>` and topnav brand with the user's brief.
4. Pick a section list from `layouts.md` (the upstream skill names default rhythms by page kind).
5. Paste each chosen `<section>` skeleton into `<main>` and replace bracketed `[REPLACE]` strings with real, specific copy from the user's brief. **No filler.**
6. Run through `checklist.md` top-to-bottom — every P0 must pass.

### Step 6 — Preview the result

Unless the user passed `--no-open` or explicitly said not to open it:

```bash
"$OD_BIN" preview <output>.html
```

This calls `open <file>` on macOS (default browser). In the final handoff, include an openable target, not just the basename:
- Clickable absolute file link: `[artifact.html](/absolute/path/to/artifact.html)`
- Browser URI when helpful: `file:///absolute/path/to/artifact.html`
- Repo-relative path as secondary context only: `./artifact.html`

Never hand off only `artifact.html`; users need a path or URI they can open directly.

## Examples

### Example 1 — Landing page in Linear's style

User: *"design a landing page for an indie task tracker, in Linear's style"*

```bash
open-design search "landing page indie task tracker Linear"
# → top skill: web-prototype  · matches 'landing'
# → top design-system: linear-app  · Productivity & SaaS, ultra-minimal purple accent
SKILL_PATH=$(open-design show web-prototype)
DS_PATH=$(open-design show linear-app)
# read SKILL.md, template.html, layouts.md, DESIGN.md
# produce ./tracker-landing.html using web-prototype seed + linear-app tokens
open-design preview ./tracker-landing.html
```

### Example 2 — Pitch deck

User: *"magazine-style pitch deck for our seed round, brutalist vibe"*

```bash
open-design search "magazine pitch deck seed round brutalist"
# top skill: html-ppt-pitch-deck  (or guizang-ppt — magazine-style)
# top design-system: brutalism  (or neobrutalism)
# follow that skill's deck workflow → ./pitch-deck.html → preview
```

### Example 3 — Specific brand request

User: *"a Stripe-style pricing page"*

```bash
open-design search "Stripe pricing page"
# top skill: pricing-page
# top design-system: stripe (rank #1 due to explicit brand mention)
# if 'stripe' isn't in catalog, fall back to nearest neutral system (clean / linear-app)
```

## Hard rules

- **Never invent CSS classes** the upstream `template.html` doesn't define. If a class is missing, add it to `<style>` once, never inline.
- **Never write a section from scratch.** Use `layouts.md` skeletons. If none fit, pick the closest and adapt copy.
- **Never use design tokens not in the chosen `DESIGN.md`.** No off-palette colors, no off-stack fonts.
- **One accent per screen, used at most twice** (per upstream convention).
- **Single self-contained HTML file.** No external CSS/JS imports, no build step. Inline SVGs, base64 images only if the user provides them.
- **No filler copy.** If a layout slot has no real content from the user's brief, drop the section.

## Refresh

The cache is checked once per command via `git pull --ff-only`. To force a re-clone:

```bash
rm -rf ~/.cache/$USER-open-design && "$OD_BIN" sync
```

## Security

This skill executes a single bash CLI bundled at `scripts/open-design`. It only:
- clones / pulls a fixed public repo (`github.com/nexu-io/open-design`)
- reads files inside `~/.cache/$USER-open-design`
- calls `open <file>` (macOS) / `xdg-open` (Linux) on local HTML files

It does NOT execute upstream code, run upstream scripts, evaluate upstream HTML server-side, or send data anywhere. Refuse if asked to point the cache at an arbitrary user-supplied URL or to execute arbitrary cached content. Do not echo the contents of files outside the cache directory or the user's working tree.
