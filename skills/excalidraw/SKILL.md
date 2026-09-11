---
name: excalidraw
description: "MANDATORY prerequisite for ALL Excalidraw MCP tool usage. Read BEFORE calling any Excalidraw tool (batch_create_elements, create_element, update_element, etc.). Without the sizing formulas, two-batch ordering (shapes-then-arrows), compact legends, domain styling presets, and write-check-review cycle in this skill, diagrams have invisible arrows, truncated text, and inconsistent colors. Use whenever the user asks to draw, sketch, visualize, or diagram anything technical - system architecture, microservices topology, C4 diagrams, data pipelines / ETL flows / lakehouse, sequence diagrams, ER diagrams, deployment / Kubernetes diagrams, network topology, flowcharts, decision trees. Includes ready-to-apply color palettes for software engineering, system architecture, and data solutions."
license: MIT
metadata:
  author: vanducng
  version: "1.1.0"
---

# Excalidraw - Technical Diagram Skill

Build professional, consistent Excalidraw diagrams via MCP: tool mechanics, sizing formulas, the write-check-review verification cycle, and domain styling presets.

## Step 0 - Detect Connection

Check **in order**:

1. **MCP server**: tools prefixed `mcp__excalidraw-mcp__*` (e.g. `batch_create_elements`, `describe_scene`) available → use MCP mode. This is the default for this user.
2. **REST fallback**: only if MCP missing - `curl -s $EXPRESS_SERVER_URL/health` returns `{"status":"ok"}`.
3. **Nothing** → auto-bootstrap the MCP config (see below), then tell user to reconnect the MCP so it registers. Do not fake output.

### Auto-bootstrap `.mcp.json`

When neither the MCP tools nor the REST fallback are available:

1. Resolve **project root**: `git rev-parse --show-toplevel` (fallback to CWD if not a git repo). Inside a git worktree this correctly returns the worktree itself - `.mcp.json` must live at the working root the session runs in, so the MCP registers for that session.
2. Derive **project name** = `basename` of the project root.
3. If `<project_root>/.mcp.json` does **not** exist, create it with this exact template (substitute `<project_name>`):

   ```json
   {
     "mcpServers": {
       "excalidraw-mcp": {
         "type": "http",
         "url": "${EXCALIDRAW_MCP_URL}",
         "headers": {
           "Authorization": "Bearer ${EXCALIDRAW_MCP_TOKEN}",
           "X-Tenant-Id": "<project_name>"
         }
       }
     }
   }
   ```

4. If `.mcp.json` already exists, **merge** - add the `excalidraw-mcp` entry under `mcpServers` without clobbering other servers. Skip if `excalidraw-mcp` already present.
5. Tell the user: file written, ensure `EXCALIDRAW_MCP_URL` and `EXCALIDRAW_MCP_TOKEN` are exported in shell env, then reconnect before re-running the skill - **Claude Code:** restart it (or run `/mcp`). **Codex:** the `.mcp.json` above is Claude Code-specific; register the same server with `codex mcp add excalidraw-mcp` or add `[mcp_servers.excalidraw-mcp]` (url + headers) to `~/.codex/config.toml`, then restart Codex.

Never write the bootstrap file outside the resolved project root, and never echo the token value.

The remote canvas is whatever host `EXCALIDRAW_MCP_URL` points at, minus the `/excalidraw/mcp` path. For visual verification beyond `get_canvas_screenshot`, use Chrome DevTools MCP to `take_screenshot` of the canvas URL - `get_canvas_screenshot` sometimes returns blank PNGs.

## Step 1 - Tenant & Project Setup

The remote Excalidraw MCP is multi-tenant. Tenant is selected via the `X-Tenant-Id` header (configured in `.mcp.json`) or via tools.

Before any drawing:

1. `list_tenants` - confirm active tenant
2. `list_projects` - confirm active project; `switch_project` with `createName` if a fresh canvas is wanted
3. `describe_scene` - read existing diagram zones + suggested next placement coordinates

**Never** call `clear_canvas` unless the user explicitly says wipe. Place new diagrams spatially offset (≥300px) from existing ones.

## Core Principles (Read Before Any Diagram)

### 1. Write → Check → Review → Fix (Mandatory Loop)

```
WRITE batch → set_viewport(scrollToContent: true) → screenshot
  → REVIEW against Quality Checklist → FIX issues → re-screenshot
    → only proceed when all checks pass
```

### 2. Use `batch_create_elements` - Not `create_from_mermaid`

`create_from_mermaid` produces overlapping text and broken layouts. Use it only as a quick preview, never for final output. For quality, always plan coordinates and call `batch_create_elements`.

### 3. Two Batches: Shapes First, Arrows Second

Arrow binding (`startElementId`/`endElementId`) requires shapes to exist already. Mixing in one batch causes binding errors.

### 4. `roughness: 0` for Technical Diagrams

Excalidraw defaults to hand-drawn (roughness > 0). For professional system / data / architecture diagrams, set `roughness: 0` on every element. Use `strokeWidth: 2` for arrows.

### 5. Multi-Diagram Canvas

Never clear canvas between diagrams. Place side-by-side or stacked with ≥300px gap. Add a title text element (fontSize 24-28) above each. Group with `group_elements` so `describe_scene` reports it as a named zone.

