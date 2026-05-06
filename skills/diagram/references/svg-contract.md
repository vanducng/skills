# SVG Output Contract

When `--format svg` is used, the LLM must emit raw SVG markup that conforms to this contract.
The orchestrator strips markdown fences and validates that output starts with `<svg`.

## Engines

Two engine paths produce SVG; both must satisfy the Hard Constraints in this file.

- **`--engine free`** (current default for `sequence` and `state-machine`): pure-LLM SVG path. The LLM owns layout AND aesthetics. Implemented in `scripts/openrouter_chat.py::generate_svg`.
- **`--engine skeleton`** (default for `system-architecture`, `data-flow`, `c4-context`, `c4-container`, `er-diagram` once Phase 8 ships): two-pass — pass-1 emits a YAML structural skeleton (see [`skeleton-contract.md`](skeleton-contract.md)); Python computes coordinates; pass-2 paints SVG with coords locked (see [`painter-contract.md`](painter-contract.md)).

## Output Requirements

- Valid **SVG 1.1**.
- Self-contained — no embedded raster images, no external font loads, no data: URLs.
- Must include `viewBox` so it scales cleanly.
- No `<script>` tags. No `<foreignObject>`. No event handlers (`onclick`, etc.).

## Hard Constraints (validated automatically — violations trigger an extra revise pass)

1. **XML well-formedness.** The SVG must parse as strict XML.
   - Escape `&` as `&amp;` in *every* `<text>` body. Even labels like `CLI & Subsystems` must be `CLI &amp; Subsystems`.
   - Self-close empty elements (`<rect ... />`, not `<rect ...>`).
   - Quote every attribute value.
2. **No CSS variables in presentation attributes.** `var(--x)` only resolves inside `<style>` rules — *not* in inline attributes when the SVG loads via `<img>`. Forbidden:
   ```svg
   <path fill="var(--primary)"/>           <!-- BROKEN -->
   <rect stroke="var(--accent)"/>          <!-- BROKEN -->
   ```
   Always use a class instead, defined in the embedded `<style>`:
   ```svg
   <style>
     .arrow-fill   { fill: var(--primary); }
     .accent-rect  { stroke: var(--accent); }
   </style>
   <path class="arrow-fill"/>
   <rect class="accent-rect"/>
   ```
   This rule applies **inside `<defs>` and `<marker>` blocks** as well — markers must use class-based fills, not inline `var()`.
3. **No node-rect overlaps.** Two `<rect>` elements with class `service`, `datastore`, `external-system`, `cache`, `queue`, `process`, `decision`, `state`, `entity`, or `actor` must not have intersecting axis-aligned bounding boxes. Layer envelopes (`class="boundary"`) and arrow-label occluders (`class="arrow-label"`) are exempt.
4. **Every visible element is anchored.** No floating dots, dashes, or stray glyphs. If you draw it, it lives inside a `<g>` parent and is connected to the diagram's semantics.
5. **Layer-boundary headers clear their children.** Boundary header text (e.g. `<text class="muted">User Input</text>`) must sit at least 12 px above the topmost child node. Putting the header inside the rect's top-left and overlapping the first child node is the most common defect — don't do it.

