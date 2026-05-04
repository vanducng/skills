# Composition Rules — Layout & Spacing

Universal layout rules. Type-specific axes are defined in each `types/<type>.md`.

## Whitespace

- **≥40px breathing room** around every grouping box.
- **≥24px** between adjacent elements on the same row.
- Labels never touch arrows. Minimum 8px gap.
- No element clips another. If two elements would overlap, shrink the diagram or split it.

## Hierarchy

- **Sequence / data-flow / system-architecture**: primary flow runs **left → right**.
- **State machine**: primary flow runs **top → bottom** (or radial when natural).
- **C4 (context, container)**: subject system at center; external relationships emanate outward.
- **ER diagram**: cluster strongly-related entities; place "core" entities centrally and dependent entities at the edges.

## Label Placement

- Arrow labels sit **above** the arrow, never below.
- Labels never cross other arrows or shapes — re-route if needed.
- Label text is at most 4 words. If you need more, attach a numbered note (`①`, `②`) and list notes off to the side.

## Grouping

- Use rounded rectangles with **1px muted borders** to denote bounded contexts, services, or subsystems.
- Group title sits at the top-left of the box, in the muted color.
- Grouping boxes never overlap. Nest at most 2 levels deep.

## Density

- Target **≤15 elements per diagram** (services, databases, actors all count).
- If the description implies >15, split into two diagrams or zoom out (use C4-context to summarize).
- White space is a feature, not waste.

## Color Application

- Primary slate `#1e293b` is the default for borders/text.
- Accent amber `#d97706` highlights at most ONE element — the subject.
- Success sage `#059669` is reserved for explicit "OK" / "sync" paths when juxtaposed against error paths.
- Error rust `#dc2626` is reserved for explicit failure / retry paths.
- Never apply success/error colors decoratively. Their meaning is semantic.

## Redundant Encoding (WCAG 1.4.1)

Every semantic distinction MUST be encoded by **at least two** of:

- color
- shape
- line style (solid / dashed / dotted)
- position (in/out, above/below, layer order)
- label text

Color alone is never sufficient. ~5% of viewers have a color-vision deficiency.

Examples:
- **Sync vs async** — solid filled-arrow vs dashed open-arrow + (optional) primary vs muted color
- **Internal vs external** — 2px solid border vs 1.5px dashed border + label tag `[External]`
- **OK vs error path** — bluish-green stroke + "ok" label + solid arrow vs vermilion stroke + "error" label + dashed arrow
