# `--wayfinder` - multi-session decision map

Adapted from [mattpocock/skills wayfinder](https://github.com/mattpocock/skills/tree/main/skills/engineering/wayfinder) (MIT).

A loose idea has arrived - too big for one agent session, and wrapped in fog: the way from here to the **destination** isn't visible yet. This mode charts the way as a **shared map** on an issue tracker, then works its **decision tickets** - questions whose resolution is a decision, not slices of a build to execute - one at a time until the route is clear.

The map is the shared memory *between* sessions: each session loads the low-res map, resolves one ticket, records the answer, and stops. Context windows stay small; the tracker carries the accumulated decisions.

This is a mode of `vd:interview`, not a separate skill. Default interview still names the destination. `--grill` still walks one ticket. Do not look for `vd:wayfinder`.

## Hard rules

1. **Name the destination first.** Run the default interview loop (or `--grill` if they already brought a plan). One or two lines after the yes: the spec, decision, or change this effort is finding its way to. It fixes the scope; every ticket is judged against it.
2. **One non-research ticket per session.** The sizing discipline that keeps every session inside a fresh context window. Research tickets may fan out in parallel subagents.
3. **Claim before work.** Assign the ticket to yourself *first* so concurrent sessions skip it. An open, unassigned ticket is unclaimed.
4. **Refer by name.** In everything the human reads, tickets go by title (wrapping the link), never bare ids. A wall of `#42, #43, #44` is illegible.
5. **The map is an index, not a store.** A decision lives in exactly one place - its ticket. The map gists and links; it never restates.
6. **Don't chart what you can't see.** Ticket only questions you can state precisely *now*; the rest stays in the fog (below).

**Plan, don't do.** Each ticket resolves a decision; the map is done when nothing is left to decide before someone goes and builds. The pull to just do the work is usually the signal you've reached the edge of the map - hand off to `vd:plan` (then `vd:cook` or `vd:ultracook`) for that chunk instead.

## The map

One issue labelled `wayfinder:map` (tracker type label, not a skill ID); tickets are its child issues. Tracker mechanics live in [`trackers.md`](trackers.md).

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

A ticket is **unblocked** when everything blocking it is closed; the **frontier** is the open, unblocked, unclaimed children.

## Ticket types

Label `wayfinder:research|prototype|grilling|task`.

| Type | Mode | Resolves via | Use when |
|---|---|---|---|
| `research` | AFK | Subagent running `vd:research`; findings linked from the ticket | A fact outside the repo blocks a decision |
| `prototype` | HITL | Throwaway spike per [`prototype.md`](prototype.md); artifact linked, never merged | "How should it look/behave?" is the question |
| `grilling` | HITL | `vd:interview --grill` (same skill, grill mode) | The default - the question is a conversation |
| `task` | either | Do the unblocking work; record what was done + resulting facts | Manual work must happen before a decision *can* be made |

If a grilling ticket isolates a single "how" with a confirmed want, that ticket may hand to `vd:brainstorm` for the 3+ options, then record the pick on the ticket.

## Fog of war

Write dim upcoming decisions into **Not yet specified**. Sharp-but-blocked → ticket with a blocking edge. Not yet phrasable → fog. **Out of scope** never graduates.

## Invocation

### Chart the map (loose idea in)

1. **Name the destination** - default interview if want is unconfirmed; `--grill` if they already brought a plan or idea.
2. **Map the frontier** - grill again, *breadth-first*. **No fog surfaced?** Stop. Stay on default / `--grill`, or hand to `vd:brainstorm` / `vd:plan`. This is not a map.
3. **Create the map** (`wayfinder:map`): Destination + Notes filled, Decisions-so-far empty, fog sketched into Not yet specified.
4. **Create the specifiable tickets** as children, then wire blocking edges in a second pass.
5. **Fire the research subagents** - claim each `research` ticket first, then resolve them in parallel via `vd:research`.
6. Stop. Charting is one session's work; it hand-resolves nothing.

### Work the map (map URL/id in, ticket optional)

1. Load the map - the low-res view, not every ticket body.
2. Choose: the named ticket, else the first frontier ticket. **Claim it** before any work.
3. Resolve it. Grilling tickets use `--grill`.
4. Record: post the answer, close the ticket, append one gist line to Decisions so far.
5. Maintain: create-then-wire newly surfaced tickets; graduate cleared fog.

### Hand off (the map is done)

When the frontier is empty and no fog remains, the way is clear. Per buildable chunk: `vd:plan` (link the relevant tickets from `decisions.md`), then `vd:cook` or `vd:ultracook`.

If `vd:ultracook` is already conducting a goal and the deciding will not fit one session, **stop the pipeline** and switch this skill to `--wayfinder`.

## Verification

- [ ] Destination named via default interview or `--grill` with an explicit yes
- [ ] Map created only after fog surfaced
- [ ] Research tickets claimed before subagents fire
- [ ] One non-research ticket per session
- [ ] Grilling tickets invoke `--grill`, not a second skill
- [ ] Cleared chunks hand to `vd:plan`, not a mega-plan written here