## Required Root Attributes

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" width="100%" height="auto">
```

Default canvas: `1600 × 900` (16:9). Adjust `viewBox` only if the layout demands a different aspect.

## Layer Convention

Wrap elements in `<g>` groups so users can hand-edit later:

```xml
<g class="layer-boundaries"> ... </g>
<g class="layer-services"> ... </g>
<g class="layer-connections"> ... </g>
<g class="layer-labels"> ... </g>
```

Order matters: boundaries draw first (back), labels last (front).

## Class Names (map to style-tokens.md shapes)

| Class | Element | Shape from style-tokens |
| --- | --- | --- |
| `.service` | Rounded rectangle | Service / app / process |
| `.datastore` | Cylinder path | Database / datastore |
| `.queue` | Horizontal pipe rectangle | Queue / message broker |
| `.cache` | Cylinder with dashed stroke | Cache (distinguishes from primary DB) |
| `.user-actor` | Stick figure (circle + path) | User / actor |
| `.external-system` | Dashed-border rounded rectangle | External system |
| `.boundary` | Large rounded rectangle, no fill | Bounded context |
| `.connection-sync` | Path + filled arrowhead marker | 2px solid |
| `.connection-async` | Path + open arrowhead marker, dashed | 2px dashed |
| `.accent-stroke` | Apply alongside `.service` / `.connection-sync` | Highlights the diagram's subject |
| `.success-stroke` | Apply alongside connection classes | OK / sync path |
| `.error-stroke` | Apply alongside connection classes | Failure / retry path |

## Theming via CSS Variables (REQUIRED)

Emit ONE `<style>` block at the top of the SVG. Use CSS variables, not inline `fill`/`stroke` attributes. This unlocks `prefers-color-scheme` adaptation and matches the pattern used by D2, Mermaid, and other modern diagram tools.

**Hard rule:** never set inline `fill` or `stroke` on themed elements. Use `class="..."` and let the `<style>` block resolve to the theme variable. Inline styles override the theme and break dark-mode adaptation.

**The CSS-vars block (`:root` + `@media`) MUST come from the active preset's `style-tokens.md`.** Each preset (`warm`, `mono`, `pastel`, `cyberpunk`) provides a ready-to-paste block. Do NOT improvise hex values — paste verbatim from the preset.

After the preset's CSS-vars block, append the following class definitions (these are theme-agnostic; they reference the variables the preset defined):

```xml
<style><![CDATA[
  /* :root block from active preset's style-tokens.md goes HERE */

  .canvas { fill: var(--bg); }
  .service { fill: var(--bg); stroke: var(--primary); stroke-width: 2; }
  .datastore { fill: var(--bg); stroke: var(--primary); stroke-width: 2; }
  .external-system { fill: var(--bg); stroke: var(--primary); stroke-width: 1.5; stroke-dasharray: 6 4; }
  .cache { fill: var(--bg); stroke: var(--primary); stroke-width: 2; stroke-dasharray: 4 2; }
  .queue { fill: var(--bg); stroke: var(--primary); stroke-width: 2; }
  .boundary { fill: none; stroke: var(--muted); stroke-width: 1; }
  .connection-sync { stroke: var(--primary); stroke-width: 2; fill: none; }
  .connection-async { stroke: var(--primary); stroke-width: 2; fill: none; stroke-dasharray: 6 4; }
  .connection-error { stroke: var(--primary); stroke-width: 2; fill: none; stroke-dasharray: 2 2; }
  .accent-stroke { stroke: var(--accent); stroke-width: 2.5; }
  .success-stroke { stroke: var(--success); }
  .error-stroke { stroke: var(--error); }
  text { font-family: "Inter", ui-sans-serif, system-ui, sans-serif; fill: var(--primary); }
  text.muted { fill: var(--muted); font-style: italic; }
  text.code { font-family: "JetBrains Mono", "Geist Mono", ui-monospace, monospace; }
]]></style>
<rect class="canvas" width="100%" height="100%"/>
```

The `mono` preset uses a slightly different `.connection-error` (dotted, not dashed) — this is already encoded in the class above (`stroke-dasharray: 2 2`).

The `<![CDATA[ ... ]]>` wrapper is REQUIRED — otherwise `<` and `>` inside selectors break SVG XML parsing.

**GitHub README caveat:** GitHub strips `@media (prefers-color-scheme: dark)` from inline SVG. For READMEs, plan to emit two files (`light.svg` + `dark.svg`) wrapped in `<picture>` — landing in v0.4. For now, GitHub renders the light branch correctly.

**Safari caveat:** when an SVG is embedded as `<img src="diagram.svg">`, Safari does not propagate `prefers-color-scheme` into the SVG buffer. Inline `<svg>` works in all browsers including Safari.

## Hard Rules (validator-enforced)

- **NO** `<script>` tags
- **NO** `<foreignObject>`
- **NO** `data:` URLs
- **NO** event handler attributes (`on*`)
- Output MUST start with `<svg` (after fence strip)
- Output MUST end with `</svg>`

## Layout Rules (HARD — most diagram failures come from breaking these)

### 1. Pick a canvas + grid before placing anything

Default canvas `1600 × 900`. For diagrams with ≥3 boundary regions OR ≥10 boxes, use `1600 × 1200` and declare it in `viewBox`.

Mentally divide the canvas into an **8-column × 6-row grid of 200×150px cells** (or 200×200 for the taller canvas). Every box snaps to cell boundaries. Every gutter between cells is at least 40px tall/wide and is reserved for connection routing — **no element ever lives in a gutter**.

### 2. Boundary regions are NON-OVERLAPPING

If you draw a `.boundary` rect at `(x1,y1)–(x2,y2)`, no other `.boundary` rect may share any pixel with it. Boundaries tile the canvas like floor tiles — never stack. Lay them out as a strict **N×1 row grid**, **1×N column grid**, or **2×2 quadrant grid**. Never freehand.

For a 4-section layout (e.g. "Upstream / Core / State / Pipeline"), the safe split is a 2×2 grid:

```
+----- Upstream (x:40–800, y:40–420) -----+ +----- State (x:840–1560, y:40–420) -----+
|                                          | |                                          |
+------------------------------------------+ +------------------------------------------+
+----- Core (x:40–1560, y:460–820) ----------------------------------------------------+
|                                                                                        |
+----------------------------------------------------------------------------------------+
+----- Pipeline (x:40–1560, y:860–1160) -----------------------------------------------+
|                                                                                        |
+----------------------------------------------------------------------------------------+
```

If a "right column" boundary would clip a "center" boundary, you have **picked the wrong layout** — restart with a different split.

### 3. Boundary captions sit INSIDE the boundary

```xml
<rect class="boundary" x="40" y="40" width="760" height="380" rx="8"/>
<text class="muted" x="60" y="68">Upstream: GitHub repos</text>   <!-- y = boundary.y + 28, INSIDE -->
```

Never `y < boundary.y` — the caption above-the-box pattern collides with whatever sits above. Always 24–32px below the boundary's top edge.

### 4. Boxes have ≥40px breathing room from boundary edges + ≥40px from each other

Inside a boundary at `(40,40,800,420)` (i.e. width 760, height 380, with a 28px caption band), the usable interior is `(60,80)–(780,400)`. Every child box stays inside that interior.

### 5. Labels sit INSIDE their parent box, padded ≥12px from edges

A `<text>` for a box at `x=100, y=200, w=160, h=80` must satisfy `112 ≤ text.x ≤ 248` and `212 ≤ text.y ≤ 268` — no labels riding on the border, no labels spilling outside.

For multi-line labels, stack vertically with `dy="1.4em"` on subsequent `<tspan>` rather than separate `<text>` elements with hand-computed y values — easier to keep aligned.

### 6. Connections route ORTHOGONALLY through gutters

A connection between two boxes in **different** boundary regions or different rows MUST be drawn as a polyline with right-angle bends, routed through the gutter between regions. Never a straight diagonal that pierces a third box.

```xml
<!-- Box A at (100,100,160,80), Box B at (1100,500,160,80), divider gutter at y=420 -->
<path class="connection-sync"
      d="M 260 140  L 700 140  L 700 460  L 1100 540"
      marker-end="url(#arrow-filled)"/>
