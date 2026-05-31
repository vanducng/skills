---
name: excalidraw
description: "MANDATORY prerequisite for ALL Excalidraw MCP tool usage. Read BEFORE calling any Excalidraw tool (batch_create_elements, create_element, update_element, etc.). Without the sizing formulas, two-batch ordering (shapes-then-arrows), compact legends, domain styling presets, and write-check-review cycle in this skill, diagrams have invisible arrows, truncated text, and inconsistent colors. Use whenever the user asks to draw, sketch, visualize, or diagram anything technical — system architecture, microservices topology, C4 diagrams, data pipelines / ETL flows / lakehouse, sequence diagrams, ER diagrams, deployment / Kubernetes diagrams, network topology, flowcharts, decision trees. Includes ready-to-apply color palettes for software engineering, system architecture, and data solutions."
license: MIT
metadata:
  author: vanducng
  version: "1.1.0"
---

# Excalidraw — Technical Diagram Skill

Build professional, consistent Excalidraw diagrams via MCP. Skill covers: tool mechanics, sizing formulas, write-check-review verification cycle, and **domain-specific styling presets** for software engineering, system architecture, and data solutions.

## Step 0 — Detect Connection

Check **in order**:

1. **MCP server**: tools prefixed `mcp__excalidraw-mcp__*` (e.g. `batch_create_elements`, `describe_scene`) available → use MCP mode. This is the default for this user.
2. **REST fallback**: only if MCP missing — `curl -s $EXPRESS_SERVER_URL/health` returns `{"status":"ok"}`.
3. **Nothing** → auto-bootstrap `.mcp.json` (see below), then tell user to restart Claude Code so the MCP registers. Do not fake output.

### Auto-bootstrap `.mcp.json`

When neither the MCP tools nor the REST fallback are available:

1. Resolve **project root**: `git rev-parse --show-toplevel` (fallback to CWD if not a git repo).
2. Derive **project name** = `basename` of the project root.
3. If `<project_root>/.mcp.json` does **not** exist, create it with this exact template (substitute `<project_name>`):

   ```json
   {
     "mcpServers": {
       "excalidraw-mcp": {
         "type": "http",
         "url": "https://mcp.dataplanelabs.com/excalidraw/mcp",
         "headers": {
           "Authorization": "Bearer ${EXCALIDRAW_MCP_TOKEN}",
           "X-Tenant-Id": "<project_name>"
         }
       }
     }
   }
   ```

4. If `.mcp.json` already exists, **merge** — add the `excalidraw-mcp` entry under `mcpServers` without clobbering other servers. Skip if `excalidraw-mcp` already present.
5. Tell the user: file written, ensure `EXCALIDRAW_MCP_TOKEN` is exported in shell env, then restart Claude Code (or run `/mcp` to reconnect) before re-running the skill.

Never write the bootstrap file outside the resolved project root, and never echo the token value.

