# ADR workflow - record an architecture decision

An ADR (Architecture Decision Record) captures the **why** behind a consequential, hard-to-reverse choice - the context, the alternatives weighed, and what it commits you to. It's the artifact that stops "why is it built this way?" from becoming archaeology six months later. The decision itself comes from `vd:brainstorm`/`vd:research`; this is where it lands permanently.

## Three-part gate

Do not write the file until all three are load-bearing:

1. **Context** - the forces that make a decision necessary (not a restatement of the ask)
2. **Decision** - one sentence, active voice, "We will…"
3. **Consequences** - what becomes easier, harder, and now a contract (including reversal cost)

Missing any one → you are still deciding. Stay in `vd:brainstorm` / `vd:interview --grill`. An ADR with only Context and Decision is a blog post.

## When to write one

- A low-reversibility choice: framework, datastore, auth model, public API shape, a boundary between services.
- A decision someone will question later, where the *alternatives we rejected and why* is the valuable part.
- **Not** for routine, easily-reversed choices - those are commit messages, not ADRs.

## Location & numbering

```
docs/decisions/
  0001-use-postgres-over-dynamodb.md
  0002-session-cookies-not-jwt.md
  0003-adopt-contract-first-api-design.md
```

- Zero-padded sequential number. To get the next: scan `docs/decisions/` for the max `NNNN` and add one (start at `0001`).
- Slug = the decision in a few words, kebab-case.
- This directory is exempt from `vd:docs` freshness/size/citation checks - ADRs are history, not current-state docs.

## Template

```markdown
# {NNNN}. {Decision in one line}

- Status: {Proposed | Accepted | Superseded by [NNNN](NNNN-slug.md) | Deprecated}
- Date: {YYYY-MM-DD}

## Context
What forces are at play - technical, product, team, constraints. The situation that
makes a decision necessary. State the problem, not the solution.

## Decision
The choice, stated plainly and in the active voice: "We will …".

## Alternatives considered
- **{Option A}** - pros / cons / why rejected.
- **{Option B}** - pros / cons / why rejected.
(If this followed a vd:brainstorm brief, link it - don't re-litigate, summarize.)

## Consequences
What becomes easier, what becomes harder, what we're now committed to (Hyrum's Law:
the choice's observable effects are now a contract). Include the migration cost if we
ever reverse it.
```

## Lifecycle

- **Supersede, never delete.** When a later decision overrides this one: write a *new* ADR, then edit the old one's `Status:` to `Superseded by [NNNN](…)`. The old record stays - the reasoning that was valid then is still valid history.
- **Status only moves forward**: Proposed → Accepted → (Superseded | Deprecated). Don't rewrite an Accepted ADR's Decision/Context; if the decision changed, that's a new ADR.

## Handoff

After writing, surface the file with an openable location. If this ADR records a `vd:brainstorm` recommendation, note that the brief's decision is now permanent in `docs/decisions/NNNN-…`.
