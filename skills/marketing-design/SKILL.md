---
name: marketing-design
description: "Marketing brand-asset generation (raster images via AI): logo design (55 styles, 30 palettes, 25 industries), corporate identity / CIP mockups (50 deliverables — business card, letterhead, signage, packaging, apparel), banner design (22 styles, social/ads/web/print), SVG icon design (15 styles), social photos (multi-platform), and model-agnostic poster prompts. Default image engine is Codex gpt-image-2 (ChatGPT subscription via `codex login`), attaching the brand logo as a reference image for CIP compositing; falls back to Gemini Nano Banana (GEMINI_API_KEY, same key as omnimedia). Actions: design logo, create CIP / brand identity, generate mockups, design banner, generate icon, create social photos, design poster, social media images. Platforms: Facebook, Twitter, LinkedIn, YouTube, Instagram, Pinterest, TikTok, Threads, Google Ads. For HTML/web pages, dashboards, and slide decks, use opendesign instead."
argument-hint: "[design-type] [context]"
license: MIT
metadata:
  author: vanducng
  version: "1.0.0"
---

# Marketing Design

Unified marketing brand-asset skill: logo, CIP, banners, SVG icons, social photos, posters. Generates **raster images** — default engine is **Codex gpt-image-2** (ChatGPT subscription, `codex login`), falling back to **Gemini Nano Banana** (`GEMINI_API_KEY`, the same key `omnimedia` uses). For HTML/web artifacts and slide decks, use `opendesign`.

## When to Use

- Logo design and AI generation
- Corporate identity program (CIP) deliverables — business card, letterhead, signage, packaging, apparel
- Brand visual identity assets
- Banner design for social media, ads, web, print
- Social photos for Instagram, Facebook, LinkedIn, Twitter, Pinterest, TikTok
- Poster design (event, editorial, marketing) with locked-style + varied-composition prompts
- SVG icons and icon sets

> Not this skill: HTML/web pages, dashboards, and slide decks → `opendesign`. Token systems / shadcn-Tailwind code → `vd:webdesign`.

## Sub-skill Routing

All built-in modules are self-contained (references + scripts + data in this skill). Route HTML artifacts and frontend implementation to the installed repo skills listed below.

| Task | Sub-skill | Details |
|------|-----------|---------|
| Static HTML artifacts, decks | `vd:opendesign` | Self-contained HTML/CSS artifacts |
| Frontend UI, tokens, shadcn/Tailwind code | `vd:webdesign` | App UI design/build/review/test |
| Full-stack FastAPI + React apps | `vd:fastreact` | Mockup-first app scaffolding |
| Logo creation, AI generation | Logo (built-in) | `references/logo-design.md` |
| CIP mockups, deliverables | CIP (built-in) | `references/cip-design.md` |
| Presentations, pitch decks | `vd:opendesign` | Use opendesign for slide decks (HTML) |
| Banners, covers, headers | Banner (built-in) | `references/banner-sizes-and-styles.md` |
| Social media images/photos | Social Photos (built-in) | `references/social-photos-design.md` |
| SVG icons, icon sets | Icon (built-in) | `references/icon-design.md` |
| Posters (event, editorial, marketing) | Poster (built-in) | `references/poster-design.md` |

## Image Generation Backend

Raster generators (`logo`, `cip`) default to **Codex `$imagegen` (gpt-image-2)** on the ChatGPT subscription — no API key. One-time setup: `brew install codex && codex login`. If Codex is unavailable (not installed / not logged in / quota), they **fall back to Gemini** automatically.

| Generator | Default engine | Reference image | Force Gemini | Notes |
|-----------|----------------|-----------------|--------------|-------|
| `logo` | Codex gpt-image-2 | — | `--provider gemini` | `--batch` always uses Gemini (Codex = one image/turn) |
| `cip` | Codex gpt-image-2 | brand logo via `--logo` (attached as `-i` reference) | `--provider gemini` | large `--set` faster on Gemini |
| `icon` | Gemini (SVG **code**, not raster) | — | n/a | Codex can't emit SVG markup |
| `poster` | model-agnostic prompt emitter | — | n/a | prints a prompt for any image model |
| `banner` / social photos | HTML→screenshot | — | n/a | not direct AI image gen |

`--provider`: `codex` (default) · `gemini` (force Nano Banana) · `auto` (codex→gemini). Codex takes 5–30s/image. Reference-image compositing requires codex-cli ≥ 0.137.

## Logo Design (Built-in)

55+ styles, 30 color palettes, 25 industry guides. Default engine: **Codex gpt-image-2** (Gemini fallback).

