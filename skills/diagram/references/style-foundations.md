# Style Foundations - Theme-Agnostic Rules

These rules are **invariant across all presets** (`warm`, `mono`, `pastel`, `cyberpunk`).
Only the palette and aesthetic feel change per preset. Iconography, typography defaults, line weights, and arrowhead semantics stay identical.

## Typography Defaults

- **Sans (labels)**: `Inter`, fall back to `ui-sans-serif`, then `system-ui`. Single weight (regular) for body, semibold for service titles. Inter pairs cleanly with JetBrains Mono.
- **Mono (code/data fields)**: `JetBrains Mono`, fall back to `Geist Mono`, then `ui-monospace`. Use for column names, queue topics, env keys, protocol tags `[JSON/HTTPS]`.
- **Min legible size at 1920px wide**: ≈14pt equivalent. If the diagram has >12 labels, drop to 12pt AND set the canvas to `viewBox="0 0 1920 1080"` to recover headroom.
- **Italic muted** is reserved for the `[Container: <tech>]` C4 tag and the optional 1-line tech-stack subtitle under a service name. No other italic usage.
- Never mix more than 2 type families.

A preset MAY override the sans/mono families (cyberpunk uses Geist Mono everywhere for vibe). Italics rule and size rules never change.

## Iconography Vocabulary (canonical shapes)

These are the ONLY shapes. Reuse across every diagram type so the visual grammar stays consistent across presets.

| Element | Shape | Notes |
| --- | --- | --- |
| Service / app / process | Rounded rectangle (corner radius ~8px), 2px primary border | Title at top, optional 1-line tech stack in muted italic below |
| Database / datastore | Cylinder (top ellipse + side rectangle) | Label inside the cylinder body |
| Queue / message broker | Horizontal pipe (rectangle with rounded short ends) | Topic name inside |
| Cache | Cylinder, dashed top ellipse | Distinguishes from primary DB |
| User / actor | Stick figure circle (head + simplified body) | Above their entry-point arrow |
| External system | Rounded rectangle, 1px dashed primary border | Visually weaker than internal services |
| Boundary / bounded context | Large rounded rectangle, 1px muted border, no fill | Used for grouping; never overlaps |

## Line Weight

- **2px** - primary connection arrows (the user-visible flow)
- **1px** - grouping outlines, boundary boxes, subordinate connections
- **Dashed** - async / optional / retry flows. Use the same color as the equivalent solid line.

## Arrowheads

- Solid filled triangle for sync calls / data flow.
- Open (unfilled) triangle for async / fire-and-forget.
- Double-headed arrow only for explicit bidirectional links (rare; usually two unidirectional arrows are clearer).

## Color Density

- **Maximum 3-5 colors per diagram.** More than 5 = visual noise.
- **The accent color highlights AT MOST one "subject" per diagram.** More than one and the highlight loses meaning.
- Success / error colors are reserved for **explicit ok / error semantics** - never decorative.

## Subject Highlighting Across Presets

Each preset specifies HOW the subject is highlighted because the technique varies with palette:

| Preset | Subject highlight technique |
| --- | --- |
| `warm` / `pastel` | Accent-color stroke at 2.5px on the subject's border. |
| `mono` | No accent color exists; use 3.5px primary border + a `[Subject]` label tag in monospace. |
| `cyberpunk` | Accent-color stroke at 2.5px PLUS a subtle outer glow filter on the subject. |

Type refs say "highlight the subject per the active preset's subject-highlighting rule" - they do NOT prescribe a technique inline.
