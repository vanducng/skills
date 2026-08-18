---
name: wayfinder
description: "Plan work too big for one agent session as a shared map of decision tickets on an issue tracker, resolved one at a time until the way is clear. Use when a loose idea spans many sessions ('this is huge', 'we'll be at this for a while'), when the user says 'chart this', 'wayfinder', 'work the map', or when interview/brainstorm/plan would produce a 12-phase mega-plan. Plans decisions, not builds - hand the cleared way to vd:plan/vd:cook per chunk. Not for one-session work: want is vd:interview, how is vd:brainstorm, steps are vd:plan."
license: MIT
argument-hint: "[loose idea to chart | map URL/id [ticket]]"
metadata:
  author: vanducng
  attribution: "Adapted from mattpocock/skills wayfinder (MIT)"
  version: "0.2.0"
---

# Wayfinder

A loose idea has arrived - too big for one agent session, and wrapped in fog: the way from here to the **destination** isn't visible yet. Wayfinding is about finding that way, not charging at the destination. This skill charts the way as a **shared map** on an issue tracker, then works its **decision tickets** - questions whose resolution is a decision, not slices of a build to execute - one at a time until the route is clear.

The map is the shared memory *between* sessions: each session loads the low-res map, resolves one ticket, records the answer, and stops. Context windows stay small; the tracker carries the accumulated decisions.

## What this skill is - and isn't

| Skill | Question it answers | Horizon |
|---|---|---|
| `vd:interview` | "What do you actually want?" | One session; want, not how |
| `vd:interview --grill` | "Are these decisions the right ones?" | One session; walk an existing plan or idea |
| `vd:brainstorm` | "How should I approach this one decision?" | One session |
| `vd:research` | "Which known option should I pick?" | One session; cited comparison |
| `vd:plan` | "Given the decided approach, what are the build steps?" | One plan, phases sized to one session each |
| **`vd:wayfinder`** | **"The idea is bigger than any session can hold - what must be decided, in what order, before anyone can plan?"** | **Many sessions; the tracker is the memory** |
| `vd:ultracook` | "Drive a decided goal through plan → cook → ship." | One goal, one pipeline |

**Plan, don't do.** Each ticket resolves a decision; the map is done when nothing is left to decide before someone goes and builds. The pull to just do the work is usually the signal you've reached the edge of the map - hand off to `vd:plan` (then `vd:cook` or `vd:ultracook`) for that chunk instead.

Grill lives only on `vd:interview --grill`. Do not invent a second grilling skill. Prototype rules live in [`references/prototype.md`](references/prototype.md).

## Hard rules

1. **Name the destination first.** One or two lines: the spec, decision, or change this effort is finding its way to. It fixes the scope; every ticket is judged against it.
2. **One non-research ticket per session.** The sizing discipline that keeps every session inside a fresh context window. Research tickets may fan out in parallel subagents.
3. **Claim before work.** Assign the ticket to yourself *first* so concurrent sessions skip it. An open, unassigned ticket is unclaimed.
4. **Refer by name.** In everything the human reads, tickets go by title (wrapping the link), never bare ids. A wall of `#42, #43, #44` is illegible.
5. **The map is an index, not a store.** A decision lives in exactly one place - its ticket. The map gists and links; it never restates.
6. **Don't chart what you can't see.** Ticket only questions you can state precisely *now*; the rest stays in the fog (below).

## The map

One issue labelled `wayfinder:map`; tickets are its child issues. Tracker mechanics (GitHub Issues via `gh`, Jira via `vd:jira`, or the local-markdown fallback) live in [`references/trackers.md`](references/trackers.md).

Map body - loaded once per session, open tickets found by query, not listed:

```markdown
## Destination
<what reaching the end looks like - one or two lines; every session orients to it first>

## Notes
<domain; vd: skills every session should consult; standing preferences for this effort>

## Decisions so far
- [<closed ticket title>](link) - <one-line gist of the answer>

## Not yet specified
<!-- in-scope fog you can't ticket yet; graduates as the frontier advances -->

## Out of scope
<!-- work ruled beyond the destination; never graduates -->
```

Each ticket's body is one question, sized to a single fresh session:

```markdown
## Question
<the decision or investigation this ticket resolves>
```

Blocking uses the tracker's native dependency relationship so the frontier renders visually in the tracker's own UI. A ticket is **unblocked** when everything blocking it is closed; the **frontier** is the open, unblocked, unclaimed children - the edge of the known.

## Ticket types

