# Type: state-machine

## Purpose
Show the lifecycle of an entity: states, transitions, triggers, conditions. Audience: anyone reasoning about valid state changes.

## When to use
Trigger words:
- "state machine", "states", "transitions", "lifecycle"
- "status flow", "from X to Y", "when condition Z then …"
- mentions of order/job/subscription/user statuses

## Visual conventions
- States: rounded rectangles, primary-color border, surface fill, name in semibold
- Initial state: small filled black circle with arrow into the first state
- Final state: circle with an inner concentric circle ("bullseye")
- Transitions: directed arrow with label `trigger [condition] / action`
- Self-transitions: small circular arrow looping back to the same state
- Composite states: large rounded rectangle wrapping nested states

## Layout direction
**Top → bottom** for sequential lifecycles (e.g. signup → active → cancelled).
**Radial / hub-and-spoke** when one state has many transitions.

## Level of detail
Include: every distinct state, every meaningful transition, the trigger and any guard condition.
Exclude: implementation detail (DB columns, code paths) — they belong in a separate doc.

## Image-prompt template
```
State machine diagram, flat vector, calm technical aesthetic.

Initial state: {initial}
States: {states}
Final state(s): {final}
Transitions (from → to, label "trigger [condition] / action"): {transitions}

Style: the surface background color, primary color borders/text, accent color on the {focal state} if there is one, success color for happy-path transitions and error color for failure transitions ONLY when the prompt explicitly distinguishes ok/error paths.

Typography: sans-serif for state names (semibold), sans-serif for transition labels, monospace for action / event identifiers. 14pt minimum.

Layout: primary flow top-to-bottom for linear lifecycles, radial when one state branches into many. Initial state (small filled black circle) at top. Final state (bullseye) at bottom or off to the side. Transition labels above arrows. Self-loops as small circular arrows on the right side of the state.

Do NOT invent states or transitions. Do NOT cram >10 states.
```

## SVG-prompt template
```
Output ONLY valid SVG 1.1 per the SVG contract. Use class .service for state rectangles (rounded), .connection-sync for transition arrows.

Initial state: {initial}
States: {states}
Final state(s): {final}
Transitions: {transitions}

viewBox="0 0 1600 900". Initial state as <circle r="6" fill="var(--primary)"/>. Final state as concentric circles. Self-loops as small arc <path d="M ...">.
```

## Golden examples

### Example 1
**User input:** "subscription lifecycle: trial → active → past_due → cancelled, can also go active → cancelled directly"
**Refined image prompt (excerpt):**
> State machine. Initial → trial. States: trial, active, past_due, cancelled (final). Transitions:
> - trial → active: "trial_ended [paid]"
> - active → past_due: "payment_failed"
> - past_due → active: "payment_succeeded"
> - past_due → cancelled: "grace_period_ended"
> - active → cancelled: "user_cancelled"
> Layout top-to-bottom, with past_due offset to the right showing the loop back to active.

### Example 2
**User input:** "order: placed, paid, fulfilled, refunded — refund possible only after paid"
**Refined image prompt (excerpt):**
> State machine. Initial → placed. States: placed, paid, fulfilled, refunded (final). Transitions: placed→paid "payment_received", paid→fulfilled "shipped", paid→refunded "refund_request" (success-colored), fulfilled→refunded "return_received [within_30_days]" (success-colored). Layout vertical.

## Common mistakes to avoid
- Do NOT use success/error colors decoratively. Reserve for explicit ok/error paths.
- Do NOT label every transition with a verbose sentence — keep to "trigger [condition] / action".
- Do NOT skip the initial-state marker (small filled circle).
- Do NOT mix layout direction within one diagram.
