# Type: system-architecture

## Purpose
Show services, databases, queues, gateways, and external APIs that together form a running system. Audience: engineers reading a design doc.

## When to use
Trigger words in user prompt:
- "system architecture", "infrastructure", "components", "services"
- mentions of multiple deployable units (frontend + backend + db)
- mentions of cloud services / queues / caches alongside app code

## Visual conventions
- Services: rounded rectangle (radius ~8px), 2px primary-color border, surface fill
- Databases: cylinder, primary-color border, surface fill, monospace label inside
- Queues: horizontal pipe rectangle with rounded short ends; topic name inside
- Caches: cylinder with dashed top ellipse
- External systems / 3rd-party APIs: dashed-border rounded rectangle
- User: stick figure circle near the entry point
- Group services by deployment boundary (e.g. "AWS", "Vercel", "On-prem") with 1px muted boundary box

## Layout direction
Primary flow: **left → right**. User on the left, datastores on the right. Internal services in the middle band. External systems sit on the periphery.

## Level of detail
Include: services, databases, queues, caches, primary external integrations.
Exclude: load balancers, DNS, low-level networking - unless explicitly mentioned in the prompt.

## Image-prompt template
```
Technical system architecture diagram, flat vector illustration, isometric-flat hybrid, clean lines, calm professional aesthetic.

Components: {components}
Connections: {relationships}
Boundaries: {boundaries}

Style: the surface background color, primary-color borders, accent color highlight on the {subject}, muted color for grouping outlines. Use 2px lines for primary connections, 1px for grouping. Solid arrows for sync calls, dashed arrows for async/queue flows.

Typography: sans-serif (Inter aesthetic) for service names; monospace for database/queue identifiers. Min label size ~14pt at 1920px wide.

Layout: primary flow left-to-right, user-actor on the left edge, datastores on the right. Group services inside their deployment boundary with a 1px muted rounded rectangle. ≥40px breathing room around groups. Maximum 5 colors total. Maximum 15 elements.

Do NOT add components not listed. Do NOT use gradients besides the most subtle ambient shading. Do NOT add decorative icons.
```

## SVG-prompt template
```
Output ONLY a valid SVG 1.1 document. Conform exactly to the SVG contract: required root attributes, layer ordering (boundaries → services → connections → labels), class names (.service, .datastore, .queue, .cache, .external-system, .boundary, .connection-sync, .connection-async, .user-actor), inline <style> block for class fills/strokes, <defs> block with arrow markers.

Components: {components}
Connections: {relationships}
Boundaries: {boundaries}

Layout left-to-right, viewBox="0 0 1600 900". User-actor at x≈80, datastores at x≈1400. Apply style-tokens palette via the <style> block. No <script>, no <foreignObject>, no data: URLs.
```

## Golden examples

### Example 1
**User input:** "FastAPI backend with Postgres and Redis cache, Stripe webhook integration"
**Refined image prompt (excerpt):**
> Technical system architecture diagram, flat vector. Components: a User actor (left), a FastAPI service (center, primary-color border, accent highlight as the subject), a Postgres database cylinder (right), a Redis cache cylinder with dashed top (right, below Postgres), a Stripe external-system box with dashed border (top-right). Connections: User → FastAPI (solid sync), FastAPI ↔ Postgres (solid sync), FastAPI → Redis (solid sync), Stripe → FastAPI (dashed async, labeled "webhook"). Surface background, primary-color borders, accent color on FastAPI...

### Example 2
**User input:** "data ingestion pipeline: Kafka → Spark → ClickHouse → Grafana"
**Refined image prompt (excerpt):**
> Technical system architecture diagram, flat vector, left-to-right flow. Components: Kafka pipe (left, with topic label "events"), Spark service (center-left), ClickHouse cylinder (center-right), Grafana service (right, accent highlight as the subject). Connections: solid sync arrows between each. Surface background...

## Common mistakes to avoid
- Do NOT add fictional services not in the description.
- Do NOT use more than 5 colors.
- Do NOT crowd >15 elements onto one diagram - split or zoom out.
- Do NOT label anything in the success-color or error-color colors unless the prompt explicitly mentions ok/error paths.
- Do NOT use gradients beyond subtle ambient shading on the surface.