Every ticket is **HITL** (worked *with* a human - the agent never answers the human's side itself) or **AFK** (agent-driven). Label `wayfinder:research|prototype|grilling|task`.

| Type | Mode | Resolves via | Use when |
|---|---|---|---|
| `research` | AFK | Subagent running `vd:research`; findings linked from the ticket | A fact outside the repo blocks a decision |
| `prototype` | HITL | Throwaway spike per [`references/prototype.md`](references/prototype.md); artifact linked, never merged | "How should it look/behave?" is the question |
| `grilling` | HITL | `vd:interview --grill` (one question at a time, recommended answer, explicit yes); sharpen terms against `docs/glossary.md` where one exists | The default - the question is a conversation |
| `task` | either | Do the unblocking work (sign up, provision, move data); record what was done + resulting facts | Manual work must happen before a decision *can* be made |

`task` is the one type that *does* rather than decides - it earns its place by unblocking a decision, not by delivering the destination.

If a grilling ticket isolates a single "how" with a confirmed want, that ticket may hand to `vd:brainstorm` for the 3+ options, then record the pick on the ticket. Brainstorm does not replace grilling and does not own `--grill`.

## Fog of war

Beyond the live tickets lies the fog: decisions you can tell are coming but can't yet pin down, because they hang on open questions. Write that dim view into **Not yet specified** - as loosely or fully as the view allows. Resolving a ticket clears fog ahead of it; graduate whatever became specifiable into fresh tickets and delete it from the fog section.

**Fog or ticket?** Whether you can state the question precisely now - *not* whether you can answer it now. Sharp-but-blocked → ticket with a blocking edge. Not yet phrasable → fog. Don't pre-slice fog into ticket-sized pieces; one patch may graduate into several tickets, or none.

**Out of scope** is different from fog: work consciously ruled beyond the destination. It never graduates. When an existing ticket turns out to sit past the destination, close it and leave one line in Out of scope (gist + why, linking the closed ticket) - it stays out of Decisions so far, which records the route actually walked.

## Invocation

### Chart the map (loose idea in)

1. **Name the destination** - `vd:interview` if want is unconfirmed; `vd:interview --grill` if they already brought a plan or idea. Settled first, because it fixes the scope.
2. **Map the frontier** - grill again, *breadth-first*: fan across the whole space, not deep on one thread. **No fog surfaced?** The journey fits one session - stop. Want unclear → `vd:interview`. How unclear → `vd:brainstorm`. How decided → `vd:plan`. Say so.
3. **Create the map** (`wayfinder:map`): Destination + Notes filled, Decisions-so-far empty, fog sketched into Not yet specified.
4. **Create the specifiable tickets** as children, then wire blocking edges in a second pass (issues need ids before they can reference each other).
5. **Fire the research subagents** - claim each `research` ticket first (assign it, per hard rule 3 - unclaimed tickets stay on the frontier and a concurrent session would duplicate the work), then resolve them in parallel via `vd:research`.
6. Stop. Charting is one session's work; it hand-resolves nothing.

### Work the map (map URL/id in, ticket optional)

1. Load the map - the low-res view, not every ticket body.
2. Choose: the named ticket, else the first frontier ticket. **Claim it** before any work.
3. Resolve it - zoom into related/closed ticket bodies on demand; consult whatever skills the map's Notes name.
4. Record: post the answer as a resolution comment, close the ticket, append one gist line to Decisions so far.
5. Maintain: create-then-wire newly surfaced tickets; graduate cleared fog; rule mis-scoped tickets out of scope; update or delete tickets the answer invalidated.

Expect other sessions to be editing the tracker concurrently - the user may run unblocked tickets in parallel.

### Hand off (the map is done)

When the frontier is empty and no fog remains, the way is clear. Per buildable chunk: `vd:plan` (the map's decisions are the plan's inputs - link the relevant tickets from `decisions.md`), then `vd:cook` or `vd:ultracook`. The map issue stays open until the destination itself is reached, then closes linking the shipped artifacts.

If `vd:ultracook` is already conducting a goal and the deciding will not fit one session, **stop the pipeline** and run this skill. Do not open a 12-phase plan to paper over fog.

## Workflow position

**Typically follows:** a loose idea too big for one interview or brainstorm; `vd:scout` when the fog is about the codebase itself
**Composes:** `vd:interview --grill` (grilling tickets + charting), `vd:research` (research tickets), [`references/prototype.md`](references/prototype.md) (prototype tickets), `vd:brainstorm` (one isolated how, after want is confirmed), `vd:jira` / `gh` (tracker ops), `vd:docs` glossary (term sharpening)
**Typically precedes:** `vd:plan` → `vd:cook` / `vd:ultracook` per cleared chunk
**Compares to:** `vd:interview` + `vd:brainstorm` + `vd:plan` (work that fits one session); `vd:ultracook` fan-out (parallel *execution* of decided work - wayfinder parallelizes *deciding*)
