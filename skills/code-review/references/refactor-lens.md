# Refactor lens (`--refactor` mode)

> Not "is this correct?" but "is this the code this codebase would have written?"

Local and report-only: no `gh pr review`, no posted comments. Run it on your own branch before the public PR pass, or on any diff when you want the reuse/consistency read specifically. `--fix` applies the minimal recommended fixes as a separate `refactor:` commit; `--save` writes the report to the injected `Reports:` path as `refactor-review-{date}-{slug}.md`.

## Hard rules

1. **No reuse claim without a search.** "The codebase already has this" must cite `path:line`. If the search came up empty, say so and recommend the smallest clean alternative instead.
2. **Understand the wiring before judging a line.** Build the call stack or data flow for the changed area first. Isolated-line review produces confident nonsense.
3. **Report-only unless `--fix`.**
4. **Proportionality.** A finding you'd ignore yourself is noise - drop it.
5. **Match the project, not your taste.** Suggestions follow the target repo's local style and existing patterns.

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

## Lenses

### Reuse

- Look for existing utilities, components, hooks, server actions, route patterns, error/result types, copy, and styling primitives before accepting new code.
- Flag duplicated logic, copied helpers, and hand-rolled versions of something the codebase already ships.
- Prefer extending the existing flow over introducing a parallel one, even when it needs a small change.
- A new "shared" helper with exactly one caller is not shared - it's extracted private logic with a vague name.

### Consistency

- File placement matches the domain and its neighbors. A new top-level `lib/` dump is a smell.
- Names match what the code does and follow sibling naming.
- Reuse the codebase's standard result / error / loading patterns rather than inventing a bespoke success shape.
- User-facing copy matches existing tone.

### Composition and boundaries

- Each function does one thing at one level of abstraction.
- Flag grab-bag modules mixing flags, IO, transformation, UI state, logging, and scheduling.
- Parameter sprawl means the boundary is wrong, not that the function needs more knobs.
- When two backing entities are one product concept, pass one unified model through intermediate layers; split back to core entities only at roots and adapters.
- Domain logic stays near its domain until cross-domain reuse is proven.

### Slop

| Kind | What it looks like |
|---|---|
| Comment slop | Restates the code, defends awkward code, or carries stale PR context |
| Helper slop | Tiny wrappers that add no meaning; a file created to make one function look shorter |
| Type slop | Exported one-off types, bespoke result shapes, annotations where inference reads better |
| Config slop | A constant, flag, or env var for a value that has exactly one possible setting |
| Compatibility cruft | Bolted-on behavior preserving accidental architecture (hand to `vd:simplify --aggressive`) |
| Diff churn | Unrelated renames, reformatting, and wrappers that enlarge the PR without improving it |
| Test slop | Tests asserting the implementation instead of the behavior; mocks of the thing under test (see `vd:tdd` anti-patterns) |

### Stack lenses

Apply the one that matches the diff.

**React / Next.js** - derive during render instead of syncing with effects; move event-caused work into handlers; reset state with `key`. No `useMemo`/`useCallback` without a real render-identity or cost reason. Avoid data waterfalls; run independent fetches concurrently when the codebase already has that pattern.

**Go** - errors wrapped with context, not re-created; no interface with a single implementation defined at the producer; context threaded, not stored; goroutine lifetimes and cancellation obvious at the call site; table tests over per-case copies.

**Python / data** - no bare `except`; pure transformation separated from IO; dataframe/SQL logic pushed to the warehouse when the codebase does that; config through the project's existing settings object, not new module globals.

**dbt / SQL** - reuse existing models via `ref()` instead of re-deriving the same CTE; new columns follow the project's naming and grain; tests declared on the new grain; no logic duplicated between a mart and its source model.

### Minimality

- Deleting beats adding.
- One clear function beats several helper-y fragments unless extraction earns reuse or clarity.
- Keep the fix proportional to the problem.

## Red flags

- "Can we reuse something?" was never answered with an actual search.
- New top-level helpers named `utils`, `helpers`, `shared`, or after their implementation.
- A function name that hides a significant side effect.
- A directory containing only `index.ts` with no reason.
- Re-exporting something already exported elsewhere.
- New custom primitives where the design system or codebase already has one.
- Several new types supporting one local function.
- Callback / memo / effect code that would vanish if state ownership moved one level.

## Output format

Open with a verdict: `clean` / `mostly clean` / `needs cleanup`. Then findings, highest priority first, in the standard severity vocabulary:

```
**Important - reuse**: `src/lib/format-date.ts:12` reimplements `formatRelative`.

`src/utils/time.ts:44` already does this and handles the null case. Delete the
new helper and import that one.
```

Each finding carries: file path and symbol, what reads as slop or inconsistency, the existing pattern that should be reused (with `path:line`) when one exists, and the minimal fix.

## Hand-offs

- Readability-only findings → `vd:simplify` (behavior stays frozen there); compatibility cruft → `vd:simplify --aggressive`.
- "Does this already exist?" spanning services or repos → `vd:scout`.
- `--fix` output lands as its own `refactor:` commit via `vd:cook`, separate from the feature.
