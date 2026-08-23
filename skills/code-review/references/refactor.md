# Refactor lens (`vd:code-review --refactor`)

Not "is this correct?" but "is this the code this codebase would have written?"

Local and report-only by default. Never posts to GitHub. `--fix` applies the minimal recommended fixes. `--save` writes the report to the injected Reports path as `refactor-review-{date}-{slug}.md`.

## Hard rules

1. **No reuse claim without a search.** Cite `path:line`. Empty search: say so and recommend the smallest clean alternative.
2. **Understand the wiring before judging a line.** Isolated-line review produces confident nonsense.
3. **Report-only unless `--fix`.**
4. **Proportionality.** A finding you would ignore yourself is noise.
5. **Match the project, not your taste.**

## First pass

1. Read the full diff.
2. Trace the feature: callers, callees, where state lives.
3. Search before judging any new helper, component, hook, type, or pattern:

```bash
rg -n -w '<new-helper-name>'
rg -n 'export (function|const) ' <sibling-dir>
rg -n '<domain-noun>' --glob '!*test*' -l
git log --oneline -10 -- <changed-path>
```

## Lenses

**Reuse.** Existing utilities, components, hooks, server actions, route patterns, error/result types, copy, styling primitives. Flag hand-rolled versions of something the repo already ships. A new "shared" helper with one caller is extracted private logic with a vague name.

**Consistency.** File placement matches neighbors. Names match siblings. Reuse the repo's result / error / loading patterns. Copy matches existing tone.

**Composition.** One job per function, one level of abstraction. Flag grab-bag modules and parameter sprawl. Prefer plain composition over callback/wrapper/memo chains. Unify two backing entities that are one product concept until an adapter needs the split.

**Slop.**

| Kind | What it looks like |
|---|---|
| Comment slop | Restates the code, defends awkward code, or carries stale PR context |
| Helper slop | Tiny wrappers that add no meaning |
| Type slop | Exported one-off types; annotations where inference reads better |
| Config slop | A constant or flag with exactly one possible setting |
| Compatibility cruft | Bolted-on behavior preserving accidental architecture (hand to `vd:simplify --aggressive`) |
| Diff churn | Unrelated renames and reformatting |
| Test slop | Tests asserting implementation; mocks of the thing under test |

**Minimality.** Deleting beats adding. Keep the fix proportional.

**Stack.** Apply the one that matches: React/Next (derive during render, no memo without a reason), Go (wrap errors, no one-impl interface at the producer), Python (no bare except, IO at the edge), dbt/SQL (`ref()` instead of re-deriving a CTE).

## Fowler smells (baseline)

Flag these when they are new in the diff, not as a repo-wide witch hunt: long method, long parameter list, feature envy, data clumps, speculative generality, shotgun surgery, comments that apologize for the code.

## Output

Verdict: `clean` / `mostly clean` / `needs cleanup`. Then findings, highest first, using this skill's severity prefixes. Each finding: file and symbol, what reads as slop, the existing pattern (`path:line`) when one exists, the minimal fix.
