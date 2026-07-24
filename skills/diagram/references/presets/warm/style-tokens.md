# Preset: warm

**Aesthetic:** warm cream surface, deep slate primary, amber accent. Calm, technical-illustration feel. The default. Best for pitch decks, design docs, blog hero images, internal architecture write-ups.

**Inspiration:** Stripe-press / Anthropic / vintage technical illustration aesthetics. Warm minimalism - clean layouts with tactile, slightly nostalgic palette.

## Palette

| Role | Hex | WCAG on `--surface` | Use for |
| --- | --- | --- | --- |
| Primary | `#1e293b` (deep slate) | 13.5:1 (AAA all sizes) | Body text, main borders, default element strokes |
| Accent | `#d97706` (warm amber) | 3.2:1 (AA Large + UI) | Stroke highlight on the diagram's *subject*. NOT for body text. |
| Success | `#009E73` (Okabe-Ito Bluish Green) | 3.5:1 (AA Large + UI) | OK / sync paths. NOT for body text. Pair with solid arrow + label. |
| Error | `#D55E00` (Okabe-Ito Vermilion) | 4.6:1 (AA all sizes) | Failure / retry paths. Pair with dashed arrow + "error" label. |
| Surface | `#faf8f3` (cream) | n/a | Canvas background fill. |
| Muted | `#57534e` (warm-700) | 7.4:1 (AAA) | Secondary text, grouping outlines, "[Container: tech]" tags. |

The success + error pair is the [Okabe-Ito palette](https://easystats.github.io/see/reference/scale_color_okabeito.html), validated for protanopia / deuteranopia / tritanopia.

## Subject Highlighting

Use accent (#d97706) at 2.5px stroke on the subject's border. No glow, no shadow.

## Typography Overrides

None. Uses the foundations defaults: Inter + JetBrains Mono.

## CSS-Vars Block (paste into SVG `<style>`)

```css
:root {
  --bg: #faf8f3;
  --primary: #1e293b;
  --accent: #d97706;
  --success: #009E73;
  --error: #D55E00;
  --muted: #57534e;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f172a;
    --primary: #e2e8f0;
    --accent: #fbbf24;
    --success: #34d399;
    --error: #f87171;
    --muted: #94a3b8;
  }
}
```

## Image-Gen Style Phrase

When refining the image-gen prompt, embed this aesthetic phrase verbatim:

> "warm cream background (#faf8f3), deep slate borders (#1e293b), warm amber (#d97706) accent on the subject, muted warm-gray (#57534e) for grouping outlines, calm technical illustration aesthetic, isometric-flat hybrid, clean lines, no gradients beyond subtle ambient shading"
