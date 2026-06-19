# Design Routing Guide

Use this guide to route design work between the local skills in this catalog.

## Local Skill Map

| Need | Route | Notes |
| --- | --- | --- |
| Logo, CIP mockups, banners, social images, SVG icons, posters | `vd:marketing-design` | Use the built-in modules in this skill. |
| Static HTML pages, decks, repo banners, email/doc artifacts | `vd:opendesign` | Produces self-contained HTML/CSS artifacts. |
| Frontend UI, shadcn/Tailwind components, responsive app screens | `vd:uiuxdesign` | Design/build/review/test live frontend surfaces. |
| Full-stack FastAPI + React app scaffold | `vd:fastreact` | Runs mockup-first, then ports design to app code. |
| Multimodal extraction, OCR, transcription, model routing | `vd:omnimedia` | Use when media analysis or model orchestration is the task. |

## Built-In Modules

| Module | Use For | Reference |
| --- | --- | --- |
| Logo | Logo concepts, style search, color/industry guidance | `logo-design.md` |
| CIP | Corporate identity deliverables and mockups | `cip-design.md` |
| Banner | Social, ad, web, and print banners | `banner-sizes-and-styles.md` |
| Social Photos | Platform-specific social graphics | `social-photos-design.md` |
| Icon | SVG icons and icon sets | `icon-design.md` |
| Poster | Event/editorial/marketing poster prompts | `poster-design.md` |

## Routing By Request

| Request | Route |
| --- | --- |
| "Create a logo for my brand" | Logo module |
| "Generate business card mockups" | CIP module |
| "Design a Facebook cover" | Banner module |
| "Create ad banners for Google" | Banner module |
| "Make a website hero banner image" | Banner module |
| "Generate a settings icon" | Icon module |
| "Create a pitch deck" | `vd:opendesign` |
| "Design a dashboard page" | `vd:opendesign` for mockup, `vd:uiuxdesign` for app implementation |
| "Build this in React" | `vd:uiuxdesign` or `vd:fastreact` |

## Multi-Skill Workflows

### Complete Brand Package

1. Logo module: generate mark variants.
2. CIP module: create deliverable mockups from the selected mark.
3. `vd:opendesign`: build the pitch deck or static brand page.

### New Web App

1. `vd:marketing-design`: generate logo and core visual assets.
2. `vd:opendesign`: produce HTML mockups and theme direction.
3. `vd:uiuxdesign` or `vd:fastreact`: implement the UI/app.

### Campaign Assets

1. Logo/CIP modules when the campaign needs brand assets.
2. Banner or Social Photos module for platform-specific graphics.
3. `vd:opendesign` for the campaign landing/deck artifact.

## Rule

Do not route to old source skill names. If the request needs a capability outside this file, use the local `vd:*` skill ID that is installed in this repo.