The remote canvas (when this user's MCP is used) is at `https://draw.dataplanelabs.com`. For visual verification beyond `get_canvas_screenshot`, use Chrome DevTools MCP to `take_screenshot` of the canvas URL — `get_canvas_screenshot` sometimes returns blank PNGs.

## Step 1 — Tenant & Project Setup

The remote Excalidraw MCP is multi-tenant. Tenant is selected via the `X-Tenant-Id` header (configured in `.mcp.json`) or via tools.

Before any drawing:

1. `list_tenants` — confirm active tenant
2. `list_projects` — confirm active project; `switch_project` with `createName` if a fresh canvas is wanted
3. `describe_scene` — read existing diagram zones + suggested next placement coordinates

**Never** call `clear_canvas` unless the user explicitly says wipe. Place new diagrams spatially offset (≥300px) from existing ones.

## Core Principles (Read Before Any Diagram)

### 1. Write → Check → Review → Fix (Mandatory Loop)

```
WRITE batch → set_viewport(scrollToContent: true) → screenshot
  → REVIEW against Quality Checklist → FIX issues → re-screenshot
    → only proceed when all checks pass
```

### 2. Use `batch_create_elements` — Not `create_from_mermaid`

`create_from_mermaid` produces overlapping text and broken layouts. Use it only as a quick preview, never for final output. For quality, always plan coordinates and call `batch_create_elements`.

### 3. Two Batches: Shapes First, Arrows Second

Arrow binding (`startElementId`/`endElementId`) requires shapes to exist already. Mixing in one batch causes binding errors.

### 4. `roughness: 0` for Technical Diagrams

Excalidraw defaults to hand-drawn (roughness > 0). For professional system / data / architecture diagrams, set `roughness: 0` on every element. Use `strokeWidth: 2` for arrows.

### 5. Multi-Diagram Canvas

Never clear canvas between diagrams. Place side-by-side or stacked with ≥300px gap. Add a title text element (fontSize 24-28) above each. Group with `group_elements` so `describe_scene` reports it as a named zone.

### 6. Add a Compact Legend When It Clarifies

Include a small legend whenever colors, shapes, stroke styles, or arrow colors encode non-obvious meaning. Keep it minimal:

- Trigger: 3+ semantic node colors, 2+ arrow styles/colors, or mixed ownership/status meanings (internal/external, allow/deny, batch/stream).
- Size: 3-6 entries total; include only semantics actually used in the diagram.
- Placement: top-right or bottom-right whitespace, outside primary flow paths; fontSize 13-14.
- Content: one swatch/mini-line + a short label (`Stream`, `Batch`, `External`, `Denied`).
- Skip it when labels already make the encoding obvious and the diagram only uses 1-2 semantic styles.

Do not build a full catalog. A legend should explain the visual language, not duplicate every node or edge label.

## Sizing Rules (Prevents Truncation)

Excalidraw's font is ~30% wider than typical sans-serif. Use these formulas:

| Shape | Width | Height | fontSize |
|-------|-------|--------|----------|
| Rectangle | `max(200, chars * 11)` | 70 (1 line) / 80 (2) / 100 (3) | 16-20 |
| Diamond (text uses ~50% of bbox — **double**) | `max(400, longestLine * 18)` | `max(160, lines * 50)` | 16 |
| Ellipse (text ~60% of bbox) | `max(280, chars * 14)` | `max(65, lines * 35)` | 16-18 |
| Title text | — | — | 24-28 |

## Arrow Visibility (Prevents Invisible Arrows)

Bound arrows shrink to `gap_between_shapes - 16` (8px binding padding each side). Below 80px, arrows vanish.

| Direction | Min gap | Recommended |
|-----------|---------|-------------|
| Vertical | 80px | **120px** |
| Horizontal | 100px | **140px** |

```
gap = nextShape.y - (currentShape.y + currentShape.height)
```

## Domain Styling Presets

Pick the preset matching the diagram type. Apply fill + stroke + shape per row. Don't mix palettes within one diagram unless intentional.

### Minimal Legend Defaults

Use these entries only when the matching semantics appear in the diagram:

| Meaning | Legend mark |
|---------|-------------|
| Sync/API call | blue solid arrow `#1976d2`, width 2 |
| Batch/data load | gray solid arrow `#757575`, width 2 |
| Stream/event | orange solid arrow `#f57c00`, width 3 |
| Async/queue | orange dashed arrow `#e8590c`, width 2 |
| Lineage/dependency | purple dotted arrow `#9c27b0`, width 1 |
| Denied/security block | red solid arrow `#d32f2f`, width 3 |

For node legends, show only the shape/color roles that are not already obvious from labels, such as `Internal service`, `External system`, `Database`, `Queue`, or `Security boundary`.

### Software Architecture (C4 / Microservices)

| Role | Shape | Fill | Stroke | Label format |
|------|-------|------|--------|--------------|
| Person / Actor | hexagon or ellipse | `#fff3e0` | `#f57c00` | `User\n[Person]` |
| Software System (Context) | rectangle | `#e3f2fd` | `#1976d2` | `My System\n[Software System]` |
| Container | rounded rectangle | `#a5d8ff` | `#0d6efd` | `API Gateway\n[Container: Node.js]` |
| Component | rectangle | `#b9e0fb` | `#0c8599` | `OrderHandler\n[Component]` |
| Database | cylinder approx (rect + ellipse top) | `#f3e5f5` | `#7b1fa2` | `Orders DB\n[PostgreSQL]` |
| External system | rectangle, **dashed** stroke | `#fce4ec` | `#c2185b` | `Stripe\n[External]` |
| Async / Message Queue | hexagon | `#f0f4c3` | `#827717` | `Order Events\n[Kafka topic]` |
| Cache | rounded rectangle | `#b2dfdb` | `#00695c` | `Session Cache\n[Redis]` |

**Rule:** all elements in one C4 view share the same abstraction level. Don't mix Container with Component shapes in one diagram — split into two.

### Cloud Architecture (AWS / GCP / Azure)

Color by **service category**, label by service name + bracket type:

| AWS Category | Fill | Stroke | Examples |
|--------------|------|--------|----------|
| Compute | `#ffe0b2` | `#f57c00` | EC2, Lambda, ECS, Fargate |
| Storage | `#c8e6c9` | `#388e3c` | S3, EBS, EFS, Glacier |
| Database | `#ffccbc` | `#d84315` | RDS, DynamoDB, Aurora |
| Network | `#e1bee7` | `#7b1fa2` | VPC, ALB, Route 53, CloudFront |
| Security | `#ffcdd2` | `#d32f2f` | IAM, KMS, Secrets Manager, WAF |
| Analytics | `#ede7f6` | `#3f51b5` | Athena, Redshift, EMR, QuickSight |
| Messaging | `#fff9c4` | `#fbc02d` | SQS, SNS, Kinesis, EventBridge |
| Monitoring | `#bbdefb` | `#1976d2` | CloudWatch, X-Ray |

Bound zones (VPC, subnet, account) with a translucent rectangle: `backgroundColor: "#e9ecef"`, `opacity: 30`, label as title above.

**No icons?** Use `[Compute]`, `[Storage]`, etc. in the label and the category color does the visual work.

### Data Pipeline / Lakehouse / ETL

Encode **batch vs stream** via stroke width and color, **lineage** via dotted, **async** via dashed:

| Component | Shape | Fill | Stroke | Label |
|-----------|-------|------|--------|-------|
| Source (DB / API / files) | cylinder | `#b3e5fc` | `#0097a7` | `PostgreSQL\n[Source]` |
| Stream broker | hexagon | `#f0f4c3` | `#827717` | `Kafka\n[Topic: events]` |
| Batch job (Airflow / dbt) | rounded rectangle | `#fff9c4` | `#fbc02d` | `dbt run\n[Daily 02:00]` |
| Stream processor (Spark / Flink) | hexagon | `#ffecb3` | `#f57f17` | `Spark Stream\n[Processor]` |
| Sink (warehouse / lake) | cylinder | `#c8e6c9` | `#388e3c` | `Snowflake\n[Warehouse]` |
| ML model / feature store | rectangle | `#d1c4e9` | `#3f51b5` | `Recommender\n[Model]` |
| BI / dashboard | rounded rectangle | `#e1bee7` | `#7b1fa2` | `Looker\n[Dashboard]` |

| Edge type | Style | Color | Width | Label |
|-----------|-------|-------|-------|-------|
| Batch | solid | `#757575` | 2 | `daily 02:00` |
| Stream | solid | `#f57c00` | **3** | `topic: orders` |
| Async / queue | dashed | `#e8590c` | 2 | `queue: tasks` |
| Lineage (dbt parent→child) | dotted | `#9c27b0` | 1 | `derived from` |
| Sync API | solid | `#1976d2` | 2 | `POST /v1/...` |

**Layout:** sources top → processing middle → sinks bottom; warehouse layers (raw → staging → marts) flow top-down with consistent column alignment.

### UML — Sequence / ER / State / Class

#### Sequence
- Actors: hexagon `#fff3e0` / `#f57c00`
- Lifeline: vertical dashed line `#999`, strokeWidth 1
- Service: rectangle on top of lifeline `#e3f2fd` / `#1976d2`
- Sync message: solid arrow `#1976d2`, label `method()`
- Async message: dashed arrow `#f57c00`, label `event`
- Return: dashed arrow `#b0bec5`, label `result`

#### ER
- Entity: rectangle `#e8f5e9` / `#388e3c`, label = TableName
- Attribute: ellipse `#f3e5f5` / `#7b1fa2`, label = `column\ntype`
- Primary key: ellipse, **underline label**
- Relationship: diamond `#fff3e0` / `#f57c00`, label = verb (`has`, `owns`)
- Cardinality: text on the connection line (`1:N`, `M:N`)

#### State
- State: rounded rectangle `#bbdefb` / `#1976d2`
- Initial: small filled ellipse `#212121`
- Final: ellipse with inner dot
- Transition: solid arrow with `event [guard] / action` label

#### Class
- Class: rectangle, three sections separated by horizontal lines (name / fields / methods)
- Inheritance: solid arrow with empty triangle head, color `#1976d2`
- Composition: arrow with filled diamond, color `#d32f2f`
- Aggregation: arrow with empty diamond, color `#757575`

### Deployment — Kubernetes / Docker

K8s blue is `#326ce5`. Use it as the cluster boundary.

| Component | Shape | Fill | Stroke |
|-----------|-------|------|--------|
| Cluster (bounding box) | rectangle, opacity 30 | `#e3f2fd` | `#326ce5` |
| Node | rectangle | `#bbdefb` | `#1976d2` |
| Pod | rounded rectangle | `#a5d8ff` | `#0d6efd` |
| Service | hexagon | `#b2dfdb` | `#00695c` |
| Ingress | hexagon | `#80cbc4` | `#00897b` |
| PVC / Storage | cylinder | `#f3e5f5` | `#7b1fa2` |
| ConfigMap / Secret | small rounded rectangle | `#fffde7` | `#f57f17` |
| NetworkPolicy | rectangle, dashed stroke | `#ffcdd2` | `#d32f2f` |

Arrows: API call solid `#1976d2`, mount dotted `#7b1fa2`, replication dashed `#f57c00`, denied policy thick red.

## Quality Checklist

After every batch, verify ALL:

| Check | Look For | Fix |
|-------|----------|-----|
| Truncation | Labels cut off, especially in diamonds | Increase width using formulas above |
| Invisible arrows | Connections you cannot trace | Increase gap to ≥120px vertical |
| Arrow label collision | YES/NO labels overlap shapes | Shorten label or widen gap |
| Element overlap | Shapes share space | Reposition with proper spacing |
| Readability | Text legible at 50–70% zoom | Bump fontSize to ≥16 |
| Color consistency | Colors match a single domain preset | Re-pick from one table above |
| Stroke + fill contrast | Light fill + dark stroke (or inverse) | Use the pairs in tables — never light fill + light stroke |
| Legend clarity | Needed semantics absent, or legend lists everything | Add 3-6 used meanings only, or remove if redundant |

If any check fails: STOP. Use `update_element` or delete + recreate. Re-screenshot. Only proceed when all checks pass.

## Standard Workflow

```
1. describe_scene                              # see existing
2. Plan: list elements, layout direction, IDs, coordinates
3. Pick a domain preset (architecture/cloud/data/UML/deployment)
4. batch_create_elements: shapes (Batch 1)
5. batch_create_elements: arrows (Batch 2)
6. Add compact legend if trigger conditions apply
7. group_elements                              # group new diagram
8. set_viewport(scrollToContent: true)
9. Screenshot → Quality Checklist → fix → repeat
```

## Anti-Patterns (Avoid)

| Mistake | Why it fails | Do this |
|---------|--------------|---------|
| `create_from_mermaid` for production | overlapping text, bad layout | `batch_create_elements` with coordinates |
| Mixing C4 levels in one view | suggests false relationships | one diagram per level (Context, Container, Component) |
| Color chaos (8+ colors no meaning) | viewer loses semantic mapping | 3–4 primary + 1–2 accents from one preset |
| Unlabeled arrows | ambiguous: sync? async? what data? | label every arrow with what + how |
| Labeling shape by tech only ("Lambda") | diagram describes infra, not domain | name first: `CheckoutHandler [Lambda]` |
| Light fill + light stroke | invisible boundary | always pair light fill with dark stroke |
| Default `roughness > 0` | unprofessional for technical diagrams | always set `roughness: 0` |
| Shapes too close | arrows shrink to 0px | ≥120px vertical, ≥140px horizontal gap |
| Single-batch shapes + arrows | binding errors | two separate `batch_create_elements` calls |
| Trusting a single screenshot | MCP screenshot may be blank | fall back to Chrome DevTools `take_screenshot` of canvas URL |
| Master diagram showing all levels | illegible | split by concern (data flow / deployment / security) |
| Oversized legend | legend becomes visual clutter | 3-6 used meanings, tucked into whitespace |

## MCP Tool Quick Reference

| Category | Tools |
|----------|-------|
| Element CRUD | `create_element`, `get_element`, `update_element`, `delete_element`, `query_elements`, `batch_create_elements`, `duplicate_elements`, `search_elements`, `element_history` |
| Layout | `align_elements`, `distribute_elements`, `group_elements`, `ungroup_elements`, `lock_elements`, `unlock_elements` |
| Scene | `describe_scene`, `get_canvas_screenshot`, `get_resource`, `read_diagram_guide` |
| File I/O | `export_scene`, `import_scene`, `export_to_image`, `export_to_excalidraw_url` |
| State | `clear_canvas`, `snapshot_scene`, `restore_snapshot` |
| Viewport | `set_viewport` |
| Tenancy | `list_tenants`, `switch_tenant` |
| Projects | `list_projects`, `switch_project` |
| Conversion | `create_from_mermaid` (low-quality preview only) |

## Element Creation Cheat Notes

- Always assign a custom `id` to each shape so arrows can bind via `startElementId` / `endElementId`.
- For shape labels (rectangles, diamonds, ellipses): set `text` directly on the element — MCP auto-creates the bound text child.
- Curved arrows: `roundness: { type: 2 }` plus 3+ `points`.
- Elbowed arrows: `elbowed: true`.
- Dashed stroke: `strokeStyle: "dashed"`. Dotted: `strokeStyle: "dotted"`.
- Translucent zone backgrounds: `backgroundColor: "#e9ecef"`, `opacity: 30`.
- Compact legend: small swatch rectangles or 80px mini-lines with short labels; group legend elements with the diagram.

## References

- `references/styling-presets.md` — full color palettes per domain, layout templates, accessibility, comprehensive examples.
- `references/cheatsheet.md` — MCP tool list, REST API mapping, env vars, multi-tenancy notes.

When in doubt, re-read the preset table for your domain before drawing. Color and shape consistency matters more than how many shapes you draw.
