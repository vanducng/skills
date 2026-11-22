---
name: simplify
description: "Reduce the complexity of existing code without changing behavior - deep nesting, long functions, dead code, unclear names, the wrong abstraction. Use after a feature works but reads heavier than it should, or to clean up code written under time pressure. Pass `--aggressive` to reshape a working feature into the form it should have had from day one (delete proven-dead compatibility paths). `--scan` lists aggressive candidates only. Every mode strips unnecessary comments and lint suppressions through a non-author reviewer so the code speaks for itself; `--comments` runs only that pass, `--comments --all <path>` sweeps existing code. Triggers: 'simplify this', 'clean up this code', 'reduce complexity', 'zero tech debt', 'remove the compat layer', 'rebuild this as if from scratch', 'strip the comments', 'remove unnecessary comments', 'the code should speak for itself', 'no comments', 'audit the eslint-disables'."
license: MIT
argument-hint: "[path or scope] [--aggressive | --scan | --comments [--all <path>]] (defaults to recently changed code)"
metadata:
  author: vanducng
  attribution: "Adapted from addyosmani/agent-skills code-simplification, the Claude code-simplifier plugin and cursor/plugins pstack no-comments"
  version: "0.4.0"
---

# simplify

> Reduce-time discipline: make existing code easier to read without changing what it does.

The goal is **not fewer lines** - it's code a new teammate understands faster. Every change must pass one test: would someone reading this for the first time grasp it quicker than the original? If not, it's churn, not simplification. Not for hot paths where the simpler form is measurably slower, or a module about to be rewritten wholesale.

Prefer simplify when the code is correct but cluttered. If the user invokes /simplify by name, run it even while the change is still being designed or still misbehaving. A bug-only task with no simplify request stays vd:fix. Judging someone's diff is `vd:code-review` (report-only).

| Mode | When | Behavior |
|---|---|---|
| **default** | Reads heavy, shape is right | Behavior frozen; readability only |
| `--aggressive` | Shape is historical (compat flags, dead aliases) | Follow [`references/aggressive.md`](references/aggressive.md) |
| `--scan` | Want the candidate list first | Same as aggressive, no edits |
| `--comments` | Only the comments and suppressions | The comment pass alone; `--all <path>` sweeps in batches |

## Hard rules

1. **Behavior is frozen.** Same output for every input, same errors, same side effects and ordering. If you're unsure a change preserves behavior, don't make it. The one exception is a comment-pass `RESHAPE` or suppression fix, committed alone as `fix:`.
2. **Tests are the proof.** Run them after every single change. A simplification that needs a test edited to pass is a behavior change in disguise - stop and reconsider.
3. **One change at a time.** Batching means you can't tell which edit broke something.
4. **Refactor commits stand alone.** Never mix a `refactor:` with a `feat:`/`fix:`. Two concerns = two commits (or two PRs).
5. **Scope to what changed.** Default to recently modified code. Drive-by refactors of unrelated code create diff noise and regression risk - broaden scope only when asked.

## Workflow

### 1. Understand before touching (Chesterton's Fence)

Don't remove a fence until you know why it's there. Before changing anything, answer:

- What is this code's responsibility? What calls it, what does it call?
- What are its edge cases and error paths? Which tests pin them?
- Why might it look this way - performance, a platform constraint, a historical reason? (`git blame` / `git log -p` the lines.)

Can't answer? You're not ready. Read more context first.

### 2. Find the opportunities (signals, not vibes)

**Structure**

| Pattern | Signal | Simplification |
|---|---|---|
| Deep nesting (3+ levels) | Control flow is hard to follow | Guard clauses; extract helpers |
| Long function (50+ lines) | Multiple responsibilities | Split into focused, named functions |
| Nested ternaries | Needs a mental stack to parse | if/else, switch, or a lookup map |
| Boolean flag params (`f(true, false)`) | Opaque at the call site | Options object or separate functions |
| Repeated conditional | Same `if` in many places | Extract a named predicate |

**Naming & redundancy**

| Pattern | Signal | Simplification |
|---|---|---|
| Generic names (`data`, `tmp`, `result`) | Says nothing about content | Rename to the content (`validationErrors`) |
| Comments, lint suppressions | See the comment pass below | Kill, reshape, encode or keep |
| Duplicated logic (5+ lines, 2+ places) | - | Extract a shared function (Rule of Three) |
| Dead code (unreachable, unused, commented-out) | - | Remove after confirming it's truly dead |
| Wrong abstraction (factory-for-a-factory, 1-impl strategy) | Indirection with no payoff | Inline to the direct form |

**Comment pass.** Every mode runs [`references/comments.md`](references/comments.md) on the scope (`--scan`: the review and report only, no edits): a non-author reviewer judges each comment and lint suppression against a five-clause keep list, then you kill, reshape the code, encode the constraint, or keep it (one line). End with one line per comment: what you did, `because <reason>`.

### 3. Apply incrementally

For each simplification: make the change → run tests → green, continue; red, revert and reconsider. Commit refactors separately from any behavior change.

**Rule of 500:** if a refactor would touch more than ~500 lines, write the codemod (sed/AST transform), don't hand-edit. Manual edits at that scale are error-prone and exhausting to review.

### 4. Verify the whole

Step back: is it genuinely easier to understand? Did you introduce a pattern foreign to the codebase? Is the diff clean and reviewable? If the "simpler" version is harder to read or review - **revert.** Not every attempt succeeds, and that's fine.

## Over-simplification traps (the failure mode)

- **Inlining a helper that named a concept** - the call site gets harder, not easier.
- **Merging unrelated logic** - two simple functions fused into one complex one is not simpler.
- **Deleting an abstraction that existed for testability/extensibility**, not for complexity.

## Integration points

- **`vd:cook`** - Step E surfaces complexity during a feature; bank the note and run `vd:simplify` as a *separate* follow-up commit, never tangled into the feature diff.
- **`vd:code-review`** flags complexity (report-only); this skill is how you act on it, with refactor commits isolated per `vd:git`'s `references/commit-standards.md`.
