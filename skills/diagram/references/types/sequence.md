# Type: sequence

## Purpose
Show interactions between actors over time. Audience: anyone reasoning about a request flow, protocol, or async choreography.

## When to use
Trigger words:
- "user does X then Y", "request flow", "protocol", "interactions"
- API call chains, OAuth flows, login flows
- "sequence", "timeline", "step by step"

## Visual conventions
- Lifelines: vertical lines descending from each actor's title at the top
- Actors at top: stick figure for user, service rounded rectangle for systems, dashed external-system for 3rd parties
- Sync messages: solid horizontal arrow with filled triangular head
- Async messages: dashed horizontal arrow with open triangular head
- Activation bars: thin rectangles on the lifeline showing when each actor is processing
- Return arrows: dashed horizontal back to caller, with the response payload as label
- Notes: surface-color sticky-note shape attached to a lifeline

## Layout direction
**Time flows top → bottom.** Actors arranged left → right at the top.

## Level of detail
Include: every meaningful message, sync vs async, return values, error branches as labeled alt fragments.
Exclude: framework-internal callbacks, repeated polling - collapse with `loop` notation.

## Image-prompt template
```
Sequence diagram, flat vector, vertical layout (time flows top to bottom). Calm technical aesthetic.

Actors (left to right at top): {actors}
Messages (in order, top to bottom): {messages}

Style: the surface background color, primary color for lifelines and actor borders, accent color for the message that represents the diagram's subject, error color ONLY if the prompt explicitly mentions an error/retry path. Solid arrows for sync, dashed for async, dashed return arrows.

Typography: sans-serif for actor names, sans-serif for message labels, monospace for payload field names. 14pt minimum.

Layout: actors evenly spaced across the top. Vertical lifelines drop straight down from each actor. Activation bars on lifelines show processing windows. Labels ABOVE arrows. Return arrows dashed, labeled with the response.

Do NOT cross arrows when reordering actors fixes it. Do NOT exceed 6 actors. Do NOT add messages not described.
```

## SVG-prompt template
```
Output ONLY valid SVG 1.1 per the SVG contract. Layer order: boundaries → services → connections → labels. Use class names .service, .user-actor, .external-system, .connection-sync, .connection-async, plus a custom .lifeline (1px primary-color dashed vertical) and .activation (4px wide rounded rect on lifeline).

Actors (in left-to-right order at top): {actors}
Messages (top-to-bottom by time): {messages}

viewBox="0 0 1600 900". Actor headers along y=80, lifelines drop to y=820. Messages spaced ~80px apart vertically. Labels above arrows in <text>. Return messages with stroke-dasharray="6 4".
```

## Golden examples

### Example 1
**User input:** "user logs in via OAuth: User → App → Auth Provider → callback"
**Refined image prompt (excerpt):**
> Sequence diagram, vertical, three lifelines: User (stick figure, left), App (service, middle), Auth Provider (external-system dashed, right). Messages top-to-bottom:
> 1. User → App: solid sync arrow, label "GET /login"
> 2. App → Auth Provider: solid sync, label "redirect to /authorize"
> 3. Auth Provider → User: dashed return, label "consent screen"
> 4. User → Auth Provider: solid sync, label "approve"
> 5. Auth Provider → App: solid sync, label "POST /callback?code=..."
> 6. App → Auth Provider: solid sync, label "exchange code for token"
> 7. Auth Provider → App: dashed return, label "access_token"
> 8. App → User: dashed return, label "set session, redirect /"

### Example 2
**User input:** "checkout: client posts cart, backend reserves inventory, charges Stripe, on success creates order, on failure releases inventory"
**Refined image prompt (excerpt):**
> Sequence diagram, four lifelines: Client, Backend, Inventory service, Stripe (external dashed). alt fragment around the Stripe charge: success branch (success-colored, labeled "ok") creates order; failure branch (error-colored, labeled "error") releases inventory...

## Common mistakes to avoid
- Do NOT mix horizontal-flow conventions - sequence diagrams are vertical for time.
- Do NOT skip return arrows; show them as dashed.
- Do NOT use the error color decoratively. It's reserved for explicit error branches.
- Do NOT cram >6 actors. Group or split.
