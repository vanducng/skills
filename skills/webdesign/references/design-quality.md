# Design Quality Reference

Use this reference for UI design, UX review, visual polish, accessibility, responsive layout, forms, charts, and dashboard work.

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