### Logo: Generate Design Brief

```bash
python3 ~/.claude/skills/marketing-design/scripts/logo/search.py "tech startup modern" --design-brief -p "BrandName"
```

### Logo: Search Styles/Colors/Industries

```bash
python3 ~/.claude/skills/marketing-design/scripts/logo/search.py "minimalist clean" --domain style
python3 ~/.claude/skills/marketing-design/scripts/logo/search.py "tech professional" --domain color
python3 ~/.claude/skills/marketing-design/scripts/logo/search.py "healthcare medical" --domain industry
```

### Logo: Generate with AI

**ALWAYS** generate output logo images with white background.

```bash
# Default: Codex gpt-image-2 (run `codex login` once)
python3 ~/.claude/skills/marketing-design/scripts/logo/generate.py --brand "TechFlow" --style minimalist --industry tech
python3 ~/.claude/skills/marketing-design/scripts/logo/generate.py --prompt "coffee shop vintage badge" --style vintage

# Force Gemini Nano Banana (e.g. for aspect-ratio control or --pro)
python3 ~/.claude/skills/marketing-design/scripts/logo/generate.py --brand "TechFlow" --provider gemini --pro

# Variant batch (Gemini — Codex has no batch mode)
python3 ~/.claude/skills/marketing-design/scripts/logo/generate.py --brand "TechFlow" --batch 9 --output-dir ./logos
```

**IMPORTANT:** When scripts fail, try to fix them directly.

After generation, ask whether the user wants an HTML preview gallery. If yes, use `vd:opendesign` for a static gallery artifact.

## CIP Design (Built-in)

50+ deliverables, 20 styles, 20 industries. Default engine: **Codex gpt-image-2** with the brand logo attached as a reference image (`-i`); Gemini Nano Banana fallback.

### CIP: Generate Brief

```bash
python3 ~/.claude/skills/marketing-design/scripts/cip/search.py "tech startup" --cip-brief -b "BrandName"
```

### CIP: Search Domains

```bash
python3 ~/.claude/skills/marketing-design/scripts/cip/search.py "business card letterhead" --domain deliverable
python3 ~/.claude/skills/marketing-design/scripts/cip/search.py "luxury premium elegant" --domain style
python3 ~/.claude/skills/marketing-design/scripts/cip/search.py "hospitality hotel" --domain industry
python3 ~/.claude/skills/marketing-design/scripts/cip/search.py "office reception" --domain mockup
```

### CIP: Generate Mockups

```bash
# With logo (RECOMMENDED)
python3 ~/.claude/skills/marketing-design/scripts/cip/generate.py --brand "TopGroup" --logo /path/to/logo.png --deliverable "business card" --industry "consulting"

# Full CIP set
python3 ~/.claude/skills/marketing-design/scripts/cip/generate.py --brand "TopGroup" --logo /path/to/logo.png --industry "consulting" --set

# Pro model (4K text)
python3 ~/.claude/skills/marketing-design/scripts/cip/generate.py --brand "TopGroup" --logo logo.png --deliverable "business card" --model pro

# Without logo
python3 ~/.claude/skills/marketing-design/scripts/cip/generate.py --brand "TechFlow" --deliverable "business card" --no-logo-prompt

# Force Gemini (faster for large --set)
python3 ~/.claude/skills/marketing-design/scripts/cip/generate.py --brand "TopGroup" --logo logo.png --industry "consulting" --set --provider gemini
```

Engines: **Codex gpt-image-2** (default, logo attached as reference image). Gemini fallback models — `--model flash` (`gemini-2.5-flash-image`), `--model pro` (`gemini-3-pro-image-preview`).

### CIP: Render HTML Presentation

```bash
python3 ~/.claude/skills/marketing-design/scripts/cip/render-html.py --brand "TopGroup" --industry "consulting" --images /path/to/cip-output
```

**Tip:** If no logo exists, use Logo Design section above first.

## Banner Design (Built-in)

22 art direction styles across social, ads, web, print. Uses the built-in banner reference, this skill's raster generation flow when imagery is needed, and browser/Playwright screenshots for exact-pixel export.

Load `references/banner-sizes-and-styles.md` for complete sizes and styles reference.

### Banner: Workflow

1. **Gather requirements** — purpose, platform, content, brand, style, quantity
2. **Research** — collect visual references only when the brief lacks a clear direction
3. **Design** — create HTML/CSS banner variants; generate raster visuals through this skill's image flow when needed
4. **Export** — screenshot to PNG at exact dimensions via Browser, Playwright, or Chrome
5. **Present** — Show all options side-by-side, iterate on feedback

