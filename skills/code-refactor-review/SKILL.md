---
name: code-refactor-review
description: "Review a diff for reuse, composition, codebase consistency, and slop - the 'does this fit the codebase' lens rather than 'is it correct'. Local and report-only by default; never posts to GitHub. Triggers: 'refactor review', 'is this slop', 'did we reinvent something that exists', 'does this fit the codebase', 'review for reuse', 'check composition'."
license: MIT
argument-hint: "[#PR | URL | ref-range | --pending] [--fix] [--save]"
metadata:
  author: vanducng
  version: "0.1.0"
---

# code-refactor-review

> Not "is this correct?" but "is this the code this codebase would have written?"

## What this skill is - and isn't

| Skill | Question | Output |
|---|---|---|
| **`vd:code-refactor-review`** (this) | "Does this fit the codebase, or is it slop?" | Local verdict + findings; edits only with `--fix` |
| `vd:code-review` | "Is this ready to land?" | Inline GitHub PR comments + summary verdict |
| `vd:simplify` | "Can this read easier without changing behavior?" | Refactor commits |
| `vd:zero-tech-debt` | "What shape should this have had from day one?" | Reshape + deletions |
| `vd:security` | "What can an attacker do with this?" | Threat-modeled findings |

This one stays local: no `gh pr review`, no posted comments. It is the pass you run on your own branch before `vd:code-review` goes public, or on someone else's diff when you want the reuse/consistency read specifically.

## Modes

| Argument | Diff source |
|---|---|
| *(none)* | `git diff` (unstaged), falling back to `git diff HEAD` when staged changes exist |
| `--pending` | `git diff HEAD` (staged + unstaged) |
| `main...HEAD` or any ref range | `git diff <range>` |
| `#123` or PR URL | `gh pr diff <n>` |

Flags: `--fix` applies the minimal recommended fixes and summarizes what changed. `--save` writes the report to the injected `Reports:` path as `refactor-review-{date}-{slug}.md`.

## Hard rules

1. **No reuse claim without a search.** "The codebase already has this" must cite `path:line`. If the search came up empty, say so and recommend the smallest clean alternative instead.
2. **Understand the wiring before judging a line.** Build the call stack or data flow for the changed area first. Isolated-line review produces confident nonsense.
3. **Report-only unless `--fix`.** Findings, not edits.
4. **Proportionality.** Every finding must be worth the author's time to act on. A finding you'd ignore yourself is noise - drop it.
5. **Match the project, not your taste.** Suggestions follow the target repo's local style and existing patterns, even when you'd write it differently.

## First pass

1. Read the full diff, not the summary.
2. Trace the feature: what calls this, what it calls, where state lives.
3. Search before judging any new helper, component, hook, type, or pattern:

```bash
rg -n -w '<new-helper-name>'                     # was it already there under another name
rg -n 'export (function|const) ' <sibling-dir>   # what siblings already provide
rg -n '<domain-noun>' --glob '!*test*' -l        # where this domain already lives
git log --oneline -10 -- <changed-path>          # what conventions this area follows
```

## Review lenses

### 1. Reuse

- Look for existing utilities, components, hooks, server actions, route patterns, error/result types, copy, and styling primitives before accepting new code.
- Flag duplicated logic, copied helpers, and hand-rolled versions of something the codebase already ships.
- Prefer extending the existing flow over introducing a parallel one, even when it needs a small change.
- A new "shared" helper with exactly one caller is not shared - it's extracted private logic with a vague name.

### 2. Consistency

- File placement matches the domain and its neighbors. A new top-level `lib/` dump is a smell.
- Names match what the code does and follow sibling naming. Implementation details in names only when they are the real product distinction.
- Reuse the codebase's standard result / error / loading patterns rather than inventing a bespoke success shape.
- User-facing copy matches existing tone.

### 3. Composition and boundaries

