# Advanced Patterns & Techniques

## Technique: Grid-Based Canvas Rendering

The most reliable approach for complex diagrams. Think of the output as a 2D character grid.

### Mental Model
```
1. Create a virtual grid: rows × cols
2. Place each element at exact (row, col) coordinates
3. Fill empty cells with spaces
4. Output row by row
```

### Why This Works
- Forces you to think in absolute positions, not relative
- Every character has a defined (row, col) - no drift
- Connectors automatically align because you place them at calculated positions

---

## Pattern: Multi-Row Nested Architecture

For diagrams with 3+ nesting levels:

```
╔══════════════════════════════════════════════╗
║ System                                       ║
║                                              ║
║  ┌────────────────────────────────────────┐  ║
║  │ Subsystem A                            │  ║
║  │                                        │  ║
║  │  ┌──────────┐  ┌──────────┐            │  ║
║  │  │ Module 1 │  │ Module 2 │            │  ║
║  │  └──────────┘  └──────────┘            │  ║
║  │                                        │  ║
║  └────────────────────────────────────────┘  ║
║                                              ║
║  ┌────────────────────────────────────────┐  ║
║  │ Subsystem B                            │  ║
║  │                                        │  ║
║  │  ┌──────────┐  ┌──────────┐            │  ║
║  │  │ Module 3 │  │ Module 4 │            │  ║
║  │  └──────────┘  └──────────┘            │  ║
║  │                                        │  ║
║  └────────────────────────────────────────┘  ║
║                                              ║
╚══════════════════════════════════════════════╝
```

**Key:** Use double-line (╔═╗) for outermost, single-line (┌─┐) for mid-level, single-line for inner. Provides visual hierarchy.

**Width invariant:** outer = 48 chars. Subsystem container inner = 40. Inside the subsystem, child rows have 2-space left padding and must keep 12-space right padding (2 padding + 10 slack) so total inner = 40.

---

## Pattern: Bidirectional Flow

```
┌──────────┐         ┌──────────┐
│  Client  │ ──req→  │  Server  │
│          │ ←res──  │          │
└──────────┘         └──────────┘
```

**Rule:** Request and response arrows on separate lines, both between the same column boundaries.

---

## Pattern: Fan-Out / Fan-In

```
                 ┌──────────┐
            ┌──→ │ Worker 1 │ ──┐
            │    └──────────┘   │
┌────────┐  │    ┌──────────┐   │    ┌─────────┐
│  Queue │ ─┼──→ │ Worker 2 │ ──┼──→ │  Sink   │
└────────┘  │    └──────────┘   │    └─────────┘
            │    ┌──────────┐   │
            └──→ │ Worker 3 │ ──┘
                 └──────────┘
```

**Key:** The fan-out connector `┼` aligns vertically. Workers are stacked with consistent spacing.

---

## Pattern: Legend / Key Box

Place in bottom-right or below the diagram:

```
┌─────────────────────┐
│ ━━━  Primary flow   │
│ ╌╌╌  Optional flow  │
│ [X]  Component      │
│  →   Data direction │
└─────────────────────┘
```

---

## Pattern: Annotated Connector

```
┌──────────┐
│  Source  │
└─────┬────┘
      │ JSON/HTTP
      │ port 8080
      ▼
┌──────────┐
│   Dest   │
└──────────┘
```

**Rule:** Annotations sit to the right of the connector, starting 1 space after `│`.

---

## Pattern: Table Inside a Box

```
┌──────────────────────────────┐
│ Configuration                │
│                              │
│  Key         │ Value         │
│  ────────────┼────────────── │
│  host        │ localhost     │
│  port        │ 8080          │
│  timeout     │ 30s           │
│                              │
└──────────────────────────────┘
```

---

## Spacing Rules

| Element                | Spacing              |
|------------------------|----------------------|
| Between sibling boxes  | 2 spaces             |
| Container padding      | 2 spaces each side   |
| Content padding in box | 1 space each side    |
| Between flow rows      | 1 blank line         |
| Between sections       | connector + 1 blank  |
| Indent per nest level  | 2 spaces             |

**Symmetric padding invariant:** left padding == right padding. If a container indents children with 2 spaces on the left, it must reserve at least 2 spaces on the right before the closing `│`.

---

## Handling Variable-Width Content

When box content varies significantly:

**Option A: Uniform width** (preferred for side-by-side)
- Set all sibling boxes to same width = max of all siblings
- Pad shorter content with spaces

**Option B: Fitted width** (OK for stacked boxes)
- Each box sized to its own content
- Must still match container width constraints

**Always choose Option A for boxes on the same row.**

---

## Connector Centering Formula

For a box starting at column `start` with outer width `w`:
```
connector_col = start + floor(w / 2)
```

For centering a connector between two stacked boxes of different widths:
```
top_center    = top_start + floor(top_width / 2)
bottom_center = bottom_start + floor(bottom_width / 2)

If different: make boxes same width, or use an L-shaped connector:
    │
    └──────┐
           │
           ▼
```

---

## Common Width Gotchas

1. **Tab characters:** NEVER use tabs. Always spaces.
2. **Unicode width:** `→` `▼` `│` `─` are all 1 column wide in monospace. Safe to use.
3. **CJK characters:** 2 columns wide. Avoid in diagrams or account for double-width.
4. **Emoji:** Variable width. NEVER use in diagrams.
5. **Box-drawing chars:** All exactly 1 column wide. Safe.
6. **Asymmetric padding:** the most common alignment bug - left padding doesn't match right padding inside a container, making child rows N-1 chars wide while borders are N chars wide.

---

## Verification Checklist (Extended)

After drawing any diagram, verify:

1. Pick any horizontal border line → count its characters
2. Pick ALL other lines in the same box → must be same count
3. For container boxes: every line between top and bottom border must be same length
4. For vertical connectors: find the `┬` or `│` → note its column → verify all subsequent `│` and `▼` are at that exact column
5. For side-by-side boxes: count lines in each → must match
6. For nested boxes: child outer_width + 2*parent_padding + 2 ≤ parent outer_width
7. No line should have trailing whitespace beyond the box border (keep it clean)
8. Right padding mirrors left padding before every closing border