<!--    │       │    │       │    │       │    │       └── enter B at left edge
        │       │    │       │    │       │    └────────── reach B's column at gutter-y
        │       │    │       │    │       └─────────────── travel down through gutter
        │       │    │       │    └─────────────────────── reach gutter-y (between rows)
        │       │    │       └──────────────────────────── travel right
        │       │    └──────────────────────────────────── still on A's row
        │       └─────────────────────────────────────── enter the routing channel
        └─────────────────────────────────────────────── leave A from right edge -->
```

Connections between **boxes in the same row, no third box between them** may be straight horizontal lines.

Anchor points: **right-edge mid-y** for outgoing, **left-edge mid-y** for incoming, on horizontal flows. Top/bottom mid-x for vertical flows. Never anchor to corners.

### 7. Bidirectional connections — ONE path, two markers

To show a two-way flow, emit **a single path with both `marker-start` and `marker-end`** — never two overlapping paths.

```xml
<!-- WRONG — two overlapping arrows render as one -->
<path class="connection-sync" d="M 100 200 L 400 200" marker-end="url(#arrow-filled)"/>
<path class="connection-sync" d="M 400 200 L 100 200" marker-end="url(#arrow-filled)"/>

<!-- RIGHT — one path, double-headed -->
<path class="connection-sync" d="M 100 200 L 400 200"
      marker-start="url(#arrow-filled)" marker-end="url(#arrow-filled)"/>
```

If the two directions need different stroke styles (e.g. one solid + one dashed), draw them as **two paths offset by ≥16px perpendicular** to the flow direction, not on the same line.

### 8. Arrow labels: ON the arrow with white-background occlusion

Arrow labels sit **directly on top of** the arrow path (centered on a straight segment), with a `<rect>` white-fill behind them to occlude the line.

**Hard rule:** the occluder `<rect>` MUST geometrically overlap the path. If the path runs horizontally at `y=440`, the rect's `y` range must include `440` (e.g. `y="431"` `height="18"` covers `y=431..449`). A rect at `y="415", height="18"` covering `y=415..433` does NOT occlude a path at `y=440` and is **wrong** — the user sees a floating label and the line passing untouched beneath.

For a horizontal segment at `y=Y`: rect `y = Y - 9`, height ≥ 18, text baseline `y = Y + 4`.
For a vertical segment at `x=X`: rect `x = X - W/2`, width = label width + 16, text `x = X`.

```xml
<!-- Path runs horizontally at y=440. Rect must straddle y=440. -->
<path class="connection-sync" d="M 930 440 L 160 440" marker-end="url(#arrow-filled)"/>
<g class="arrow-label">
  <rect x="500" y="431" width="80" height="18" fill="var(--bg)"/>
  <text x="540" y="445" text-anchor="middle" class="code">manifest</text>
</g>
```

**Every label must label exactly one connection.** Floating "label-like" text (e.g. a word in empty whitespace that doesn't sit on any path) is forbidden — drop it instead of placing it.

### 9. Pre-flight checklist (the LLM MUST mentally walk through before emitting)

- [ ] All boundary rects tile the canvas — none overlap any other boundary
- [ ] Each box sits entirely inside its boundary, with ≥40px padding from boundary edges
- [ ] Each text node sits entirely inside its parent box (≥12px padding) OR in a gutter explicitly reserved for arrow labels
- [ ] Each cross-region connection uses orthogonal routing (right-angle polyline)
- [ ] No bidirectional pair drawn as two same-line paths
- [ ] Arrow labels have white-fill rect behind them
- [ ] Boundary caption is INSIDE the boundary, never above it

## Markers (arrowheads)

Define once at top of `<defs>`, reuse via `marker-end`:

```xml
<defs>
  <marker id="arrow-filled" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="var(--primary)"/>
  </marker>
  <marker id="arrow-open" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10" fill="none" stroke="var(--primary)" stroke-width="1.5"/>
  </marker>
</defs>
```