### Banner: Quick Size Reference

| Platform | Type | Size (px) |
|----------|------|-----------|
| Facebook | Cover | 820 x 312 |
| Twitter/X | Header | 1500 x 500 |
| LinkedIn | Personal | 1584 x 396 |
| YouTube | Channel art | 2560 x 1440 |
| Instagram | Story | 1080 x 1920 |
| Instagram | Post | 1080 x 1080 |
| Google Ads | Med Rectangle | 300 x 250 |
| Website | Hero | 1920 x 600-1080 |

### Banner: Top Art Styles

| Style | Best For |
|-------|----------|
| Minimalist | SaaS, tech |
| Bold Typography | Announcements |
| Gradient | Modern brands |
| Photo-Based | Lifestyle, e-com |
| Geometric | Tech, fintech |
| Glassmorphism | SaaS, apps |
| Neon/Cyberpunk | Gaming, events |

### Banner: Design Rules

- Safe zones: critical content in central 70-80%
- One CTA per banner, bottom-right, min 44px height
- Max 2 fonts, min 16px body, ≥32px headline
- Text under 20% for ads (Meta penalizes)
- Print: 300 DPI, CMYK, 3-5mm bleed

## Icon Design (Built-in)

15 styles, 12 categories. Gemini 3.1 Pro Preview generates SVG text output.

### Icon: Generate Single Icon

```bash
python3 ~/.claude/skills/marketing-design/scripts/icon/generate.py --prompt "settings gear" --style outlined
python3 ~/.claude/skills/marketing-design/scripts/icon/generate.py --prompt "shopping cart" --style filled --color "#6366F1"
python3 ~/.claude/skills/marketing-design/scripts/icon/generate.py --name "dashboard" --category navigation --style duotone
```

### Icon: Generate Batch Variations

```bash
python3 ~/.claude/skills/marketing-design/scripts/icon/generate.py --prompt "cloud upload" --batch 4 --output-dir ./icons
```

### Icon: Multi-size Export

```bash
python3 ~/.claude/skills/marketing-design/scripts/icon/generate.py --prompt "user profile" --sizes "16,24,32,48" --output-dir ./icons
```

### Icon: Top Styles

| Style | Best For |
|-------|----------|
| outlined | UI interfaces, web apps |
| filled | Mobile apps, nav bars |
| duotone | Marketing, landing pages |
| rounded | Friendly apps, health |
| sharp | Tech, fintech, enterprise |
| flat | Material design, Google-style |
| gradient | Modern brands, SaaS |

**Model:** `gemini-3.1-pro-preview` — text-only output (SVG is XML text). No image generation API needed.

## Poster Design (Built-in)

20-30 curated styles × 15-20 palettes × 10-14 layouts × 8-12 textures. Model-agnostic — emits text prompts only. Use any image model (Gemini Nano Banana 2, GPT Image, Imagen, Midjourney).

Three axes (style, palette, texture) locked per call to preserve identity; layout + variation seed randomized to guarantee per-call variety. 5 calls with same `--style` → 5 visibly distinct posters that read as one series.

Load `references/poster-design.md` for the full guide and `references/poster-prompt-engineering.md` for prompt anatomy + model-specific tweaks.

### Poster: Search Knowledge Base

```bash
~/.claude/skills/.venv/bin/python3 ~/.claude/skills/marketing-design/scripts/poster/search.py --domain style --query "swiss editorial"
~/.claude/skills/.venv/bin/python3 ~/.claude/skills/marketing-design/scripts/poster/search.py --domain palette --query "warm earthy"
~/.claude/skills/.venv/bin/python3 ~/.claude/skills/marketing-design/scripts/poster/search.py --domain texture --query "risograph"
~/.claude/skills/.venv/bin/python3 ~/.claude/skills/marketing-design/scripts/poster/search.py --domain layout --query "centered grid"
```

### Poster: Build Brief

```bash
~/.claude/skills/.venv/bin/python3 ~/.claude/skills/marketing-design/scripts/poster/search.py --poster-brief --topic "AI Conference" --query "minimal grid"
```

### Poster: Generate Prompt

```bash
~/.claude/skills/.venv/bin/python3 ~/.claude/skills/marketing-design/scripts/poster/generate.py --topic "AI Conference"
~/.claude/skills/.venv/bin/python3 ~/.claude/skills/marketing-design/scripts/poster/generate.py --topic "AI Conference" --query "swiss" --aspect a2
~/.claude/skills/.venv/bin/python3 ~/.claude/skills/marketing-design/scripts/poster/generate.py --topic "AI Conference" --style "Swiss Editorial Grid" --seed 42
```

