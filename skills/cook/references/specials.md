# Cook specials

Load this file when the phase matches. The core loop in SKILL.md does not change.

## Migrations

Phase A (migration) must include a tested rollback path before phase B (consumers) starts. Untested rollback is hope, not a migration.

## API breaking changes

Verify all callers compile/run after each step. If you cannot add the new path without breaking the old one, the plan is wrong - kick back to `vd:plan`.

## Performance work

Step C must compare against baseline numbers from the plan. "Faster" without numbers is unfalsifiable.

## Refactors with `--tdd`

Step B's failing tests document **current** behavior. After implementation, all those tests must still pass. A new green that was not green before is suspicious - investigate, do not celebrate.

## UI work

Step C must include manual browser verification. Type errors and visual bugs are orthogonal.

## Library upgrades

Every phase ends with a smoke of one feature touched by the upgraded library. Do not lump smokes into a final QA phase.

## Bug fixes (`--quick`)

Write the test that reproduces the bug first, watch it fail, then fix. Without the failing test you have no proof the bug existed.

## Parallel fan-out

Phases cooked concurrently by separate agents in one checkout. Four rules:

1. **Scaffold the shared surface in the foundation phase** - route registry, barrel imports, type stubs - so parallel phases fill disjoint files and never both touch the registry.
2. **Strict glob ownership per phase** + "commit only your paths, never `git add -A`". The one phase that edits or deletes a shared file owns that edit alone.
3. **Resume from uncommitted state on agent death.** Read the uncommitted tree, amend the phase prompt with `RESUME NOTE: read git status/diff, continue from there`, and re-run.
4. **Run the full integrated gate at HEAD after the fan-out.** Per-phase DONE claims miss cross-phase compile/test gaps. Regenerate gitignored generated dirs before trusting a red build.
