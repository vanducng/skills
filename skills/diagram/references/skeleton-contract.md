# Skeleton Contract — pass-1 (YAML)

You are emitting a **YAML skeleton** describing a diagram's structure. This is pass-1 of a two-pass pipeline. **DO NOT emit SVG, pixel coordinates, colors, or styling.** Pass-2 paints the SVG; Python computes layout. Your job is _what to show_, not _where_ or _how it looks_.

## YAML schema

```yaml
# Top level
type: system-architecture        # one of the supported types (see list below)
preset: warm                     # warm | mono | pastel | cyberpunk
title: "vd CLI architecture"     # OPTIONAL one-line caption
groups:                          # ordered; each becomes a layer/lane
  - name: upstream               # snake_case identifier; unique within file
    label: "Upstream sources"    # OPTIONAL human label
elements:                        # flat list; each element references a group by name
  - name: cli                    # snake_case identifier; unique within file
    kind: service                # see `kind` enum below
    group: core                  # MUST reference an existing group's name
    label: "vd CLI"              # display text, ≤ 40 chars
    subject: true                # OPTIONAL; max 1 element per diagram
    note: "Go binary"            # OPTIONAL secondary text below label
edges:                           # ordered
  - from: user                   # MUST be an existing element name
    to: cli                      # MUST be an existing element name
    label: "commands"            # OPTIONAL; ≤ 4 words
    kind: sync                   # sync | async | error
    bidirectional: false         # OPTIONAL; default false
notes:                           # OPTIONAL free-floating annotations
  - attached: cli                # MUST be an existing element name
    position: below              # above | below | left | right
    text: "Single binary"
```

### Supported `type` values
`system-architecture`, `data-flow`, `workflow`, `sequence`, `er-diagram`, `state-machine`, `c4-context`, `c4-container`.

### Supported `kind` values for elements
`service`, `datastore`, `external-system`, `cache`, `queue`, `actor`, `process`, `decision`, `state`, `entity`.

### Supported edge `kind` values
`sync`, `async`, `error`.

## Validation rules (every one is enforced — emit nothing outside these)

1. **Allowed top-level keys: exactly** `type`, `preset`, `groups`, `elements`, `edges` (required) and `title`, `notes` (optional). Any other top-level key — `caption`, `metadata`, `description`, `version`, etc. — is **rejected**.
2. `type` MUST be one of the eight supported diagram types.
3. `preset` MUST be one of `warm | mono | pastel | cyberpunk`.
4. Every element's `group` MUST reference an existing group by `name`.
5. Every edge's `from` and `to` MUST reference an existing element by `name`.
6. Every note's `attached` MUST reference an existing element by `name`.
7. Element `kind` MUST be in the kind enum; edge `kind` MUST be in the edge-kind enum.
8. Element `name` and group `name` MUST match `^[a-z][a-z0-9_-]*$` — start lower-case letter, then lower-case letters / digits / underscore / hyphen.
9. AT MOST one element with `subject: true`.
10. No duplicate element `name`s; no duplicate group `name`s.
11. Element `label` ≤ 40 chars; edge `label` ≤ 4 words.

## Examples

### Minimal — system-architecture, 2 groups, 4 elements, 3 edges

```yaml
type: system-architecture
preset: warm
title: "vd CLI architecture"
groups:
  - name: client
    label: "Client side"
  - name: server
    label: "Server side"
elements:
  - name: user
    kind: actor
    group: client
    label: "User"
  - name: cli
    kind: service
    group: client
    label: "vd CLI"
    subject: true
  - name: api
    kind: service
    group: server
    label: "Plugin API"
  - name: db
    kind: datastore
    group: server
    label: "skills.lock"
edges:
  - {from: user, to: cli, label: "runs", kind: sync}
  - {from: cli, to: api, label: "requests", kind: sync}
  - {from: api, to: db, label: "reads", kind: sync}
```

### Richer — system-architecture, 4 groups, 10 elements, 7 edges, 2 notes

```yaml
type: system-architecture
preset: warm
title: "Microservices platform"
groups:
  - name: edge
    label: "Edge"
  - name: core
    label: "Core services"
  - name: data
    label: "Data layer"
  - name: external
    label: "External"
elements:
  - {name: user, kind: actor, group: edge, label: "User"}
  - {name: gateway, kind: service, group: edge, label: "API Gateway", subject: true}
  - {name: auth, kind: service, group: core, label: "Auth"}
  - {name: orders, kind: service, group: core, label: "Orders"}
  - {name: billing, kind: service, group: core, label: "Billing"}
  - {name: queue, kind: queue, group: core, label: "Events"}
  - {name: db, kind: datastore, group: data, label: "Postgres"}
  - {name: cache, kind: cache, group: data, label: "Redis"}
  - {name: stripe, kind: external-system, group: external, label: "Stripe"}
  - {name: sendgrid, kind: external-system, group: external, label: "SendGrid"}
edges:
  - {from: user, to: gateway, label: "HTTPS", kind: sync}
  - {from: gateway, to: auth, label: "verify", kind: sync}
  - {from: gateway, to: orders, label: "RPC", kind: sync}
  - {from: orders, to: billing, kind: async}
  - {from: orders, to: queue, kind: async}
  - {from: billing, to: stripe, label: "charge", kind: sync}
  - {from: orders, to: db, label: "writes", kind: sync}
notes:
  - {attached: gateway, position: below, text: "TLS terminates here"}
  - {attached: queue, position: right, text: "RabbitMQ"}
```

