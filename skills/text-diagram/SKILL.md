---
name: text-diagram
description: Draw reliable, well-aligned text/ASCII architecture diagrams with nested boxes, arrows, and connectors. Use when user asks to draw/create text diagrams, ASCII art diagrams, box diagrams, or architecture diagrams in plain text. For rendered image artifacts (PNG/SVG), use /vd:diagram instead.
license: MIT
argument-hint: "[diagram description or 'from image']"
metadata:
  author: vanducng
  version: "0.1.0"
---

# Text Diagram Drawing

Draw professional, pixel-perfect text-based architecture diagrams using monospace characters. Every character must align correctly in a monospace font.

## Critical Rules (NEVER violate)

1. **Calculate widths BEFORE drawing.** Never freehand a diagram. Always compute column widths, box widths, and total widths first, then render.
2. **Every line in a box must be the SAME character length.** Count characters. Verify.
3. **Use ONLY ASCII-safe monospace characters** for borders: `|`, `-`, `+` for basic; or Unicode box-drawing (see charset below). Never mix styles in one diagram.
4. **Pad content with spaces** to fill the full inner width of every box.
5. **Vertical connectors** (`|` or `│`) must be at the EXACT same column position on every line between two boxes.
6. **After drawing, mentally re-count** character positions of the first line, last line, and any connector lines to verify alignment.
7. **One box-drawing style per diagram.** Don't mix `+--+` with `┌──┐`.

## Character Sets

### Style A: Pure ASCII (safest, works everywhere)
```
Corners:  +
Horiz:    -
Vert:     |
Arrow:    -> or -->
Down:     v or V
Cross:    +
T-junc:   +
```

### Style B: Unicode Light Box Drawing (cleaner look)
```
Corners:  ┌ ┐ └ ┘
Horiz:    ─
Vert:     │
T-junc:   ├ ┤ ┬ ┴
Cross:    ┼
Arrow:    → ← ↑ ↓
Triangle: ▼ ▲ ► ◄
```

### Style C: Unicode Rounded (friendly look)
```
Corners:  ╭ ╮ ╰ ╯
Horiz:    ─
Vert:     │
(rest same as Style B)
```

### Style D: Double-line (emphasis/outer containers)
```
Corners:  ╔ ╗ ╚ ╝
Horiz:    ═
Vert:     ║
T-junc:   ╠ ╣ ╦ ╩
Cross:    ╬
```

### Style E: Dashed borders (secondary containers)
```
Vert:     ¦  or  :  or  ╎
Horiz:    - - -  (dash-space-dash)
```

## Width Constraints

- **Default max width: 80 characters** (standard terminal). Use 120 for wide diagrams.
- If a diagram exceeds the limit, reduce padding, abbreviate labels, or split into multiple diagrams.
- **Never use tab characters.** Always spaces.
- All Unicode box-drawing chars (U+2500–U+257F) are exactly 1 column wide. Safe to use.
- **Avoid:** CJK chars (2-wide), emoji (variable width), heavy/dashed variants if cross-platform rendering matters.

## Drawing Algorithm

**ALWAYS follow these steps in order:**

### Step 1: Plan the Layout
- List all boxes, their nesting depth, and content lines
- Determine layout direction (top-down, left-right, or mixed)
- Identify connectors between boxes

### Step 2: Calculate Dimensions (CRITICAL)
```
For each box:
  inner_width = max(len(line) for line in content_lines) + 2*padding
  outer_width = inner_width + 2  (for left/right borders)

For side-by-side boxes:
  total_width = sum(outer_widths) + gaps_between_boxes

For container boxes:
  container_inner_width = max(total_width_of_children, len(title)) + 2*padding
  container_outer_width = container_inner_width + 2
```

### Step 3: Render Top-Down
- Draw each line as a fixed-width string
- Use `.ljust()` / space-padding to ensure every line in a box is the same width
- For nested boxes: indent children by container's left border + padding
- **Symmetric padding rule:** if you indent a child row with 2 spaces on the LEFT after the container's `│`, you must reserve 2 spaces on the RIGHT before the closing `│`. The most common alignment bug is leaving only 1 space on the right.

