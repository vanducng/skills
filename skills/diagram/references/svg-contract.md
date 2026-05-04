# SVG Output Contract

When `--format svg` is used, the LLM must emit raw SVG markup that conforms to this contract.
The orchestrator strips markdown fences and validates that output starts with `<svg`.

## Output Requirements

- Valid **SVG 1.1**.
- Self-contained — no embedded raster images, no external font loads, no data: URLs.
- Must include `viewBox` so it scales cleanly.
- No `<script>` tags. No `<foreignObject>`. No event handlers (`onclick`, etc.).

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
