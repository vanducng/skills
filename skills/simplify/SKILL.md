---
name: simplify
description: "Reduce the complexity of existing code - default freezes behavior (nesting, long functions, dead code, unclear names); --aggressive reshapes as if designed right from day one (delete compat cruft, collapse mode flags); --scan surveys the codebase for refactor candidates and reports. Triggers: 'simplify this', 'clean up this code', 'reduce complexity', 'this is hard to read', 'untangle this', 'zero tech debt', 'remove the compat layer', 'rebuild this as if from scratch', 'where should we refactor'."
license: MIT
argument-hint: "[path or scope] [--aggressive | --scan] (defaults to recently changed code)"
metadata:
  author: vanducng
  attribution: "Adapted from addyosmani/agent-skills code-simplification and the Claude code-simplifier plugin"
  version: "0.2.0"
---

# simplify

> Reduce-time discipline: make existing code easier to read without changing what it does.

The goal is **not fewer lines** - it's code a new teammate understands faster. Every change must pass one test: would someone reading this for the first time grasp it quicker than the original? If not, it's churn, not simplification.

## What this skill is - and isn't

| Skill | When | Output |
|---|---|---|
| **`vd:simplify`** (this) | Existing code works but reads heavy or carries historical shape | Refactor commits, tests still green |
| `vd:cook` | Writing new code | Simplicity is built in at write-time (Pragmatism rules), not a later pass |
| `vd:code-review` | Judging someone's diff (`--refactor` for the fit/slop lens) | Reports findings; never edits |
| `vd:fix` | Code is broken | Changes behavior to fix a bug |

Use this when the code is *correct but cluttered*. If it's buggy, that's `vd:fix`. If you're still writing it, that's `vd:cook`.

## Modes

| Mode | Question | Surface contract |
|---|---|---|
| **default** | "Can this read easier?" | Behavior **and** surface frozen - readability only |
| `--aggressive` | "What shape should this have had from day one?" | May change the surface: delete dead paths, collapse mode flags, rename to product intent. Full playbook: [`references/aggressive.md`](references/aggressive.md) |
| `--scan` | "Where in this codebase is refactoring worth it?" | No edits - explores and reports candidates; user picks one, then run default or `--aggressive` on it |

Shape first, reading second: when both apply, run `--aggressive` before the default pass - polishing code you're about to delete is waste.

### `--scan` - find the candidates

Explore organically - follow the code's actual seams, don't walk a rigid checklist. Look for **deepening opportunities**: shallow modules (big interface, thin logic), one concept implemented twice under different names, boundaries that leak implementation detail, god files that every change touches, historical shape (compat layers, `v2` suffixes, mode flags). For each candidate write: what it is (`path`), why it hurts (evidence - churn from `git log`, duplication cites), the before/after shape in 2-3 lines, and a recommendation strength (do-now / worthwhile / marginal). Cap at ~6 candidates, strongest first. Write the report to the injected `Reports:` path as `simplify-scan-{date}-{slug}.md`, surface the top 3 inline, and stop - the user picks; don't start refactoring unprompted. To sharpen a picked candidate's end state, grill it: `vd:brainstorm --grill`.

## When to use

- A feature passes tests but the implementation feels heavier than the problem.
- Code written under deadline accreted nesting, dead branches, or generic names.
- A review flagged readability and you're acting on it.

**Not for:** code that's already clean (don't simplify for its own sake), code you don't yet understand (comprehend first), hot paths where the simpler form is measurably slower, or a module you're about to rewrite anyway.

## Hard rules (default mode)

1. **Behavior is frozen.** Same output for every input, same errors, same side effects and ordering. If you're unsure a change preserves behavior, don't make it. (`--aggressive` relaxes only the *surface* part - the surviving flow's behavior stays frozen; its rules live in the reference.)
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
| "What" comments (`// increment` over `i++`) | Restates the code | Delete - the code is the comment |
| "Why" comments (`// retry: API flakes under load`) | Carries intent code can't | **Keep** |
| Duplicated logic (5+ lines, 2+ places) | - | Extract a shared function (Rule of Three) |
| Dead code (unreachable, unused, commented-out) | - | Remove after confirming it's truly dead |
| Wrong abstraction (factory-for-a-factory, 1-impl strategy) | Indirection with no payoff | Inline to the direct form |

### 3. Apply incrementally

For each simplification: make the change → run tests → green, continue; red, revert and reconsider. Commit refactors separately from any behavior change.

**Rule of 500:** if a refactor would touch more than ~500 lines, write the codemod (sed/AST transform), don't hand-edit. Manual edits at that scale are error-prone and exhausting to review.

### 4. Verify the whole

Step back: is it genuinely easier to understand? Did you introduce a pattern foreign to the codebase? Is the diff clean and reviewable? If the "simpler" version is harder to read or review - **revert.** Not every attempt succeeds, and that's fine.

## Over-simplification traps (the failure mode)

- **Inlining a helper that named a concept** - the call site gets harder, not easier.
- **Merging unrelated logic** - two simple functions fused into one complex one is not simpler.
- **Deleting an abstraction that existed for testability/extensibility**, not for complexity.
- **Optimizing for line count.** Fewer lines ≠ clearer.

## Rationalizations to catch in yourself

| Thought | Reality |
|---|---|
| "I'll just clean up this nearby code too" | Scope creep - that's a separate PR |
| "Fewer lines is better" | Comprehension is the metric, not length |
| "This abstraction is pointless" | Check why it exists before removing it (Fence) |
| "Tests fail but my version is clearer" | Then it changed behavior - it's not a simplification |

## Integration points

- **`vd:cook`** - Step E surfaces complexity during a feature; bank the note and run `vd:simplify` as a *separate* follow-up commit, never tangled into the feature diff.
- **`vd:code-review`** - review flags complexity and cruft (report-only; `--refactor` for the fit lens); this skill is how you act on it.
- **`vd:brainstorm --grill`** - sharpen a `--scan` candidate's end state before reshaping.
- **`vd:git`** - refactor commits stay isolated per the `vd:git` skill's `references/commit-standards.md`.

## Future (out of scope for MVP)

- Language-specific codemod recipes beyond the Rule-of-500 pointer.
- An automatic complexity metric gate (cyclomatic/cognitive) - judgment-first for now.