### Step 4: Verify Alignment
- Check: first border line length == last border line length
- Check: all content lines length == border line length
- Check: vertical connector column is consistent across all rows
- Check: side-by-side boxes have matching heights (pad shorter ones with empty lines)

## Layout Patterns

### Pattern: Container with Title
```
┌──────────────────────────────┐
│ Container Title              │
│                              │
│  ┌────────┐  ┌────────┐      │
│  │ Box A  │  │ Box B  │      │
│  └────────┘  └────────┘      │
│                              │
└──────────────────────────────┘
```
**Rule:** outer width = 32. Every row (border, title, empty, child rows, bottom) is exactly 32 chars. Right padding before the closing `│` mirrors the left padding (2 spaces) plus any extra slack.

### Pattern: Vertical Flow with Connector
```
┌──────────┐
│  Box A   │
└────┬─────┘
     │
     ▼
┌──────────┐
│  Box B   │
└──────────┘
```
**Rule:** The `│` and `▼` must be at the same column as `┬`. Calculate: `left_border + (inner_width / 2) + 1`.

### Pattern: Horizontal Flow Inside Container
```
┌──────────────────────────────────────┐
│                                      │
│  ┌─────────┐    ┌─────────┐          │
│  │ Step 1  │ →  │ Step 2  │          │
│  └─────────┘    └─────────┘          │
│                                      │
└──────────────────────────────────────┘
```
**Rule:** outer width = 40. Arrow `→` sits at the vertical midpoint of the boxes, between them. Right side keeps ≥2 spaces before the closing `│` to mirror left padding.

### Pattern: Side-by-Side Boxes (Equal Height)
```
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Title A  │  │ Title B  │  │ Title C  │
│ (desc)   │  │ (desc)   │  │ (desc)   │
└──────────┘  └──────────┘  └──────────┘
```
**Rule:** All boxes MUST have the same number of lines. Pad shorter boxes with blank content lines.

### Pattern: Centered Connector Between Sections
```
┌─────────────────────────┐
│ Section A               │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Section B               │
└─────────────────────────┘
```
**Rule:** Both sections should be the same width. Connector at `width / 2`.

## Common Mistakes to Avoid

| Mistake | Fix |
|---------|-----|
| Lines in a box have different lengths | Pad ALL lines to `max_content_width + 2*padding` |
| Right border 1 char short on child rows | Mirror left padding: if left has 2 spaces, right needs 2 spaces too |
| Vertical connector off by 1 | Calculate center: `border_start + 1 + floor(inner_width / 2)` |
| Nested box wider than parent | Calculate parent width from children FIRST |
| Side-by-side boxes different heights | Count lines, pad shorter box with empty `│{spaces}│` lines |
| Right border not aligned | Use fixed-width strings, never rely on "looks right" |
| Mixed border styles | Pick ONE style at the start, use it throughout |
| Arrow not vertically centered on box | Arrow row = top_border_row + 1 + floor(content_lines / 2) |
| Forgot to account for border chars | outer_width = inner_width + 2 (left `│` + right `│`) |

## Rendering Checklist (Run mentally after drawing)

- [ ] Every box: first border line length == last border line length
- [ ] Every box: all content lines == border line length
- [ ] Container boxes: wider than all children combined + gaps + padding
- [ ] Side-by-side boxes: all same height (line count)
- [ ] Vertical connectors: same column on every row
- [ ] No trailing spaces inconsistency
- [ ] Nested boxes indented consistently
- [ ] Arrows aligned to box midpoints
- [ ] Right padding mirrors left padding before the closing border

## Examples

See `references/examples.md` for complete worked examples with dimension calculations, and `references/advanced-patterns.md` for nested architectures, fan-out, and annotated connectors.
