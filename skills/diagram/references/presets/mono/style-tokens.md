# Preset: mono

**Aesthetic:** monochrome line drawing. Pure black on white. No accent color exists. Differentiation through line weight, dash pattern, and label tags. Best for PR-diffable engineering docs, B&W print, technical specs, RFCs.

**Inspiration:** Edward Tufte information design + technical patent drawings + ASCII-diagram traditions. The most legible at small print sizes; survives photocopy.

## Palette

| Role | Hex | WCAG on `--surface` | Use for |
| --- | --- | --- | --- |
| Primary | `#0a0a0a` (near-black) | 19.5:1 (AAA all sizes) | Body text, main borders, default element strokes |
| Accent | `#0a0a0a` | - | Same as primary; use 3.5px border + `[Subject]` label tag instead of color |
| Success | `#0a0a0a` (mono) | - | OK / sync paths. Differentiate via solid + filled arrow + "ok" label. |
| Error | `#0a0a0a` (mono) | - | Failure / retry paths. Differentiate via dotted line + open arrow + "error" label. |
| Surface | `#ffffff` (white) | n/a | Canvas background fill. |
| Muted | `#737373` (neutral-500) | 4.5:1 (AA) | Secondary text, grouping outlines, "[Container: tech]" tags. |

## Subject Highlighting

**No color highlight available.** Use:
1. **3.5px primary border** on the subject (vs 2px on others)
2. A `[Subject]` text tag in monospace below the subject's name
3. Pull the subject visually forward by giving it ~10% more breathing room than peers

## Typography Overrides

None - same Inter + JetBrains Mono. Mono leans on weight contrast: regular for body, bold (not semibold) for service titles.

## CSS-Vars Block

```css
:root {
  --bg: #ffffff;
  --primary: #0a0a0a;
  --accent: #0a0a0a;
  --success: #0a0a0a;
  --error: #0a0a0a;
  --muted: #737373;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0a0a0a;
    --primary: #fafafa;
    --accent: #fafafa;
    --success: #fafafa;
    --error: #fafafa;
    --muted: #a3a3a3;
  }
}
```

## Differentiation Strategies (replaces color coding)

| Distinction | Mono technique |
| --- | --- |
| Internal vs external | 2px solid border vs 1.5px dashed border + `[External]` tag |
| Sync vs async | Solid line + filled arrow vs dashed line + open arrow |
| OK path vs error path | Solid line + "ok" label vs **dotted** line (not dashed) + "error" label |
| Subject vs peer | 3.5px border + `[Subject]` tag vs default 2px |
| Cache vs primary DB | Cylinder with dashed body vs cylinder with solid body |

## Image-Gen Style Phrase

> "pure white background (#ffffff), black line drawing aesthetic (#0a0a0a), no color, all differentiation via line weight (2px primary, 1px secondary), dash pattern (solid sync, dashed async, dotted error), and text labels. Style: technical patent drawing, Tufte information design, photocopy-safe, hand-traceable. No gradients, no fills, no shadows. Inter sans-serif for labels, JetBrains Mono for code."
