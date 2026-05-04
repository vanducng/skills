# Preset: pastel

**Aesthetic:** soft slate-50 surface, sky-blue accent, low-saturation overall. Reads as "polished but approachable". Best for PowerPoint slides, executive presentations, customer-facing docs, marketing one-pagers.

**Inspiration:** modern SaaS marketing (Linear, Notion, Stripe Atlas) — pastel surface, restrained accent, plenty of breathing room.

## Palette

| Role | Hex | WCAG on `--surface` | Use for |
| --- | --- | --- | --- |
| Primary | `#1e293b` (slate-800) | 13.7:1 (AAA all sizes) | Body text, main borders, default element strokes |
| Accent | `#0284c7` (sky-600) | 4.5:1 (AA all sizes) | Stroke highlight on the diagram's *subject*. Body text OK if ≥14pt. |
| Success | `#009E73` (Okabe-Ito Bluish Green) | 3.5:1 (AA Large + UI) | OK / sync paths. Pair with solid arrow + "ok" label. |
| Error | `#D55E00` (Okabe-Ito Vermilion) | 4.6:1 (AA all sizes) | Failure / retry paths. Pair with dashed arrow + "error" label. |
| Surface | `#f8fafc` (slate-50) | n/a | Canvas background fill. |
| Muted | `#64748b` (slate-500) | 4.6:1 (AA) | Secondary text, grouping outlines, "[Container: tech]" tags. |

## Subject Highlighting

Use accent (#0284c7) at 2.5px stroke on the subject's border. No glow. Optional: tint the subject's fill with `color-mix(in srgb, var(--accent) 8%, var(--bg))` for a faint sky-blue wash.

## Typography Overrides

None. Inter + JetBrains Mono.

## CSS-Vars Block

```css
:root {
  --bg: #f8fafc;
  --primary: #1e293b;
  --accent: #0284c7;
  --success: #009E73;
  --error: #D55E00;
  --muted: #64748b;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f172a;
    --primary: #f1f5f9;
    --accent: #38bdf8;
    --success: #34d399;
    --error: #fb7185;
    --muted: #94a3b8;
  }
}
```

## Image-Gen Style Phrase

> "soft slate-50 background (#f8fafc), slate-800 primary borders (#1e293b), sky-blue accent (#0284c7) on the subject, Okabe-Ito bluish-green for ok paths and vermilion for error paths, slate-500 muted for grouping. Style: modern SaaS marketing aesthetic (Linear, Notion vibes), restrained, polished, professional, plenty of whitespace, low-saturation overall. Inter sans-serif for labels, JetBrains Mono for code."
