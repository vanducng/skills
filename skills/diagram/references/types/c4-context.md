# Type: c4-context

## Purpose
Show a software system in its environment: external users and external systems it interacts with. **No internal detail.** Audience: non-engineers, stakeholders, new joiners.

## When to use
Trigger words:
- "C4 context", "context diagram", "system in its environment"
- "users and external systems", "system landscape"
- "high-level overview" of how a system fits into the world

## Visual conventions
- The subject system: large rounded rectangle, **accent-highlighted border**, label `[Software System]` in muted italic under the name
- External users: stick figure, label below
- External systems: rounded rectangle with **dashed border**, label `[Software System]` in muted italic
- Relationships: solid arrows with verb-phrase labels (e.g. "uses", "sends notifications via")

## Layout direction
**Subject system at center.** External users and systems arrange around it. Direction less important than radial clarity.

## Level of detail
Include: subject system, every external user role, every external system, the relationship verb.
**Exclude: ANY internal containers, services, databases, or code-level detail.** That's c4-container's job.

## Image-prompt template
```
C4 context diagram, flat vector, calm professional aesthetic.

Subject system (centered, accent highlight): {subject}
External users (with role): {users}
External systems (dashed border): {externals}
Relationships (verb labels): {relationships}

Style: the surface background color, primary-color borders, accent color on the subject system ONLY, muted color for external system borders. Subject system gets a 2.5px accent-color border and slightly larger size to draw the eye. Externals get 1.5px dashed primary-color borders.

Typography: sans-serif. System / user names in semibold. The label "[Person]" or "[Software System]" in muted italic at smaller size below each.

Layout: subject system at center. Users and externals arranged around it (think hub and spoke). Solid arrows with verb labels. ≥40px breathing room. Maximum 8 surrounding entities.

Do NOT show internal containers, services, or databases inside the subject system. The subject is a single black box at this zoom level.
```

## SVG-prompt template
```
Output ONLY valid SVG 1.1 per the SVG contract. Use .service for the subject system (with class additions for the accent highlight), .external-system for externals, .user-actor for users, .connection-sync for relationships.

Subject: {subject}
Users: {users}
Externals: {externals}
Relationships: {relationships}

viewBox="0 0 1600 900". Subject centered around (800, 450), 360px wide, 200px tall, 2.5px accent-color stroke. Externals/users distributed radially. Each entity has the type tag "[Software System]" or "[Person]" as a smaller <text class="muted">.
```

## Golden examples

### Example 1
**User input:** "C4 context for an internal HR portal: used by employees and managers, integrates with Active Directory and Workday"
**Refined image prompt (excerpt):**
> C4 context. Subject (center, accent-highlighted): "HR Portal [Software System]". Users: Employee (left), Manager (top). Externals (dashed): Active Directory, Workday. Relationships: Employee "views/submits via" → HR Portal; Manager "approves via" → HR Portal; HR Portal "authenticates via" → Active Directory; HR Portal "syncs employee records with" → Workday.

### Example 2
**User input:** "Context for a checkout service used by customers, integrating with Stripe and SendGrid"
**Refined image prompt (excerpt):**
> C4 context. Subject (center, accent-highlighted): "Checkout Service". User: Customer (left). Externals (dashed): Stripe, SendGrid. Customer "pays through" → Checkout; Checkout "charges card via" → Stripe; Checkout "sends receipt via" → SendGrid.

## Common mistakes to avoid
- Do NOT show containers (web, api, db) inside the subject — that's c4-container.
- Do NOT skip the `[Person]` / `[Software System]` type tags — they're the C4 convention.
- Do NOT highlight more than one system with the accent color. The subject is singular.
- Do NOT use cardinality numbers — C4 uses verb labels, not relational notation.
