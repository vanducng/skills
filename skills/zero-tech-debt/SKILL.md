---
name: zero-tech-debt
description: "Rework a change as if the intended architecture existed from day one - delete compatibility cruft, collapse mode flags, and reshape around the final product surface. Use after a feature works but still carries the scars of how it was built. Triggers: 'zero tech debt', 'rebuild this as if from scratch', 'remove the compat layer', 'what would this look like if we designed it right', 'this flag exists only for the old path'."
license: MIT
argument-hint: "[path, PR, or scope] (defaults to the current branch diff)"
metadata:
  author: vanducng
  version: "0.1.0"
---

# zero-tech-debt

> Optimize for the code that should exist, not for the smallest diff from the code that does.

A working feature usually encodes its own history: a mode flag from the migration, a wrapper kept "just in case", a route alias nobody hits, a prop threaded three levels for one caller that no longer exists. This skill removes the history and leaves the end state.

## What this skill is - and isn't

| Skill | When | Behavior |
|---|---|---|
| **`vd:zero-tech-debt`** (this) | Feature works but its *shape* is historical | **May change the surface** - delete dead paths, collapse flags, rename to product intent |
| `vd:simplify` | Code reads heavy but the shape is right | Behavior frozen - readability only |
| `vd:code-refactor-review` | Judging someone's diff for fit and slop | Reports; edits only when asked |
| `vd:cook` | Writing new code | Builds the end state first time |
| `vd:fix` | Code is broken | Changes behavior to correct a bug |

Rule of thumb: if deleting the old path would break a *real* caller, that's a migration, not this skill.

## When to use

- Right after `vd:cook` lands a feature that grew through iterations.
- A migration finished and both paths still exist.
- A component or endpoint has grown `mode` / `variant` / `isLegacy` flags that only one product surface uses.
- Review feedback said "this is fine but it isn't the shape we want".

**Not for:** code you don't understand yet (scout first), a surface with external consumers you can't enumerate, or a module about to be replaced anyway.

## Hard rules

1. **Write the end state first.** One or two sentences, before touching anything. Can't state it? You're designing, not refactoring - go to `vd:brainstorm`.
2. **Prove dead before deleting.** A search that returns zero callers is evidence. "Probably unused" is not. See the recipe below.
3. **The intended flow's behavior is frozen.** You may delete paths nobody uses; you may not quietly change what the surviving path does. That's a separate commit.
4. **No framework for one feature.** Collapsing three flags into one clear component is the goal. Inventing a plugin registry is the failure.
5. **Refactor commits stand alone.** Never mixed with a `feat:` or `fix:`. Deletion commits are their own reviewable unit.
6. **Scope stops at coherence.** Include what makes the final shape make sense. Everything else is a follow-up.

## Workflow

### 1. State the end state

Write it down, literally:

> "One `ReportView` that takes a report id. No prebuilt/remote distinction above the data loader. Permissions decided once in the route guard."

Everything below is judged against that sentence.

### 2. Prove dead before you delete

For every flag, prop, wrapper, alias, fallback, or export you plan to remove:

```bash
rg -n -w '<symbol>' --hidden -g '!node_modules' -g '!dist'   # current callers
git log -S'<symbol>' --oneline -20                            # when and why it appeared
rg -n '<symbol>' --glob '*test*' --glob '*spec*'              # test-only callers = dead
```

For shared libraries, dbt models, or anything crossing a repo boundary, widen the search:

```bash
gh search code '<symbol>' --owner <org> --limit 50   # cross-repo callers
rg -n "ref\('<model>'\)" models/                     # dbt lineage
rg -n '<dag_id>|<task_id>' dags/                     # Airflow references
```

**Delete freely:** internal-only symbols with zero non-test callers, flags with one branch ever taken, wrappers whose only job is passing through.

**Deprecate instead of deleting** when the surface leaves your blast radius:

| Surface | Why not a straight delete | Do this |
|---|---|---|
| Published package export | Unknown consumers | Deprecate, ship a major, delete next cycle |
| HTTP route / API field | External clients | Keep + log usage, delete when traffic is zero |
| DB column or table with rows | Data loss is irreversible | Backfill or archive, then drop in a later migration |
| Event / message schema | In-flight producers and consumers | Version the schema, drain, then remove |
| Feature flag read by ops | Runbooks reference it | Confirm with the owner before removing |

### 3. Reshape around the final surface

- One clear component, function, or flow instead of one generic thing with mode flags.
- Split only on a real boundary: different state ownership, different layout, different permissions, different domain command. "It got long" is not a boundary - that's `vd:simplify`.
- When two backing entities are one product concept, unify them into a single model at the boundary and split back only at the adapter or persistence layer.

### 4. Move shared rules to one place

Feature flags, permission checks, route gating, URL/query state, and command naming belong in one owner - not duplicated per page or buried inside a view component. If the same `if (canEdit)` appears in three components, the gate is at the wrong level.

### 5. Rename to product intent

`useRemoteOrPrebuiltReportV2` is implementation history. `useReport` is the product. Rename last, once the shape is settled, in its own commit so the diff stays readable.

### 6. Verify the intended flow, and the assumptions you deleted

Run the tests, then explicitly exercise what the deleted paths used to guard:

- Navigation and deep links that referenced the removed alias.
- Permission boundaries the removed gate covered.
- Persisted state: existing rows, saved URLs, cached payloads, in-flight jobs written under the old shape.
- Migration replay on a copy of real-shaped data when a column or schema changed.

Tests that had to be edited to pass are a signal: either behavior changed (revert and split it out) or the test was pinning the historical shape (fine - say so in the commit body).

## Traps

- **Deleting the fence you didn't read.** A weird-looking fallback may be a production incident's fix. `git log -S` before you assume.
- **Generalizing while reshaping.** Removing three flags and adding a config object is a lateral move.
- **Scope drift.** "While I'm here" is how a 200-line cleanup becomes an unreviewable 2000-line one.
- **Deleting the only test coverage** along with the dead path, leaving the surviving path untested.

## Integration points

- **`vd:cook`** - run this as a follow-up pass after the feature is green, never tangled into the feature diff.
- **`vd:simplify`** - complementary: this fixes the *shape*, that fixes the *reading*. Shape first.
- **`vd:code-refactor-review`** - use it to find the cruft; use this to remove it.
- **`vd:scout`** - when the caller search spans services or repos, dispatch it rather than grepping by hand.
- **`vd:git`** - deletions and renames land as separate `refactor:` commits.
- **`vd:ship`** - deprecation-path items become changelog entries, not silent removals.