Pipe stdout into any image-gen model. For series: same `--style`, different `--seed` values (lock identity, vary composition).

### Poster: Rebuild Knowledge Base

```bash
# Vision analysis (resume-safe; needs GEMINI_API_KEY)
~/.claude/skills/.venv/bin/python3 ~/.claude/skills/marketing-design/scripts/poster/analyze.py --input-dir /path/to/posters

# Re-cluster + regenerate CSVs
~/.claude/skills/.venv/bin/python3 ~/.claude/skills/marketing-design/scripts/poster/cluster.py
```

## Social Photos (Built-in)

Multi-platform social image design: HTML/CSS → screenshot export. Uses built-in social templates, brand context from the brief, and Browser/Playwright screenshots.

Load `references/social-photos-design.md` for sizes, templates, best practices.

### Social Photos: Workflow

1. **Orchestrate** — track variants and parallelize independent work when useful
2. **Analyze** — Parse prompt: subject, platforms, style, brand context, content elements
3. **Ideate** — 3-5 concepts and present concise options
4. **Design** — apply brand tokens from the brief; build HTML per idea × size
5. **Export** — Browser or Playwright screenshot at exact px (2x deviceScaleFactor)
6. **Verify** — visually inspect exported designs; fix layout/styling issues and re-export
7. **Report** — Summary to `plans/reports/` with design decisions
8. **Organize** — sort output files and reports under the chosen artifact directory

### Social Photos: Key Sizes

| Platform | Size (px) | Platform | Size (px) |
|----------|-----------|----------|-----------|
| IG Post | 1080×1080 | FB Post | 1200×630 |
| IG Story | 1080×1920 | X Post | 1200×675 |
| IG Carousel | 1080×1350 | LinkedIn | 1200×627 |
| YT Thumb | 1280×720 | Pinterest | 1000×1500 |

## Workflows

### Complete Brand Package

1. **Logo** → `scripts/logo/generate.py` → Generate logo variants
2. **CIP** → `scripts/cip/generate.py --logo ...` → Create deliverable mockups
3. **Presentation** → use `opendesign` to build the pitch deck (HTML)

### New Design System

1. **Brand assets** (this skill) → Define visual direction and generate marks/mockups
2. **HTML artifact** (`vd:opendesign`) → Explore page/deck direction
3. **Implement** (`vd:webdesign`) → Configure Tailwind, shadcn/ui, and frontend screens

## References

| Topic | File |
|-------|------|
| Design Routing | `references/design-routing.md` |
| Logo Design Guide | `references/logo-design.md` |
| Logo Styles | `references/logo-style-guide.md` |
| Logo Colors | `references/logo-color-psychology.md` |
| Logo Prompts | `references/logo-prompt-engineering.md` |
| CIP Design Guide | `references/cip-design.md` |
| CIP Deliverables | `references/cip-deliverable-guide.md` |
| CIP Styles | `references/cip-style-guide.md` |
| CIP Prompts | `references/cip-prompt-engineering.md` |
| Banner Sizes & Styles | `references/banner-sizes-and-styles.md` |
| Social Photos Guide | `references/social-photos-design.md` |
| Icon Design Guide | `references/icon-design.md` |
| Poster Design Guide | `references/poster-design.md` |
| Poster Prompt Engineering | `references/poster-prompt-engineering.md` |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/logo/search.py` | Search logo styles, colors, industries |
| `scripts/logo/generate.py` | Generate logos with Gemini AI |
| `scripts/logo/core.py` | BM25 search engine for logo data |
| `scripts/cip/search.py` | Search CIP deliverables, styles, industries |
| `scripts/cip/generate.py` | Generate CIP mockups with Gemini |
| `scripts/cip/render-html.py` | Render HTML presentation from CIP mockups |
| `scripts/cip/core.py` | BM25 search engine for CIP data |
| `scripts/icon/generate.py` | Generate SVG icons with Gemini 3.1 Pro |
| `scripts/poster/analyze.py` | Vision-extract design tokens from poster images |
| `scripts/poster/cluster.py` | Cluster into 4 CSVs (style/palette/layout/texture) |
| `scripts/poster/search.py` | BM25 search + brief assembly across poster CSVs |
| `scripts/poster/generate.py` | Emit text prompt for any image-gen model |

## Setup

```bash
export GEMINI_API_KEY="your-key"  # https://aistudio.google.com/apikey
pip install google-genai pillow
```

## Integration

**Related skills:** `vd:opendesign`, `vd:webdesign`, `vd:fastreact`, `vd:omnimedia`
