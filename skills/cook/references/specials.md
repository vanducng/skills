# Cook specials - situation playbooks

Load the section that matches the work; skip the rest.

## Migrations

Phase A (migration) must include a **tested rollback path** before phase B (consumers) starts. Untested rollback = hope, not migration. Never interleave migration steps with feature steps - if the plan does, kick back to `vd:plan`.

## API breaking changes

Verify all callers compile/run after each step. The sequence is add-new → migrate-callers → remove-old; if you can't add new without breaking old, the plan is wrong → kick back. Never collapse the three steps into one phase.

## Performance work

Step C must compare against baseline numbers from the plan. "Faster" without numbers is unfalsifiable. If the plan has no baseline, capture one before the first change and record it in the phase notes.

## Refactors with `--tdd`

Step B's failing tests document **current** behavior. After implementation, all tests must still pass. A new green that wasn't green before is suspicious - investigate, don't celebrate.

## UI work

Step C must include manual browser verification. Type errors and visual bugs are orthogonal. For flows, drive the page (agent-browser / web-e2e) rather than trusting a compile.

## Library upgrades

Every phase ends with a smoke of one feature touched by the upgraded library. Don't lump smokes into a final QA phase - by then you can't bisect which phase broke it.

## Bug fixes (`--quick`)

Write the test that reproduces the bug *first* (per `vd:tdd` - red before green is the reproduction), watch it fail, then fix. Without the failing test you have no proof the bug existed.

## Parallel fan-out

Phases cooked concurrently by separate agents in one checkout (e.g. via `Workflow`/`Task`). Four rules earn the speedup without corruption:

1. **Scaffold the shared surface in the foundation phase** - route registry, barrel imports, type stubs - so parallel phases fill *disjoint* files and never both touch the registry.
2. **Strict glob ownership per phase** + "commit only your paths, never `git add -A`". The one phase that edits or deletes a shared file (the registry, the god-component) owns that edit *alone*.
3. **Resume from uncommitted state on agent death.** Long fan-outs lose agents to session limits and transient API socket drops mid-phase. Recover by reading the uncommitted tree, amending the phase prompt with a `RESUME NOTE: read git status/diff, continue from there`, and re-running (`Workflow resumeFromRunId` returns completed phases from cache).
4. **Run the full integrated gate at HEAD after the fan-out.** Per-phase "DONE" claims don't catch cross-phase compile/test gaps, and a generated/gitignored dir (e.g. `proto/gen`) can throw phantom "undefined X" errors that look like a broken merge - regenerate before trusting a red build.