- Each function does one thing at one level of abstraction.
- Flag grab-bag modules mixing flags, IO, transformation, UI state, logging, and scheduling.
- Parameter sprawl means the boundary is wrong, not that the function needs more knobs.
- Prefer plain composition over chains of callbacks, wrappers, memo helpers, and prop plumbing.
- When two backing entities are one product concept, pass one unified model through intermediate layers; split back to core entities only at roots and adapters where persistence or payload format demands it.
- Domain logic stays near its domain until cross-domain reuse is proven.

### 4. Slop

| Kind | What it looks like |
|---|---|
| Comment slop | Restates the code, defends awkward code, or carries stale PR context |
| Helper slop | Tiny wrappers that add no meaning; a file created to make one function look shorter |
| Type slop | Exported one-off types, bespoke result shapes, annotations where inference reads better |
| Config slop | A constant, flag, or env var for a value that has exactly one possible setting |
| Compatibility cruft | Bolted-on behavior preserving accidental architecture (hand to `vd:zero-tech-debt`) |
| Diff churn | Unrelated renames, reformatting, and wrappers that enlarge the PR without improving it |
| Test slop | Tests asserting the implementation instead of the behavior; mocks of the thing under test |

### 5. Stack lenses

Apply the one that matches the diff.

**React / Next.js** - derive during render instead of syncing with effects; move event-caused work into handlers; reset state with `key`. No `useMemo`/`useCallback` without a real render-identity or cost reason. No redundant state. Avoid data waterfalls; run independent fetches concurrently when the codebase already has that pattern.

**Go** - errors wrapped with context, not re-created; no interface with a single implementation defined at the producer; context threaded, not stored; goroutine lifetimes and cancellation obvious at the call site; table tests over per-case copies.

**Python / data** - no bare `except`; pure transformation separated from IO; dataframe/SQL logic pushed to the warehouse when the codebase does that; config through the project's existing settings object, not new module globals.

**dbt / SQL** - reuse existing models via `ref()` instead of re-deriving the same CTE; new columns follow the project's naming and grain; tests declared on the new grain; no logic duplicated between a mart and its source model.

### 6. Minimality

- Deleting beats adding.
- One clear function beats several helper-y fragments unless extraction earns reuse or clarity.
- Keep the fix proportional to the problem.
- No new architecture, docs, or comments unless they remove real ambiguity.

## Output format

Open with a verdict:

- `clean` - no meaningful concerns.
- `mostly clean` - minor cleanup only.
- `needs cleanup` - real reuse, composition, or consistency problems.

Then findings, highest priority first, using the `vd:code-review` severity vocabulary so the two skills read the same:

```
**Important - reuse**: `src/lib/format-date.ts:12` reimplements `formatRelative`.

`src/utils/time.ts:44` already does this and handles the null case. Delete the
new helper and import that one.
```

Each finding carries: file path and symbol, what reads as slop or inconsistency, the existing pattern that should be reused (with `path:line`) when one exists, and the minimal fix.

With `--fix`, apply the fixes and end with a short list of what changed. Without it, do not edit files.

## Red flags

- "Can we reuse something?" was never answered with an actual search.
- New top-level helpers named `utils`, `helpers`, `shared`, or after their implementation.
- A function name that hides a significant side effect.
- A directory containing only `index.ts` with no reason.
- Re-exporting something already exported elsewhere.
- New custom primitives where the design system or codebase already has one.
- A long comment explaining why an awkward prop or flag exists.
- Several new types supporting one local function.
- Callback / memo / effect code that would vanish if state ownership moved one level.

## Rules

- Be direct and concise. No preamble, no praise padding.
- Ground every claim in the codebase. Do not invent architecture.
- If a pattern genuinely does not exist yet, say so and propose the smallest clean version.
- When in doubt, favor code that reads obvious left to right.

## Integration points

- **`vd:code-review`** - run this first on your own branch; that one is the public, PR-posting pass.
- **`vd:zero-tech-debt`** - hand compatibility-cruft findings over; that skill removes them.
- **`vd:simplify`** - hand readability-only findings over; behavior stays frozen there.
- **`vd:scout`** - when "does this already exist?" spans services or repos, dispatch it instead of grepping blind.
- **`vd:cook`** - `--fix` output lands as its own `refactor:` commit, separate from the feature.
