# Type: c4-container

## Purpose
Zoom one level into the subject system: show internal containers (web app, API, database, queue, worker) inside the system boundary, plus the external systems they talk to. Audience: engineers onboarding to the system.

## When to use
Trigger words:
- "C4 container", "container diagram"
- mentions of internal containers (web, api, mobile, db, queue, worker) inside one system
- "what's inside [system]"

## Visual conventions
- System boundary: large rounded rectangle, **1px muted border, no fill**, label "Subject System [Software System]" at top-left
- Containers: rounded rectangle, primary-color border, surface fill, label `[Container: <tech>]` in muted italic under the name (e.g. "Web App [Container: Next.js]")
- External systems: dashed-border rounded rectangle outside the boundary, label `[Software System]`
- External users: stick figure outside the boundary
- Relationships: solid arrows with verb + protocol label (e.g. "Reads from, [SQL/TLS]")

## Layout direction
Containers arranged inside the system boundary; external entities outside. Internal flow typically left → right (frontend → backend → datastore).

## Level of detail
Include: every internal container, its tech choice in italics, every external system, every relationship with verb + protocol.
**Exclude: code-level structure (classes, functions).** That's the next C4 zoom (component diagram), out of scope here.

## Image-prompt template
```
C4 container diagram, flat vector, calm professional aesthetic.

System boundary (label): {boundary_label}
Containers (with tech stack in italic): {containers}
External users: {users}
External systems (dashed border): {externals}
Relationships (verb + [protocol]): {relationships}

Style: the surface background color, primary color for container borders/text, accent color on the {focal container} if any, muted color for the system boundary outline and the "[Container: ...]" tech labels. Boundary box uses 1px muted dashed-or-solid line, no fill. Containers inside use 2px primary-color solid borders.

Typography: sans-serif for container names (semibold), muted italic sans-serif for the "[Container: <tech>]" tag, sans-serif for relationship labels, monospace inside square brackets for protocol/format (e.g. [JSON/HTTPS]).

Layout: subject system boundary fills most of the canvas. Containers inside flow left-to-right. External users and external systems sit outside the boundary, connected through arrows that cross the boundary line. ≥40px breathing room. Maximum 8 internal containers.

Do NOT add code-level detail. Do NOT skip the [Container: ...] tech labels.
```

## SVG-prompt template
```
Output ONLY valid SVG 1.1 per the SVG contract. Use .boundary for the system box, .service for containers, .external-system for externals, .user-actor for users, .connection-sync for relationships.

Boundary label: {boundary_label}
Containers (name + tech): {containers}
External users: {users}
External systems: {externals}
Relationships (verb + protocol): {relationships}

viewBox="0 0 1600 900". Boundary as a large rounded rect, fill="none", stroke="var(--muted)", stroke-width="1". Containers inside: 240px wide, header line is the name in semibold, second line is "[Container: tech]" in <text class="muted">. Relationship labels in two parts: verb on top line, "[protocol]" in monospace below.
```

## Golden examples

### Example 1
**User input:** "C4 container for an internal blog: Next.js frontend, FastAPI backend, Postgres database, Redis cache, used by employees, sends emails via SendGrid"
**Refined image prompt (excerpt):**
> C4 container. Boundary: "Internal Blog [Software System]". Containers: Web App "[Container: Next.js]" (left), API "[Container: FastAPI]" (center), Database "[Container: Postgres]" (right), Cache "[Container: Redis]" (right, below DB). External user: Employee (left, outside boundary). External system: SendGrid (right, outside, dashed). Relationships: Employee "views/posts via [HTTPS]" → Web App; Web App "API calls [JSON/HTTPS]" → API; API "reads/writes [SQL/TLS]" → Database; API "caches [RESP]" → Cache; API "sends emails via [HTTPS]" → SendGrid.

### Example 2
**User input:** "Checkout container view: React mobile app, Node.js BFF, Python orders service, MySQL, RabbitMQ for payment events, Stripe outside"
**Refined image prompt (excerpt):**
> C4 container. Boundary: "Checkout [Software System]". Containers: Mobile App "[Container: React Native]", BFF "[Container: Node.js]", Orders Service "[Container: Python/FastAPI]", Database "[Container: MySQL]", Queue "[Container: RabbitMQ]". External user: Customer. External system: Stripe (dashed). Relationships labeled with verb + protocol.

## Common mistakes to avoid
- Do NOT skip the `[Container: <tech>]` tag — it's the differentiator from system-architecture.
- Do NOT show code-level components (classes, modules).
- Do NOT use the success/error colors decoratively.
- Do NOT exceed 8 internal containers.
