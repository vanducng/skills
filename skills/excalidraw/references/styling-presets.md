# Styling Presets - Full Reference

Detailed color palettes, layout templates, and accessibility guidance for technical diagrams. Apply alongside SKILL.md.

## Master Palette Principle

Every color encodes information. No decoration without meaning. Within a single diagram, use at most **5 active semantic colors** from one preset. Treat long preset tables as menus, not instructions to use every color. Similar components share one color family; use shape, stroke style, grouping, and labels for extra distinctions. Gray is reserved for secondary/supporting elements.

### Stroke + Fill Pairs (Always Pair Light Fill With Dark Stroke)

| Role | Fill | Stroke | Text | Use |
|------|------|--------|------|-----|
| Primary | `#a5d8ff` | `#0d6efd` | `#000` | main service, API gateway |
| Secondary | `#e2e3e5` | `#6c757d` | `#000` | supporting / network |
| Accent / warm | `#ffe0b2` | `#f57c00` | `#000` | compute, processing, warnings |
| Cool / storage | `#c8e6c9` | `#388e3c` | `#000` | databases, storage, sinks |
| Async / event | `#f0f4c3` | `#827717` | `#000` | event queues, async tasks |
| Security | `#ffcdd2` | `#d32f2f` | `#fff` | auth, security, denied |
| External | `#fce4ec` | `#c2185b` | `#000` | third-party, external APIs |

## Stroke Width Conventions

| Width | Visual | Use |
|-------|--------|-----|
| 1 | thin | dividers, lifelines, lineage, secondary paths |
| 2 | standard | shapes, main flows, standard arrows |
| 3 | bold | streaming arrows, critical paths, emphasis |
| 4+ | dominant | sparingly - only for ultimate emphasis |

## Minimal Legends

Add a compact legend when visual encodings are meaningful but not self-evident. Keep it to the semantics used in the diagram, not the full palette.

| Include when | Limit |
|--------------|-------|
| 3+ semantic node colors | list only the 3-5 visible roles |
| 2+ arrow colors/styles | show mini-lines for only the edge types used |
| allow/deny, internal/external, batch/stream, sync/async appear together | prefer shape + line style, not color alone |

Default arrow legend entries:

| Meaning | Style | Color | Width |
|---------|-------|-------|-------|
| Sync/API call | solid | `#1976d2` | 2 |
| Batch/data load | solid | `#757575` | 2 |
| Stream/event | solid | `#f57c00` | 3 |
| Async/queue | dashed | `#f57c00` | 2 |
| Lineage/dependency | dotted | `#9c27b0` | 1 |
| Denied/security block | solid | `#d32f2f` | 3 |

The default arrow legend uses five colors: blue, gray, orange, purple, and red. Stream and async share orange; line style and width carry the distinction.

Place the legend in unused top-right or bottom-right space. Use fontSize 13-14, short labels, and no more than one compact legend per diagram.

## C4 Color Assignment (Full)

| C4 Level | Fill | Stroke | Shape | Label |
|----------|------|--------|-------|-------|
| Context (System) | `#e3f2fd` | `#1976d2` | rectangle | `System Name\n[Software System]` |
| Container | `#a5d8ff` | `#0d6efd` | rounded rect | `Service\n[Container: Tech]` |
| Component | `#b9e0fb` | `#0c8599` | rectangle | `Component\n[Component: Role]` |
| Code/Class | `#e8f5e9` | `#388e3c` | small rect | `class()` |
| Person | `#fff3e0` | `#f57c00` | hexagon | `User\n[Person]` |
| Database | `#f3e5f5` | `#7b1fa2` | cylinder | `DB\n[PostgreSQL]` |
| External | `#fce4ec` | `#c2185b` | dashed rect | `Stripe\n[External]` |

## Cloud Architecture (AWS Categories)

| Category | Fill | Stroke | Examples |
|----------|------|--------|----------|
| Compute | `#ffe0b2` | `#f57c00` | EC2, Lambda, ECS, Fargate, Batch |
| Storage | `#c8e6c9` | `#388e3c` | S3, EBS, EFS, Glacier, FSx |
| Database | `#ffccbc` | `#d84315` | RDS, DynamoDB, Aurora, DocumentDB |
| Network | `#e1bee7` | `#7b1fa2` | VPC, ALB/NLB, Route 53, CloudFront, API Gateway |
| Security | `#ffcdd2` | `#d32f2f` | IAM, KMS, Secrets Manager, WAF, Shield, Cognito |
| Analytics | `#ede7f6` | `#3f51b5` | Athena, Redshift, EMR, QuickSight, Glue |
| Messaging | `#fff9c4` | `#fbc02d` | SQS, SNS, Kinesis, EventBridge, MSK |
| Monitoring | `#bbdefb` | `#1976d2` | CloudWatch, X-Ray, CloudTrail |

GCP and Azure: keep their primary blue (`#4285F4`, `#0078D4`) for vendor branding when shown alongside, but use the same category colors for consistency across multi-cloud diagrams.

## Data Pipeline Components

