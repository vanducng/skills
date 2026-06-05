# Type: workflow

## Purpose
Show a business or operational process: steps, ownership, decisions, handoffs, queues, and terminal outcomes. Audience: engineers, operators, product teams, and reviewers who need to see how work moves.

## When to use
Trigger words:
- "workflow", "process", "approval", "handoff", "swimlane"
- "from request to fulfillment", "review flow", "onboarding flow"
- mentions of teams, systems, manual steps, queues, retries, or SLAs

## Visual conventions
- Process step: rounded rectangle, label = action verb + object (`Review order`)
- Decision: diamond or `.decision`-kind shape, label as a short question (`Risk flagged?`)
- Actor/team lane: boundary group with muted title (`Customer`, `Ops`, `Warehouse`)
- System step: rectangle with bracket tag (`Fraud API\n[System]`)
- Queue/wait state: queue shape, label includes SLA or trigger (`Payment queue\n[SLA 5m]`)
- Terminal outcome: state-like rounded rectangle, label = `Approved`, `Rejected`, `Shipped`

## Layout direction
Primary flow runs **left → right**. Use groups as swimlanes by team, system, or stage. In the YAML skeleton, order groups top-to-bottom as swimlane rows and order elements in rough process order. The deterministic SVG engine will place each lane as a horizontal band and assign numbered steps from left-to-right position. Keep the happy path near the center lanes and route exceptions downward or upward.

## Level of detail
Include: ownership, decision branches, retries, manual vs automated steps, external handoffs, terminal outcomes.
Exclude: full API payloads, table schemas, UI wireframes, and implementation internals unless the prompt explicitly asks.

## Image-prompt template
```
Workflow diagram, modern flat vector, reviewable technical aesthetic.

Actors / lanes: {lanes}
Steps: {steps}
Decisions and branches: {decisions}
Queues / waits / SLAs: {queues}
Terminal outcomes: {outcomes}

Style: use the active preset palette. Encode manual vs automated by shape and label text, not color alone. Use dashed arrows for async handoffs/retries and solid arrows for direct handoffs.

Typography: short step labels, 14pt minimum, sans-serif. Monospace only for IDs or system names.

Layout: left-to-right happy path, exception paths offset vertically. Group boundaries act as swimlanes and never overlap. Decision labels must be yes/no or short branch labels.

Do NOT invent owners or outcomes. Do NOT exceed 15 steps; split large workflows into phases.
```

## SVG-prompt template
```
Output ONLY valid SVG 1.1 per the SVG contract. Use class .service for process steps, .queue for queued work, .external-system for external systems, .connection-sync for direct handoffs, .connection-async for async/retry paths.

Lanes: {lanes}
Steps: {steps}
Decisions: {decisions}
Branches: {branches}
Outcomes: {outcomes}

viewBox="0 0 1600 900". Draw swimlanes as non-overlapping .boundary regions. Place arrow labels above the arrow. Use one path with both markers for bidirectional handoffs.
```

## Golden examples

### Example 1
**User input:** "checkout workflow from cart to shipment, including payment, fraud review, warehouse pick, and customer notification"
**Refined image prompt (excerpt):**
> Workflow. Lanes: Customer, Commerce App, Risk, Warehouse, Notifications. Steps: Review cart → Submit order → Authorize payment → Fraud check. Decision: Risk flagged? Yes → Manual review → approve/reject. No → Create pick ticket → Pack order → Ship → Send notification. Async arrows for warehouse and notification handoffs.

### Example 2
**User input:** "support escalation workflow: tier 1 triage, engineering bug, product decision, customer update"
**Refined image prompt (excerpt):**
> Workflow with lanes Support, Engineering, Product, Customer. Tier 1 triage routes to known answer, bug escalation, or product decision. Engineering bug path loops through reproduce → fix candidate → deploy. Product path goes decision → roadmap or workaround. Customer update happens on every terminal branch.

## Common mistakes to avoid
- Do NOT turn a workflow into a sequence diagram; show ownership and stages, not lifelines.
- Do NOT color manual vs automated without also using labels or shapes.
- Do NOT let exception paths cross the happy path when vertical offset fixes it.
- Do NOT omit terminal outcomes; reviewers need to know where each branch ends.
