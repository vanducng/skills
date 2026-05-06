# Painter Contract — pass-2 (SVG paint with locked coordinates)

You paint, you don't lay out.

You receive a fully laid-out skeleton — every node bbox, every edge waypoint, every label coordinate is **locked**. Your job is to render the diagram as SVG using the active preset's style tokens. Aesthetic distinctness across presets (warm vs cyberpunk must look different) is the explicit goal.

## What is locked (do not change)

For every element in the skeleton:
- `bbox.x`, `bbox.y`, `bbox.w`, `bbox.h`

For every edge:
- Each `waypoints` (x, y) tuple
- The `label_xy` (if present)

For every note:
- The `xy` anchor

You may NOT move any of these by more than 5%. The validator rejects drift > 5%; rejection triggers a revise pass that will see your output again with stronger language. Save the round-trip — get coords right the first time.

## What is yours (paint freely)

- **Colors** — pull from the active preset's CSS variables (`var(--bg)`, `var(--primary)`, `var(--accent)`, etc.).
- **Line weights** — `stroke-width` for connections, borders, accents.
- **Marker shapes** — arrowhead style (filled vs open vs custom), size.
- **Dash patterns** — for async/error edges, dashed-border externals.
- **Label font weights** — bold the subject, mute notes.
- **Decorative ornaments** — sparingly. The cyberpunk preset can add neon glow filters; warm can add subtle drop shadows; mono stays flat.
- **Accent placement** on the `subject: true` element (heavier border, accent color).
- **Layer ordering** of `<g>` groups (boundaries back, labels front).
- **Per-kind shape recipes** (see table below).
- **Embedded `<style>` block** including the `:root` palette and `@media (prefers-color-scheme: dark)` swap from the preset.

## Required SVG output structure

1. Root `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas.w} {canvas.h}" width="100%" height="auto">`.
2. ONE `<style><![CDATA[ ... ]]></style>` block containing the preset's `:root` block, the `@media (prefers-color-scheme: dark)` swap, and class rules that map element kinds to fills/strokes.
3. `<defs>` with arrow markers (filled, open, etc.) — colors via class, NEVER inline `var()` in presentation attrs.
4. `<rect class="canvas" width="100%" height="100%"/>` background.
5. Layer `<g>` groups in this order (back → front):
   - `<g class="layer-boundaries">` — group/lane envelopes
   - `<g class="layer-services">` — node bodies (rects, cylinders, actors)
   - `<g class="layer-connections">` — edges
   - `<g class="layer-labels">` — node labels, edge labels, notes
6. Every node element MUST have `data-name="{element.name}"` so the validator can match by name.

## Hard constraints (must satisfy — copied from svg-contract.md)

1. **XML well-formedness.** Escape `&` as `&amp;` in every `<text>`. Self-close empty elements. Quote every attribute value.
2. **No CSS variables in presentation attributes.** `var(--x)` only resolves inside `<style>` rules and inline `style="..."` — NOT in `fill="var(--x)"` attributes when the SVG loads via `<img>`. Use classes.
3. **No node-rect overlaps.** Two element rects must not have intersecting AABBs. The supplied coords are non-overlapping by construction; if you preserve them, this holds.
4. **Every visible element is anchored** to the diagram's semantics.

## Coordinate-fidelity rule

For every element listed in the skeleton, emit ONE SVG element representing it with `data-name="{element.name}"`. The validator reads its bbox and compares to the supplied `bbox.x/y/w/h` (5% per-axis tolerance, 4 px floor).

- For `<rect>`: read `x`, `y`, `width`, `height` directly. Match the supplied bbox.
- For `<ellipse>`: matched as `(cx-rx, cy-ry, 2*rx, 2*ry)`.
- For `<g>` composite shapes (e.g. actor = circle + body lines): emit a `<g data-name="..." data-bbox="x,y,w,h">` outer wrapper so the validator can read the bbox directly. The validator otherwise unions children — keep children inside the supplied bbox or emit `data-bbox`.
- For `<path>` (e.g. cylinder for datastore): you MUST emit `data-bbox="x,y,w,h"` (the four numbers from the supplied coords). Skipping `data-bbox` on a path element will be treated as a missing element by the drift detector.

## Per-kind shape recipes

| `kind` | SVG primitive | Notes |
| --- | --- | --- |
| `service` | `<rect rx="8">` rounded | The most common kind; bold border for `subject: true`. |
| `process` | `<rect rx="8">` rounded | Same shape as service; semantic distinction in label. |
| `external-system` | `<rect rx="8" stroke-dasharray="6 4">` | Dashed border (C4 convention). |
| `datastore` | `<g data-name="..." data-bbox="x,y,w,h">` containing 3-path cylinder (top ellipse + body + bottom ellipse). |
| `cache` | `<rect stroke-dasharray="4 2">` dashed-border rect — distinguishes from primary DB. |
| `queue` | `<rect rx="20">` heavily-rounded "pipe" rectangle. |
| `actor` | `<g data-name="..." data-bbox="x,y,w,h">` circle + stick lines centered in bbox. |
| `decision` | `<polygon>` diamond fitted to bbox; emit `data-bbox` since polygon has no width/height attrs. |
| `state` | `<rect rx="40">` pill shape. |
| `entity` | `<rect>` with internal divider lines; for ER. |

For label text inside a node: place `<text>` at the bbox center with `text-anchor="middle"` and `dominant-baseline="middle"`. Multi-line via `<tspan dy="1.4em">`.

## What NOT to invent

- Don't add elements not in the skeleton.
- Don't add edges not in the skeleton.
- Don't reposition labels — use `label_xy` from the skeleton verbatim (rounded to 1 px).
- Don't change `data-name` values.
- Don't omit any element from the skeleton — the validator checks every name exists in the SVG.
- Don't emit pixel coordinates that disagree with the supplied bbox by more than 5%.

## Response format

Emit ONLY the final SVG. No markdown fences, no preamble, no commentary. The first character is `<`.
