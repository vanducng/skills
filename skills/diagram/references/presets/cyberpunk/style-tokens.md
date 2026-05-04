# Preset: cyberpunk

**Aesthetic:** dark canvas, neon cyan accent, holographic glow. High-impact, talk-stage energy. Best for conference slides, demo videos, dev-tool launch announcements, OG/social-share images.

**Inspiration:** Vercel ship-week graphics, Cloudflare Workers landing pages, Berkeley Mono on dark, Apollo / Linear keynote slides. NOT for sustained reading — the dark surface eye-fatigues over time.

## Palette

| Role | Hex | WCAG on `--surface` | Use for |
| --- | --- | --- | --- |
| Primary | `#e2e8f0` (slate-200) | 14.5:1 (AAA all sizes) | Body text, main borders, default element strokes |
| Accent | `#22d3ee` (cyan-400) | 7.8:1 (AAA all sizes) | Stroke highlight + glow on the diagram's *subject*. |
| Success | `#34d399` (emerald-400) | 8.6:1 (AAA all sizes) | OK / sync paths. Pair with solid arrow + "ok" label. |
| Error | `#fb7185` (rose-400) | 5.9:1 (AAA Large + AA body) | Failure / retry paths. Pair with dashed arrow + "error" label. |
| Surface | `#0a0e1a` (near-black indigo) | n/a | Canvas background fill. |
| Muted | `#94a3b8` (slate-400) | 6.6:1 (AAA Large + AA body) | Secondary text, grouping outlines, "[Container: tech]" tags. |

Brightness inverted vs warm/pastel. Hexes chosen so all roles still pass WCAG AA on the dark surface.

## Subject Highlighting

Use accent (#22d3ee) at 2.5px stroke PLUS a subtle outer glow filter (SVG `feGaussianBlur` with stdDeviation=4 + `feMerge`). The glow is the differentiator — just stroke alone reads less "cyberpunk", more "blue accent".

```xml
<filter id="glow-accent" x="-50%" y="-50%" width="200%" height="200%">
  <feGaussianBlur stdDeviation="4" result="blur"/>
  <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
```

Apply via `filter="url(#glow-accent)"` on the subject element.

## Typography Overrides

- **Sans (labels)**: keep `Inter` for legibility.
- **Mono (code/data fields)**: prefer `Geist Mono` first, then `JetBrains Mono`, then `ui-monospace`. Geist Mono leans more contemporary/synthetic for the cyberpunk feel.
- Optional: bump body weight from regular to `400 → 500` for slightly bolder rendering against the dark surface.

## CSS-Vars Block

```css
:root {
  --bg: #0a0e1a;
  --primary: #e2e8f0;
  --accent: #22d3ee;
  --success: #34d399;
  --error: #fb7185;
  --muted: #94a3b8;
}
@media (prefers-color-scheme: light) {
  :root {
    --bg: #f8fafc;
    --primary: #0f172a;
    --accent: #0891b2;
    --success: #059669;
    --error: #e11d48;
    --muted: #475569;
  }
}
```

Note the inverted media query: cyberpunk's **default** is dark; light mode is the fallback. This ensures cyberpunk stays cyberpunk regardless of viewer's OS theme — but provides a usable light fallback for people who absolutely need it (printing, projector compatibility).

## Image-Gen Style Phrase

> "dark near-black background (#0a0e1a), light slate-200 primary borders (#e2e8f0), neon cyan-400 accent (#22d3ee) with a soft outer glow on the subject, emerald-400 for ok paths and rose-400 for error paths, slate-400 muted for grouping. Style: cyberpunk technical illustration, Vercel ship-week aesthetic, Cloudflare Workers vibe, high-energy keynote slide, subtle holographic glow on accents, Inter sans-serif for labels, Geist Mono for code, no gradients on body fills but accent-element glows are encouraged."