| Component | Shape | Fill | Stroke | Label |
|-----------|-------|------|--------|-------|
| Source DB | cylinder | `#b3e5fc` | `#0097a7` | `PostgreSQL\n[Source]` |
| Source API | rectangle | `#b3e5fc` | `#0097a7` | `REST API\n[Source]` |
| Source files / S3 | rectangle | `#b3e5fc` | `#0097a7` | `S3 raw\n[Source]` |
| Stream broker | hexagon | `#f0f4c3` | `#827717` | `Kafka\n[topic: events]` |
| Batch job | rounded rect | `#fff9c4` | `#fbc02d` | `dbt run\n[Daily 02:00]` |
| Stream processor | hexagon | `#ffecb3` | `#f57f17` | `Spark Stream\n[Processor]` |
| Workflow / orchestrator | rectangle | `#fff9c4` | `#fbc02d` | `Airflow DAG\n[Orchestrator]` |
| Lakehouse layers | cylinder | `#c8e6c9` | `#388e3c` | `Bronze / Silver / Gold` |
| Warehouse | cylinder | `#c8e6c9` | `#388e3c` | `Snowflake\n[Warehouse]` |
| Feature store | rectangle | `#d1c4e9` | `#3f51b5` | `Feast\n[Feature Store]` |
| ML model | rectangle | `#d1c4e9` | `#3f51b5` | `Recommender\n[Model]` |
| BI dashboard | rounded rect | `#e1bee7` | `#7b1fa2` | `Looker\n[Dashboard]` |
| Catalog / metadata | rectangle, dashed | `#e0f7fa` | `#00838f` | `DataHub\n[Catalog]` |

### Data Edge Conventions

| Edge | Style | Color | Width | Label example |
|------|-------|-------|-------|---------------|
| Batch | solid | `#757575` | 2 | `daily 02:00` |
| Stream | solid | `#f57c00` | **3** | `topic: orders` |
| Async / queue | dashed | `#f57c00` | 2 | `queue: tasks` |
| Lineage (parent→child) | dotted | `#9c27b0` | 1 | `derived from` |
| Sync API | solid | `#1976d2` | 2 | `POST /v1/...` |
| CDC | solid + thick | `#0097a7` | 3 | `Debezium / WAL` |

## Kubernetes Deployment

K8s blue is `#326ce5` - use as cluster-level boundary.

| Component | Shape | Fill | Stroke | Notes |
|-----------|-------|------|--------|-------|
| Cluster | rectangle, opacity 30 | `#e3f2fd` | `#326ce5` | bounding box, label `Cluster: name` |
| Namespace | rectangle, opacity 20 | `#e0f7fa` | `#00838f` | nested in cluster |
| Node | rectangle | `#bbdefb` | `#1976d2` | label with capacity (`3 CPU, 8 GB`) |
| Pod | rounded rect | `#a5d8ff` | `#0d6efd` | `pod-name\n[image:tag]` |
| Deployment / StatefulSet | rounded rect | `#90caf9` | `#1565c0` | parent of pods |
| Service (ClusterIP / LB) | hexagon | `#b2dfdb` | `#00695c` | `svc\n[ClusterIP]` |
| Ingress | hexagon | `#80cbc4` | `#00897b` | label with host |
| HPA | small rounded rect | `#fff9c4` | `#fbc02d` | `HPA: 2-10 replicas` |
| PVC / Storage | cylinder | `#f3e5f5` | `#7b1fa2` | `PVC: name [10Gi]` |
| ConfigMap / Secret | small rounded rect | `#fffde7` | `#f57f17` | `cm-name` |
| NetworkPolicy | rectangle, dashed | `#ffcdd2` | `#d32f2f` | label `allow` / `deny` |
| ServiceAccount / RBAC | rectangle | `#e8eaf6` | `#3949ab` | rare, only when relevant |

### K8s Edge Conventions

| Connection | Style | Color | Width | Label |
|------------|-------|-------|-------|-------|
| API call | solid | `#1976d2` | 2 | `:6443 gRPC`, `:443 HTTPS` |
| Watches / informers | dashed | `#f57c00` | 2 | `watches`, `syncs` |
| Volume mount | dotted | `#7b1fa2` | 1 | `mount /data` |
| Network policy allow | solid | `#388e3c` | 3 | `allow :8080` |
| Network policy deny | solid | `#d32f2f` | 3 | `deny` |
| External traffic | solid | `#f57c00` | 3 | `ingress 443` |

## Layout Templates

### Three-Tier Web App (top-down)
```
[Users] → [Frontend] → [Backend API] → [Database]
                            ↓
                          [Cache]
```

### Event-Driven (fan-out)
```
              [Source Service]
                    ↓ (event)
            [Event Bus / Kafka]
           ↓        ↓        ↓
    [Handler 1] [Handler 2] [Handler 3]
           ↓        ↓        ↓
              [Sink / Lake]
```

### Lambda Architecture (data)
```
Batch Layer:                       Speed Layer:
[Historical] → [Batch Job]         [Stream] → [Processor]
                  ↓                              ↓
            [Data Lake]                 [Real-time Views]
                  ↓                              ↓
            [Batch Views]
                  ↓                              ↓
                    [Combined Result / Serving Layer]
                              ↓
                         [User Query]
```

