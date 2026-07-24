# Design Quality Reference

Use this reference for UI design, UX review, visual polish, accessibility, responsive layout, forms, charts, dashboard work, and the design-quality scoring loop.

> Aesthetic and anti-slop principles below are distilled/adapted from claudekit's `frontend-design` and `ui-ux-pro-max` skills, in this skill's own voice.

## Aesthetic Direction

Commit to a point of view before coding. Intentionality over intensity - refined minimalism and bold maximalism both work when executed deliberately; a vague middle never does.

- **Purpose:** what problem the interface solves and who uses it under what pressure.
- **Tone:** pick one and hold it (minimal, editorial, brutalist, luxury, playful, industrial, retro-futuristic…). Don't converge on the same look every time; vary theme, type, and density across designs.
- **Differentiation:** the one thing someone remembers. Match code complexity to the vision - maximalism needs elaborate motion/effects, minimalism needs restraint and precise spacing.

## Aesthetics

- **Typography:** distinctive, characterful fonts. Avoid Inter/Roboto/Arial/system defaults and overused Space Grotesk. Pair a display font with a refined body font; use 500/600 weights for subtle hierarchy; `text-wrap: balance`/`pretty` to kill orphans. Reserve serifs for editorial, not data UIs.
- **Color / theme:** cohesive dominant color with one considered accent - dominant-plus-accent beats timid even palettes. Define semantic CSS variables; stick to one gray family; desaturate (no saturation > ~80%); off-black (`#0a0a0a`/Zinc-950), never pure `#000`.
- **Motion:** high-impact moments over scattered micro-interactions - one well-orchestrated staggered load reveal delights more than perpetual fidgeting. CSS-first; transform/opacity; spring/custom cubic-bezier over default ease; restraint.
- **Spatial composition:** asymmetry, overlap, grid-breaking, generous negative space OR controlled density - deliberately, not by accident.
- **Backgrounds / depth:** atmosphere over flat fills where the domain allows - subtle noise/grain, gradient mesh, layered transparency, tinted shadows. Keep app/dashboard surfaces calm; save atmosphere for marketing/editorial.

## Anti-Slop: Forbidden AI Defaults

LLM fingerprints - avoid unless the user explicitly asks or the domain genuinely calls for it.

