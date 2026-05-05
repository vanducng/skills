# Excalidraw MCP Cheatsheet

## Connection

- **Remote MCP** (this user's setup): `https://mcp.dataplanelabs.com/excalidraw/mcp`. Auth via `Authorization: Bearer ${EXCALIDRAW_MCP_TOKEN}`. Tenant via `X-Tenant-Id` header.
- **Canvas (visual)**: `https://draw.vanducng.dev` — open in browser or screenshot via Chrome DevTools MCP.
- **Local install** (fallback): `sanjibdevnathlabs/mcp-excalidraw-local`. Canvas at `http://localhost:3000`. Health: `GET /health`.
- **Persistence**: server-side SQLite, scoped per tenant.

## MCP Tools (32 total)

### Element CRUD
| Tool | Required params | Notes |
|------|-----------------|-------|
| `create_element` | `type`, `x`, `y` | single element |
| `get_element` | `id` | |
| `update_element` | `id` | partial update |
| `delete_element` | `id` | |
| `query_elements` | (optional) `type` | filter by type |
| `batch_create_elements` | `elements[]` | **preferred** for diagrams |
| `duplicate_elements` | `elementIds[]`, optional offset | clone with offset |
| `search_elements` | `query` | full-text label/text |
| `element_history` | optional `elementId`, `limit` | version history |

### Layout & Organization
| Tool | Required params |
|------|-----------------|
| `align_elements` | `elementIds[]`, `alignment` (left/center/right/top/middle/bottom) |
| `distribute_elements` | `elementIds[]`, `direction` (horizontal/vertical) |
| `group_elements` | `elementIds[]` |
| `ungroup_elements` | `groupId` |
| `lock_elements` | `elementIds[]` |
| `unlock_elements` | `elementIds[]` |

### Scene Awareness
| Tool | Notes |
|------|-------|
| `describe_scene` | groups, bounding box, **suggested next placement** |
| `get_canvas_screenshot` | optional `background`. May return blank — fall back to Chrome DevTools |
| `get_resource` | `resource` (scene/library/theme/elements) |
| `read_diagram_guide` | server-side best practices guide |

### File I/O & Export
| Tool | Required | Notes |
|------|----------|-------|
| `export_scene` | optional `filePath` | dumps `.excalidraw` JSON |
| `import_scene` | `mode` (replace/merge), `filePath` or `data` | |
| `export_to_image` | `format` (png/svg), optional `filePath`, `background` | needs canvas browser open |
| `export_to_excalidraw_url` | (none) | shareable excalidraw.com URL — may be blocked |

### State Management
| Tool | Required | Notes |
|------|----------|-------|
| `clear_canvas` | (none) | wipes active project. Don't call without explicit user ask |
| `snapshot_scene` | `name` | named snapshot |
| `restore_snapshot` | `name` | may not reload into view — re-fetch elements if blank |

### Viewport
| Tool | Notes |
|------|-------|
| `set_viewport` | `scrollToContent: true` (auto-fit), `scrollToElementId`, manual `zoom`/`offsetX`/`offsetY` |

### Multi-Tenancy
| Tool | Required |
|------|----------|
| `list_tenants` | (none) |
| `switch_tenant` | `tenantId` |

### Projects (Within a Tenant)
| Tool | Required |
|------|----------|
| `list_projects` | (none) |
| `switch_project` | optional `projectId`, `createName`, `createDescription` |

### Conversion
| Tool | Notes |
|------|-------|
| `create_from_mermaid` | ⚠ low quality — use `batch_create_elements` for production |

## MCP vs REST Format Differences

| Concept | MCP | REST |
|---------|-----|------|
| Shape label | `"text": "My Label"` | `"label": {"text": "My Label"}` |
| Arrow binding | `"startElementId"` / `"endElementId"` | `"start": {"id": ...}` / `"end": {"id": ...}` |
| `fontFamily` | number or string | string |
| Tenant scoping | active tenant auto | `X-Tenant-Id` header on every request |

## Element Property Reference

| Property | Values | Notes |
|----------|--------|-------|
| `type` | rectangle, ellipse, diamond, text, arrow, line, freedraw, image | |
| `strokeColor` | hex | outline |
| `backgroundColor` | hex | fill |
| `fillStyle` | solid, hachure, cross-hatch | solid for clean technical diagrams |
| `strokeWidth` | 1 (thin), 2 (default), 3 (bold), 4+ | use 3 for streaming/critical paths |
| `strokeStyle` | solid, dashed, dotted | dashed = async/external; dotted = mount/lineage |
| `roughness` | 0 (clean), 1 (sketch), 2 (rough) | always 0 for technical diagrams |
| `opacity` | 0–100 | 30 for translucent zone backgrounds |
| `fontFamily` | 1–8 (Virgil/Helvetica/Cascadia/...) | 5 = Excalifont (default), 2 = Helvetica for cleanest reads |
| `fontSize` | 16–28 | 16-20 shapes, 24-28 titles |
| `roundness` | `{type: 2}` | curved arrows or rounded rectangles |
| `elbowed` | true | elbowed arrows |
| `points` | `[[x,y]...]` or `[{x,y}...]` | both forms accepted |
| `startElementId` / `endElementId` | string id | arrow binding |
| `endArrowhead` | "arrow", "triangle", null | direction marker |

## REST API (HTTP) Quick Reference

All endpoints accept optional `X-Tenant-Id` to scope.

### Elements
- `GET /api/elements` · `GET /api/elements/:id` · `POST /api/elements` · `PUT /api/elements/:id` · `DELETE /api/elements/:id`
- `DELETE /api/elements/clear` · `GET /api/elements/search?type=...`
- `POST /api/elements/batch` (batch create) · `POST /api/elements/sync` (replace all)
- `POST /api/elements/from-mermaid`

### Tenants
- `GET /api/tenants` · `GET /api/tenant/active` · `PUT /api/tenant/active`

### Export / Viewport / Snapshots / System
- `POST /api/export/image` · `POST /api/viewport`
- `POST /api/snapshots` · `GET /api/snapshots` · `GET /api/snapshots/:name`
- `GET /health` · `GET /api/sync/status`

## Multi-Tenancy

- Tenant maps to a workspace identity (e.g. `infra`, `home`).
- Project groups diagrams within a tenant — switch/create via `switch_project`.
- Hierarchy: Tenant → Project → Elements.
- Concurrent sessions: each sends `X-Tenant-Id` for isolation. SQLite `busy_timeout` handles writes.

## Environment Variables (Local Mode)

| Var | Default | Description |
|-----|---------|-------------|
| `CANVAS_PORT` | 3000 | canvas server listen port |
| `EXPRESS_SERVER_URL` | `http://localhost:3000` | full canvas URL |
| `EXCALIDRAW_EXPORT_DIR` | cwd | base dir for exports (path traversal protection) |

## Common Recipes

### Bind an arrow between two shapes
```json
{
  "type": "arrow",
  "x": 0, "y": 0,
  "startElementId": "box-a",
  "endElementId": "box-b",
  "endArrowhead": "arrow",
  "strokeColor": "#1976d2",
  "strokeWidth": 2,
  "roughness": 0,
  "text": "calls"
}
```

### Translucent zone (VPC, cluster, namespace)
```json
{
  "type": "rectangle",
  "x": 0, "y": 0, "width": 1200, "height": 600,
  "backgroundColor": "#e9ecef",
  "strokeColor": "#326ce5",
  "fillStyle": "solid",
  "opacity": 30,
  "roughness": 0
}
```

### Cylinder approximation (database)
```
ellipse on top  (x, y,        w, 30)
rectangle below (x, y + 15,   w, 70)   strokeStyle: solid
ellipse bottom  (x, y + 70,   w, 30)   (optional, partial cover)
```
Or simply: rectangle with `roundness: {type: 2}` and label `[PostgreSQL]`.

### Dashed external system
```json
{
  "type": "rectangle",
  "strokeStyle": "dashed",
  "backgroundColor": "#fce4ec",
  "strokeColor": "#c2185b",
  "text": "Stripe\n[External]"
}
```

## Verification Loop

```
batch_create_elements (shapes)
  → batch_create_elements (arrows)
    → set_viewport(scrollToContent: true)
      → wait 1-2s
        → get_canvas_screenshot                       # primary
            (if blank) → Chrome DevTools take_screenshot of canvas URL  # fallback
        → run Quality Checklist (SKILL.md)
        → fix issues with update_element / delete_element
        → re-screenshot, repeat
```