### Per-type examples

**data-flow** — pipeline of transformations (sources → process → sinks):

```yaml
type: data-flow
preset: warm
title: "ETL pipeline"
groups:
  - {name: source, label: "Sources"}
  - {name: process, label: "Processing"}
  - {name: sink, label: "Sinks"}
elements:
  - {name: kafka, kind: queue, group: source, label: "Kafka topics"}
  - {name: spark, kind: process, group: process, label: "Spark", subject: true}
  - {name: ch, kind: datastore, group: sink, label: "ClickHouse"}
  - {name: graf, kind: external-system, group: sink, label: "Grafana"}
edges:
  - {from: kafka, to: spark, label: "stream", kind: async}
  - {from: spark, to: ch, label: "writes", kind: sync}
  - {from: ch, to: graf, label: "queries", kind: sync}
```

**workflow** — process map with ownership lanes, decisions, queues, and terminal outcomes:

```yaml
type: workflow
preset: warm
title: "Checkout fulfillment"
groups:
  - {name: customer, label: "Customer"}
  - {name: commerce, label: "Commerce app"}
  - {name: risk, label: "Risk"}
  - {name: warehouse, label: "Warehouse"}
elements:
  - {name: cart, kind: process, group: customer, label: "Review cart"}
  - {name: order, kind: process, group: commerce, label: "Submit order", subject: true}
  - {name: fraud, kind: decision, group: risk, label: "Risk flagged?"}
  - {name: review, kind: process, group: risk, label: "Manual review"}
  - {name: pick, kind: queue, group: warehouse, label: "Pick ticket"}
  - {name: shipped, kind: state, group: warehouse, label: "Shipped"}
edges:
  - {from: cart, to: order, label: "checkout", kind: sync}
  - {from: order, to: fraud, label: "score", kind: sync}
  - {from: fraud, to: review, label: "yes", kind: async}
  - {from: fraud, to: pick, label: "no", kind: async}
  - {from: review, to: pick, label: "approve", kind: sync}
  - {from: pick, to: shipped, label: "fulfill", kind: sync}
```

**c4-context** — system boundary with users + external systems. Use larger labels; mark the system-of-interest with `subject: true`.

```yaml
type: c4-context
preset: warm
title: "Banking app — system context"
groups:
  - {name: users, label: "Users"}
  - {name: system, label: "System"}
  - {name: external, label: "External systems"}
elements:
  - {name: customer, kind: actor, group: users, label: "Customer"}
  - {name: cbs, kind: service, group: system, label: "Core Banking", subject: true}
  - {name: gw, kind: external-system, group: external, label: "Payment Gateway"}
edges:
  - {from: customer, to: cbs, label: "uses", kind: sync}
  - {from: cbs, to: gw, label: "settles", kind: sync}
```

**c4-container** — internal containers within a system. Use `service` for app/API tiers, `datastore` for DBs.

```yaml
type: c4-container
preset: mono
title: "Internet banking — containers"
groups:
  - {name: client, label: "Client apps"}
  - {name: api, label: "API tier"}
  - {name: data, label: "Data tier"}
elements:
  - {name: web, kind: service, group: client, label: "Web SPA"}
  - {name: api, kind: service, group: api, label: "REST API", subject: true}
  - {name: accounts, kind: datastore, group: data, label: "Accounts DB"}
edges:
  - {from: web, to: api, label: "HTTPS", kind: sync}
  - {from: api, to: accounts, label: "reads", kind: sync}
```

**er-diagram** — entities + relationships. Use `entity` kind. Group by user-perceived clusters (party / order / catalog) — Phase 7 punts cluster-by-density.

```yaml
type: er-diagram
preset: warm
title: "E-commerce schema"
groups:
  - {name: party, label: "Party"}
  - {name: order, label: "Order"}
  - {name: catalog, label: "Catalog"}
elements:
  - {name: customer, kind: entity, group: party, label: "Customer"}
  - {name: order, kind: entity, group: order, label: "Order", subject: true}
  - {name: orderline, kind: entity, group: order, label: "OrderLine"}
  - {name: product, kind: entity, group: catalog, label: "Product"}
edges:
  - {from: customer, to: order, label: "places", kind: sync}
  - {from: order, to: orderline, label: "has", kind: sync}
  - {from: orderline, to: product, label: "refs", kind: sync}
```

## Anti-patterns to AVOID

- **Don't emit SVG.** No `<svg>`, no `<rect>`, no `<path>`, no XML.
- **Don't emit pixel coordinates.** No `x:`, `y:`, `width:`, `height:`.
- **Don't emit colors or hex.** No `fill:`, no `#` color literals.
- **Don't quote names with backticks or angle brackets.** `name: "<cli>"` is wrong; use `name: cli`.
- **Don't invent new `kind` values.** Stay inside the enum; if nothing fits, use `service` as the safe default.
- **Don't mark more than one element with `subject: true`.** At most one per diagram.
- **Don't write edge labels longer than 4 words.** If you need more, split into two edges or drop the label.
- **Don't add unknown top-level keys** (`caption`, `metadata`, `description` — all rejected).
- **Don't use camelCase or PascalCase** for `name` fields. Snake_case only.

## Response format

Emit **ONLY the YAML**. No markdown fences (```yaml, ```), no preamble, no commentary. The first character of your response is `t` (start of `type:`).
