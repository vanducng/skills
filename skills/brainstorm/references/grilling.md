# Grilling - the converge interview loop

Grilling is how brainstorm converges: a relentless, structured interview that sharpens a decision until nothing load-bearing is left ambiguous. It is the default questioning mechanism for this skill and is also invoked directly by `vd:plan` and `vd:ultracook` (semi mode) when they hit an underspecified decision - via `vd:brainstorm --grill`.

## The model

Treat the decision as a **design tree**. The root is the decision being made; branches are sub-decisions; leaves are questions that only the user can answer. The **frontier** is the set of questions that are currently askable - not blocked by an unanswered parent.

Division of labor, non-negotiable:

- **Facts are your job, never the user's.** If a question can be answered by reading code, docs, or the web, dispatch a lookup (subagent, grep, WebSearch) and answer it yourself. Never ask the user something the environment can tell you.
- **Decisions are the user's.** Anything that trades off cost, scope, risk, taste, or priorities goes to the user - with your recommendation attached.

## The loop

1. Build the tree from what you know so far. Mark each leaf: *fact* (you resolve) or *decision* (user resolves).
2. Resolve all fact leaves yourself.
3. Emit **one round**: every currently-askable decision question at once - numbered, each with a recommended answer and a one-line reason. Never drip questions one at a time; never ask questions whose answer depends on an earlier unanswered question.
4. Deliver the round (see delivery modes below) and wait.
5. Fold answers back in, recompute the tree - answers usually open new branches - and emit the next round.
6. **Done when the frontier is empty**: every load-bearing decision has an explicit answer, and you can state the sharpened idea in one paragraph the user agrees with.

Round format (used in both delivery modes):

```markdown
## Round {N}

1. **{Question}?**
   ➡️ Recommended: {answer} - {one-line reason}
2. **{Question}?**
   ➡️ Recommended: {answer} - {one-line reason}
...
```

## Delivery: Plannotator first

**Default - Plannotator is installed** (`command -v plannotator` succeeds, or the host agent has the Plannotator plan-review hook):

1. Write the round as a standalone markdown brief to the injected `Reports:` path (or the active plan dir): `grill-{YYYYMMDD-HHMM}-round-{N}.md`. Open with one paragraph of current understanding ("Here's the idea as I understand it so far"), then the round's numbered questions, then a **Coverage** section listing the angles examined so far (see below).
2. Open it for annotation: `plannotator-annotate <file>` (or the `plannotator annotate` CLI). The user answers by annotating - inline comments as answers, deletions to cut scope, quick labels ("clarify this", "out of scope"), a global comment for direction.
3. Read the structured feedback that comes back. Deletions remove branches; comments answer or reshape questions; "out of scope" prunes the tree. Fold everything in, then write round N+1 as a **new file** - the version trail is part of the record.

**Fallback - no Plannotator**: post the round directly in chat, same format, and fold in the user's reply.

## Coverage: grill from multiple angles

A grilling session that only asks about the happy path has not converged. Across rounds, deliberately rotate angles - and show the rotation in the brief's Coverage section so the user sees what has and hasn't been examined:

- **Scope** - what is explicitly out? What's the smallest version that's still worth doing?
- **Users/consumers** - who hits this? What breaks for them if it's wrong?
- **Failure** - what does this look like when it fails at 3am? Blast radius?
- **Data** - what state does it create/mutate? Migration? Backfill?
- **Reversibility** - cost to undo in 12 months?
- **Operations** - who runs it, monitors it, gets paged?
- **Sequencing** - what must land first? What can be deferred?
- **The unstated goal** - is the ask a proxy for a different need?

Two or three angles per round; frontier decides which. Do not pad rounds with angle questions whose answers are already knowable facts.

## Anti-patterns

| Anti-pattern | Fix |
|---|---|
| Asking one question per message | Emit the whole frontier per round |
| Asking the user for facts | Look them up; only decisions go to the user |
| Questions without a recommendation | Always take a position - a recommendation forces you to have understood the question |
| Stopping after round 1 because answers "seem clear" | Recompute the tree; new branches almost always open |
| Endless grilling | Done when the frontier is empty, not when questions run out of novelty |