### 6. Add a Compact Legend When It Clarifies

Include a small legend whenever colors, shapes, stroke styles, or arrow colors encode non-obvious meaning: 3+ semantic node colors, 2+ arrow styles/colors, or mixed ownership/status meanings. Keep it to 3-5 entries that cover only semantics actually used, placed in top-right or bottom-right whitespace outside primary flow paths (fontSize 13-14, one swatch/mini-line + short label). Skip it when labels already make the encoding obvious. A legend explains the visual language - it does not duplicate every node or edge label. Default arrow-legend entries live in `references/styling-presets.md`.

## Sizing Rules (Prevents Truncation)

Excalidraw's font is ~30% wider than typical sans-serif. Use these formulas:

| Shape | Width | Height | fontSize |
|-------|-------|--------|----------|
| Rectangle | `max(200, chars * 11)` | 70 (1 line) / 80 (2) / 100 (3) | 16-20 |
| Diamond (text uses ~50% of bbox - **double**) | `max(400, longestLine * 18)` | `max(160, lines * 50)` | 16 |
| Ellipse (text ~60% of bbox) | `max(280, chars * 14)` | `max(65, lines * 35)` | 16-18 |
| Title text | - | - | 24-28 |

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

Before drawing, load `references/styling-presets.md` and pick the ONE preset matching the diagram type - C4/Software Architecture, Cloud (AWS/GCP/Azure), Data Pipeline/Lakehouse/ETL, UML (Sequence/ER/State/Class), or Kubernetes/Docker. It carries the full fill + stroke + shape tables, stroke-width and edge conventions, layout templates, colorblind-safe substitutes, and text-contrast rules. Don't mix palettes within one diagram unless intentional. Data pipelines run sources top → processing middle → sinks bottom.

### Active Color Budget

Use at most **5 active semantic colors** in any one diagram. Similar components share one color family: all internal services together, all data stores together, all compute/jobs together, all external systems together, all security/blocked paths together.

Treat long preset tables as menus, not a requirement to use every color. If the diagram needs more than five meanings, keep the color and vary shape, stroke style, arrow width, grouping boundary, or label. Neutral gray boundaries/backgrounds and black/white text do not count against the 5-color budget.

## Quality Checklist

After every batch, verify ALL:

| Check | Look For | Fix |
|-------|----------|-----|
| Truncation | Labels cut off, especially in diamonds | Increase width using formulas above |
| Invisible arrows | Connections you cannot trace | Increase gap to ≥120px vertical |
| Arrow label collision | YES/NO labels overlap shapes | Shorten label or widen gap |
| Element overlap | Shapes share space | Reposition with proper spacing |
| Readability | Text legible at 50-70% zoom | Bump fontSize to ≥16 |
| Color consistency | Colors match a single domain preset | Re-pick from one table above |
| Color budget | More than 5 active semantic colors in one diagram | Merge similar components; use shape/stroke/labels for extra meaning |
| Stroke + fill contrast | Light fill + dark stroke (or inverse) | Use the pairs in tables - never light fill + light stroke |
| Legend clarity | Needed semantics absent, or legend lists everything | Add 3-5 used meanings only, or remove if redundant |

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
| Mixing C4 levels in one view | suggests false relationships | one diagram per level (Context, Container, Component) |
| Unlabeled arrows | ambiguous: sync? async? what data? | label every arrow with what + how |
| Labeling shape by tech only ("Lambda") | diagram describes infra, not domain | name first: `CheckoutHandler [Lambda]` |
| Master diagram showing all levels | illegible | split by concern (data flow / deployment / security) |

## Exports

When exporting through `export_scene` or `export_to_image`, write finalized images into the injected `Visuals:` path (it resolves under the umbrella even from a worktree, so exports survive `worktree clean`); fall back to a temp dir only when no `Visuals:` path was injected. Then hand off an openable output location:
- Clickable absolute file link: `[diagram.png](/absolute/path/to/diagram.png)`
- Plain browser URI when useful: `file:///absolute/path/to/diagram.png`
- Remote share URL from `export_to_excalidraw_url`, if generated

Never report only `diagram.png` or another basename; include the canvas URL plus the file path/URI for every finalized exported file.

## Element Creation Cheat Notes

- Always assign a custom `id` to each shape so arrows can bind via `startElementId` / `endElementId`.
- For shape labels (rectangles, diamonds, ellipses): set `text` directly on the element - MCP auto-creates the bound text child.
- Curved arrows: `roundness: { type: 2 }` plus 3+ `points`.
- Elbowed arrows: `elbowed: true`.
- Dashed stroke: `strokeStyle: "dashed"`. Dotted: `strokeStyle: "dotted"`.
- Translucent zone backgrounds: `backgroundColor: "#e9ecef"`, `opacity: 30`.
- Compact legend: small swatch rectangles or 80px mini-lines with short labels; group legend elements with the diagram.

## References

- `references/styling-presets.md` - full color palettes per domain (C4, cloud, data pipeline, UML, K8s), stroke-width and edge conventions, layout templates, accessibility, comprehensive examples.
- `references/cheatsheet.md` - MCP tool list with required params, REST API mapping, env vars, multi-tenancy notes.

When in doubt, re-read the preset table for your domain before drawing. Color and shape consistency matters more than how many shapes you draw.