### Modern ELT Lakehouse (Bronze / Silver / Gold)
```
Sources (top row):  [Postgres] [APIs]  [S3 raw]  [Kafka]
                       ↓ batch  ↓ batch ↓ batch  ↓ stream
Bronze (raw):       [───────── Bronze layer S3 ─────────]
                       ↓ dbt staging
Silver (cleaned):   [───────── Silver layer ────────────]
                       ↓ dbt marts
Gold (business):    [───── Gold marts (Snowflake) ──────]
                       ↓                ↓             ↓
                   [BI dashboards] [ML models]  [Reverse ETL]
```

### Microservices + Service Mesh
```
[─── Cluster ─────────────────────────────────────────]
[ Ingress → Gateway                                    ]
[    ↓                                                 ]
[ [svc A]──mTLS──→[svc B]──→[svc C]                   ]
[    ↓             ↓                                   ]
[ [Postgres]   [Redis]                                 ]
[                                                      ]
[ Sidecars (Envoy) on each pod, control plane: Istio   ]
[──────────────────────────────────────────────────────]
                ↓ external
            [Stripe / SendGrid / ...]
```

### C4 Container View Skeleton
```
[Person] ───→ [─────────── My System ────────────────]
              [                                       ]
              [ [Frontend]──→[API]──→[Worker]         ]
              [                ↓        ↓             ]
              [           [Postgres] [Queue]          ]
              [───────────────────────────────────────]
                                          ↓
                                  [External: Stripe]
```

## Accessibility (Colorblind-Safe Substitutes)

For diagrams shared with audiences with red-green colorblindness:

| Original | Colorblind-safe alt | When to use |
|----------|---------------------|-------------|
| `#0d6efd` primary | `#0173b2` | always safe |
| `#388e3c` storage green | `#029e73` | substitute when paired with red |
| `#dc3545` danger red | `#cc78bc` (purple) | when paired with green |
| `#ffc107` warning yellow | `#de8f05` | always safe |
| `#0dcaf0` info | `#ca9161` (brown) | high contrast variant |

When red and green appear together, **also encode with line style** (dashed for one) - never rely on color alone.

## Text Contrast Rules

- Min text contrast on white: `#757575` or darker.
- Light fill → dark text. Dark fill (red, dark blue, dark purple) → light text (`#fff`).
- Never light text on light fill - invisible.
- Aim for WCAG AA (4.5:1 contrast ratio) on all labels.

## Layout Discipline

- Align all shapes to an invisible 8px or 16px grid.
- Min spacing between unconnected elements: 40px.
- Min spacing between connected (bound by arrow) elements: 120px vertical / 140px horizontal.
- Primary element gets more whitespace; supporting elements cluster tighter.
- Top-down for data flow, time progression, and abstraction-level decomposition.

## Anti-Patterns (Domain-Specific)

| Mistake | Why fails | Fix |
|---------|-----------|-----|
| Using 6+ category colors in one diagram | viewer overwhelmed | merge similar components and cap active colors at 5 |
| C4 Container view that contains internal Components | mixes abstraction levels | split into Container view + per-container Component view |
| Same shape (rectangle) for source AND warehouse in data diagrams | breaks shape semantics | cylinder for stores, rect for compute |
| Light gray arrows on white background | invisible | minimum stroke darkness `#757575`, ideally `#000`-derived |
| Streaming and batch arrows visually identical | viewer cannot tell async from sync | thick orange = stream, thin gray = batch |
| Putting NetworkPolicy on a node-level diagram | wrong abstraction layer | NetworkPolicy belongs on namespace/pod-level diagram |
| Drawing K8s pods at cluster scale | clutter | choose one zoom level: cluster, namespace, or pod |
| External system rendered identical to internal | reader assumes ownership | dashed stroke + pink fill family |
| Async event arrow without topic name | meaningless | always label `topic: name` or `queue: name` |
| Mixing UML stereotypes (`«interface»`) with C4 brackets (`[Container]`) | inconsistent notation | pick one notation per diagram |

## Implementation Checklist

Before declaring a diagram done, verify:

- [ ] All elements use a single domain preset (no palette mixing)
- [ ] No more than 5 active semantic colors in one diagram
- [ ] Each color/shape used has a documented semantic role
- [ ] Stroke + fill pairs have visible contrast
- [ ] All text legible at 50-70% zoom (fontSize ≥16)
- [ ] Same shape always means the same thing in this diagram
- [ ] Every arrow labeled with what flows + how (sync/async/stream/batch)
- [ ] Aligned to grid, ≥40px between unconnected, ≥120px between connected
- [ ] Primary elements have more breathing room than supporting
- [ ] One concern per diagram (not "everything")
- [ ] Compact legend included when color/shape/arrow styles are non-obvious
- [ ] Colorblind-safe alternative palette ready when red/green appear together
- [ ] No mixing C4 abstraction levels
- [ ] No invisible connections (light arrow on light bg)
- [ ] No unlabeled resources (Lambda → name first, e.g. `CheckoutHandler [Lambda]`)
