# Aggressive reshape (`vd:simplify --aggressive`)

Optimize for the code that should exist, not for the smallest diff from the code that does. May change the **surface** (delete dead paths, collapse flags, rename to product intent). The intended flow's behavior stays frozen.

Use after a feature works but still carries the scars of how it was built. If deleting the old path would break a real caller, that is a migration, not this mode.

`--scan` only lists candidates (end-state sentence + dead-path evidence). No edits.

## Hard rules

1. **Write the end state first.** One or two sentences. Cannot state it? That is design - go to `vd:brainstorm`.
2. **Prove dead before deleting.** A search that returns zero callers is evidence. "Probably unused" is not.
3. **The intended flow's behavior is frozen.** Deleting unused paths is allowed. Quietly changing the surviving path is not.
4. **No framework for one feature.** Collapsing three flags into one clear component is the goal.
5. **Refactor commits stand alone.** Deletion commits are their own reviewable unit.
6. **Scope stops at coherence.**

## Workflow

### 1. State the end state

> "One `ReportView` that takes a report id. No prebuilt/remote distinction above the data loader. Permissions decided once in the route guard."

### 2. Prove dead

```bash
rg -n -w '<symbol>' --hidden -g '!node_modules' -g '!dist'
git log -S'<symbol>' --oneline -20
rg -n '<symbol>' --glob '*test*' --glob '*spec*'
```

Widen for shared libraries / dbt / cross-repo:

```bash
gh search code '<symbol>' --owner <org> --limit 50
rg -n "ref\('<model>'\)" models/
rg -n '<dag_id>|<task_id>' dags/
```

**Delete freely:** internal-only symbols with zero non-test callers, flags with one branch ever taken, pass-through wrappers.

**Deprecate instead** when the surface leaves your blast radius: published exports, HTTP fields, DB columns with rows, in-flight event schemas, ops-read feature flags.

### 3. Reshape around the final surface

One clear component or flow instead of one generic thing with mode flags. Split only on a real boundary (state ownership, layout, permissions, domain command). "It got long" is default `vd:simplify`, not this mode.

### 4. Move shared rules to one place

Flags, permission checks, route gating, URL state, command naming: one owner.

### 5. Rename to product intent

`useRemoteOrPrebuiltReportV2` is history. `useReport` is the product. Rename last, own commit.

### 6. Verify the intended flow and the deleted assumptions

Tests, then the paths the deleted code used to guard: deep links, permission boundaries, persisted rows/URLs, migration replay on real-shaped data. Tests that had to be edited: either behavior changed (revert and split) or the test pinned the historical shape (say so in the commit body).

## Traps

- Deleting the fence you did not read (`git log -S` first)
- Generalizing while reshaping (three flags → a config object is a lateral move)
- Scope drift
- Deleting the only test coverage with the dead path
