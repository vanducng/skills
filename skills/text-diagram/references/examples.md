# Text Diagram Examples

## Example 1: Simple Vertical Flow

**Goal:** Three boxes connected vertically.

**Step 1 - Content:**
- Box A: "Input Data" (10 chars)
- Box B: "Process" (7 chars)
- Box C: "Output" (6 chars)

**Step 2 - Dimensions:**
- Padding: 1 space each side
- Box A inner_width = 10 + 2 = 12, outer = 14
- Box B inner_width = 10 + 2 = 12, outer = 14 (use max for uniform width)
- Box C inner_width = 10 + 2 = 12, outer = 14
- Connector column = 1 + floor(12/2) = 7 (0-indexed)

**Step 3 - Render:**
```
┌──────────────┐
│  Input Data  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Process    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    Output    │
└──────────────┘
```

**Verification:**
- All border lines: 14 chars (┌ + 12×─ + ┐) ✓
- Content lines: 14 chars (│ + content padded to 12 + │) ✓
- Connector at col 7 on all connector rows ✓

---

## Example 2: Side-by-Side Boxes in a Container

**Goal:** Container "Services" with 3 child boxes.

**Step 1 - Content:**
- Child A: "Auth" (4 chars), "(JWT)" (5 chars) → 2 content lines
- Child B: "Users" (5 chars), "(CRUD)" (6 chars) → 2 content lines
- Child C: "Mail" (4 chars), "(SMTP)" (6 chars) → 2 content lines

**Step 2 - Dimensions:**
- Child padding: 1 space each side
- Child A: inner = max(4,5)+2 = 8, outer = 10
- Child B: inner = max(5,6)+2 = 8, outer = 10
- Child C: inner = max(4,6)+2 = 8, outer = 10
- Gap between children: 2 spaces
- Children row total: 10 + 2 + 10 + 2 + 10 = 34
- Container padding: 2 spaces each side (LEFT and RIGHT must match)
- Container inner = max(34, len("Services")) + 4 = 38
- Container outer = 40

**Step 3 - Render:**
```
┌──────────────────────────────────────┐
│ Services                             │
│                                      │
│  ┌────────┐  ┌────────┐  ┌────────┐  │
│  │  Auth  │  │ Users  │  │  Mail  │  │
│  │ (JWT)  │  │ (CRUD) │  │ (SMTP) │  │
│  └────────┘  └────────┘  └────────┘  │
│                                      │
└──────────────────────────────────────┘
```

**Verification:**
- Container border: 40 chars each ✓
- All container content lines: 40 chars (1 + 2 left-pad + 34 children + 2 right-pad + 1 = 40) ✓
- Child boxes all 10 chars wide, 4 lines tall (border + 2 content + border) ✓
- Children aligned on same row ✓

**Common bug:** It's tempting to write only 1 trailing space before the closing `│` on the children rows. That makes those rows 39 chars while the border is 40 - visibly misaligned in monospace. Always mirror the left padding.

---

## Example 3: Horizontal Flow with Arrows

**Goal:** Pipeline: Validate → Transform → Load

**Step 1 - Dimensions:**
- Box widths: all uniform at outer=14 (inner=12)
- Arrow: " → " (3 chars between boxes)
- Total width: 14 + 3 + 14 + 3 + 14 = 48

**Step 3 - Render:**
```
┌────────────┐   ┌────────────┐   ┌────────────┐
│  Validate  │ → │ Transform  │ → │    Load    │
└────────────┘   └────────────┘   └────────────┘
```

**Verification:**
- Each box: 14 chars wide ✓
- Arrow at content midpoint (row 2 of 3) ✓
- Total line length: 48 chars, consistent ✓

---

## Example 4: Multi-Level Architecture

**Goal:** 3-tier diagram: YAML Manifest → GCPlane Engine → GoClaw Instance

**Step 2 - Dimensions (bottom-up):**

Tier 1 children (4 boxes, each outer=12, gap=2):
- Row total: 12+2+12+2+12+2+12 = 54
- Container padding: 2 each side
- Container inner = max(54, 25) + 4 = 58
- Container outer = 60

For consistency across tiers we'll use **outer=64** (matches the Tier 3 row below; pad earlier tiers).

Tier 3 children (Instance internals): 4 boxes (outer 14, 14, 14, 10) with 2-space gaps
- Row: 14+2+14+2+14+2+10 = 58
- Container inner = max(58, 41) + 4 = 62
- Container outer = 64

**Step 3 - Render (uniform outer = 64):**
```
┌──────────────────────────────────────────────────────────────┐
│ YAML Manifest (camelCase)                                    │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Provider │  │  Agent   │  │ Channel  │  │MCPServer │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
│                                                              │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ GCPlane Engine                                               │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────────┐  │
│  │  Validate    │    │  Reconcile   │    │ Apply (Create/ │  │
│  │  (refs +     │ →  │  (Observe →  │ →  │ Update/Delete) │  │
│  │   schema)    │    │   Compare)   │    │                │  │
│  └──────────────┘    └──────────────┘    └────────────────┘  │
│                                                              │
│  ┌───────────────────┐  ┌──────────────────────────────┐     │
│  │ Key Translation   │  │ Source (File / Git repo)     │     │
│  │ camelCase ↔ snake │  │ SHA256 / commit hash skip    │     │
│  └───────────────────┘  └──────────────────────────────┘     │
│                                                              │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ GoClaw Instance                                              │
│ HTTP REST API (:18790) + WebSocket RPC v3                    │
│                                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────┐  │
│  │ Providers  │  │  Agents    │  │  Channels  │  │  MCP/  │  │
│  │ (13+ LLM)  │  │ (AI bots)  │  │ (TG/Slack) │  │ Teams  │  │
│  └────────────┘  └────────────┘  └────────────┘  └────────┘  │
│                                                              │
│                          ▼                                   │
│                     PostgreSQL                               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Verification:** every line is exactly 64 chars wide. Right padding mirrors left padding (2 spaces) for every children row.

---

## Example 5: Dashed Border Boxes

Use dashed borders for optional/secondary elements:

```
┌─────────────────────────────┐
│ Main System                 │
│                             │
│  ┌─────────┐  ╌╌╌╌╌╌╌╌╌╌╌╌  │
│  │  Core   │  ╎ Optional ╎  │
│  │ Module  │  ╎  Plugin  ╎  │
│  └─────────┘  ╌╌╌╌╌╌╌╌╌╌╌╌  │
│                             │
└─────────────────────────────┘
```

Or use simple dashes with colons for vertical:

```
┌─────────┐ - - - - - -
│  Core   │   : Plugin  :
│ Module  │   : (opt.)  :
└─────────┘ - - - - - -
```

---

## Width Calculation Quick Reference

```
single_box_outer = max(content_line_lengths) + 2*padding + 2
side_by_side     = sum(child_outers) + (n-1)*gap
container_outer  = max(children_total, title_len) + 2*container_padding + 2
connector_col    = left_edge + 1 + floor(inner_width / 2)
```

**Symmetric padding invariant:** for every container row, the count of spaces between the opening `│` and the first child must equal the count of spaces between the last child and the closing `│`. Right-side padding being 1 char short of left-side padding is the #1 alignment bug.