- **Type:** no Inter / Roboto / Arial / system fonts. Input `font-size ≥ 16px` (smaller triggers mobile zoom).
- **Color:** no purple/blue gradient-on-white (the #1 tell); no pure `#000`; no oversaturated accents; no gradient text on headers or body.
- **Layout:** no 3-column equal-card feature rows; no centered hero + centered H1 at high variance (split-screen / left-align instead); no `h-screen` - use `min-h-[100dvh]`; constrain to a max-width.
- **Content:** no "John Doe" / "Acme" / "Nexus"; no round fake numbers (50%, $100.00) - use organic values (47.2%, $99); no AI clichés ("Elevate", "Seamless", "Unleash", "Next-Gen", "Delve"); no Lorem Ipsum; sentence case, not Title Case Everywhere; no "Oops!" errors.
- **Effects:** no neon/outer glows, no custom cursors, no gradient text on headers. Tinted inner shadows instead.
- **Components:** no default unstyled shadcn; no Lucide-only icons at high density (try Phosphor/Heroicons/custom); no generic border+shadow+white card at high density - use spacing/dividers.

## Design Dials

Optional tunable knobs - set at session start, override per request:

- **Variance** (symmetry/centered/equal-grid → asymmetric/masonry/large empty zones). Above mid, force split-screen or left-aligned over centered heroes.
- **Motion** (CSS hover-only → scroll reveals + spring physics + perpetual micro-animation).
- **Density** (gallery whitespace → cockpit: tiny paddings, 1px dividers, tabular numbers, fewer cards).

## Design-Quality Process

A credible quality score requires SEEING the rendered screen - not reading code. Drive quality with a measured loop, not perfectionism.

- **Default target = 9/10** (not 9.5). Reserve >9 effort only when the user explicitly demands it, and warn them about diminishing returns and oscillation.
- **Loop:** render → screenshot → score → refactor against the real running UI. Capture with the `agent-browser` skill (note its headless drawer-capture caveat - animations can clip mid-frame).
- **Critic panel:** run an independent, multi-lens adversarial panel (visual / UX / skeptic) that READS the screenshots and scores an explicit rubric. Synthesize by **MEDIAN across critics**, never the harshest single voice.
- **Stop rule:** a "never concede" critic is asymptotic and oscillates - it invents new minor/subjective items each round and will even reverse prior advice (observed: a panel went 8.7 → 9.1 → 9.2 over three cycles, demanded a single-hue funnel, then called that single-hue funnel "one bar fading"). STOP when median ≥ 9 AND remaining items are subjective / contradictory / edge-case.
- **Separate capture artifacts from real gaps** before acting: a drawer clipped mid-animation or a wrong-record screenshot is a capture bug, not a design bug.
- **Fix real bugs the loop surfaces** - it often finds logic, not just looks (e.g. a `phone.includes("")` filter that matched everything; a progress-bar/funnel math error).
- **Parallelize per-screen refactors** with STRICT file ownership: one agent per file, a single agent owning shared components/mocks, so concurrent rounds don't conflict.
- **Native-integration precedence:** when the UI must be native to an existing app (internal/operator tools especially), match the app's design language and component library - the bold/distinctive anti-slop default yields to native consistency.

## Design Pass

Start with the product context:

- **User and job:** who uses this, how often, under what pressure, and what they must accomplish first.
- **Surface type:** app/workbench, admin/dashboard, marketing page, product page, docs, portfolio, game, editor, data viz, or 3D experience.
- **Density:** operational tools need dense but organized information; marketing surfaces can use more editorial rhythm.
- **Existing language:** tokens, component library, icon set, radius scale, spacing scale, typography, charts, and empty-state style.
- **Constraints:** accessibility, mobile use, slow data, internationalized text, long labels, large datasets, and permissions.

Then decide:

- Layout hierarchy before color.
- Interaction states before decoration.
- Responsive behavior before desktop polish.
- Verification before handoff.

## Accessibility Floor

WCAG 2.2 is the baseline. It extends earlier WCAG versions and applies across desktop and mobile web. Automated tools help, but manual checks remain required.

Check:

- Page has one logical `h1`, sequential headings, and landmark regions.
- Interactive elements are keyboard reachable in a sensible order.
- Focus indicators are visible and not hidden by sticky headers, drawers, cookie banners, or overlays.
- Controls have accessible names; icon-only buttons use `aria-label` or equivalent.
- Form inputs have visible labels, not placeholder-only labels.
- Errors are tied to fields and announced with `aria-describedby`, `role="alert"`, or an appropriate live region.
- Text contrast is at least 4.5:1 for normal text and 3:1 for large text or non-text UI indicators.
- Do not encode meaning by color alone. Add text, icons, patterns, or shape.
- Motion respects `prefers-reduced-motion`.
- Touch targets meet WCAG 2.2 minimums and, for practical touch UI, aim for 44x44 CSS px with enough spacing.

Sources:

- WCAG 2.2: https://www.w3.org/TR/WCAG22/
- WCAG focus appearance understanding: https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html
- WCAG target size understanding: https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html

## Responsive Layout

Use mobile-first CSS and stable constraints:

- Test at small mobile (~375px), tablet (~768px), desktop (~1280px), and wide desktop when the layout changes.
- Prefer `min-height: 100dvh` / `min-h-dvh` for viewport-height surfaces.
- Avoid fixed pixel container widths. Use `max-width`, fluid grid tracks, `clamp()` for spacing when needed, and content-based breakpoints.
- Reserve space for async content, media, charts, and canvases with `width`/`height`, `aspect-ratio`, skeletons, or fixed grid tracks.
- Avoid nested scroll regions unless the product needs them. If used, make them obvious and keyboard-scrollable.
- Sticky headers/footers must not cover focused elements or final list items.
- Long words, labels, emails, URLs, code, and translated strings must wrap or truncate intentionally with an affordance to see the full value.

## Visual Polish

Prefer a coherent system over decorative novelty:

- Type scale: keep body text at 16px or larger; use 12-14px only for metadata, labels, and dense tables.
- Line height: body 1.45-1.7; compact controls can be tighter.
- Line length: prose 60-75 characters on desktop; shorter on mobile.
- Radius: keep cards and controls at 8px or less unless the existing system uses more.
- Shadows: use a small elevation scale. Do not stack blur, glow, ring, border, and shadow on the same element without purpose.
- Color: define semantic tokens (`background`, `foreground`, `muted`, `border`, `primary`, `danger`, `success`) and avoid raw hex scattered through components.
- Dark mode: design separately; do not invert light mode. Recheck contrast and disabled states.
- Icons: one visual family, consistent size and stroke, aligned to text baseline.
- Animation: 150-300ms for micro-interactions, transform/opacity only when possible, interruptible, and tied to state change.

Avoid:

- Decorative gradient/orb/bokeh backgrounds in app UI.
- Hero-size text inside compact panels or dashboards.
- Cards inside cards.
- Floating page sections styled as giant cards.
- Hover-only affordances.
- Spinner-only waits over one second without skeleton or progress context.

## Forms

Good forms are explicit and recoverable:

- Labels are visible and persistent.
- Required/optional status is clear.
- Use semantic input types and autocomplete attributes.
- Validate on blur or submit by default, not on every keystroke unless the feedback is genuinely useful.
- Put error text next to the relevant field and move focus to the first invalid field after submit.
- Keep submit buttons stable. On submit, disable or guard duplicate submission and show progress.
- Preserve user input on errors and route changes unless intentionally discarded.
- Destructive actions require confirmation or undo.
- Multi-step flows need progress, back navigation, and draft persistence when long.

## Data Tables And Charts

For tables:

- Use real column headers, sorting state (`aria-sort` where applicable), row focus/selection states, and keyboard-accessible row actions.
- Keep numeric columns aligned and use tabular figures.
- Use sticky headers only when they do not hide focus.
- Provide empty, loading, error, filtered-empty, and permission-empty states.
- Virtualize large tables and keep row height stable.

For charts:

- Choose chart by question: trend -> line/area, comparison -> bar, distribution -> histogram/box, part-to-whole -> stacked bar or donut only for few categories.
- Provide units, readable axis labels, legends, and exact-value tooltip or data labels.
- Do not rely on red/green or color alone.
- Add a text summary for screen readers and a table/export path for data-heavy products.
- Simplify charts on mobile instead of shrinking dense axes into unreadability.

## Review Format

When asked to review UI, lead with findings:

```text
file:line - Severity - Issue. Why it matters. Suggested fix.
```

Severity:

- `Blocker`: unusable, inaccessible, data-loss, broken primary flow.
- `High`: major accessibility, responsive, or interaction issue.
- `Medium`: polish or consistency issue users will notice.
- `Low`: minor improvement.

If no issues are found, say so and list what was actually checked.
