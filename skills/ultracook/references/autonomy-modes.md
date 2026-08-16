# Autonomy modes - `manual` / `semi` / `auto`

Three modes control how often the flow pauses for user confirmation. Mode is set when the goal is created (`state.json.autonomy`) and can be edited in place mid-flight - the executor re-reads state each iteration.

## Mode definitions

| Mode | Gates on… | Use when |
|---|---|---|
| `manual` | EVERY stage | Debugging the skill; first-time use; high-stakes goals |
| **`semi`** (default) | First `plan` approval (initial design), `ship` (high blast radius), the final stage's done-when check | Normal workflow - most goals run here |
| `auto` | Nothing (only stops on terminal state) | Trusted small fixes; CI-driven runs; user is away |

**Hard gates override all modes** - the always-ask list in `conductor.md` (delete/deploy/migrations/secrets/broad codemods/expensive fan-outs) fires even in `auto`.

## Gate semantics

- `semi` gates the **first** time a stage needs approval, not on retries of the same stage - re-gating every cook iteration is approval fatigue, the failure mode this mode exists to prevent.
- Once a gate clears, escalate back to the user only on *exceptions* (unrelated test failure, merge conflict, non-auto-fixable structural error, service down after retries, never-seen error).
- Gate questions are one clear decision each, with the evidence attached ("Plan written - N phases, audit found 1 HIGH. Approve, revise, or abort?"). Where Plannotator is installed, plan approval rides its plan-review hook instead of a terminal question.

## On `blocked`

When `state.terminal = blocked` in `semi` or `auto`, surface loudly: print the blocker reason and the journal/state path, and use the host's notification primitive if one exists (the user may have walked away). `manual` mode skips the notification - the user is present.

## Mid-flight edits

Editing `state.json.autonomy` is the supported override path:

- Stuck in `manual` and tired of clicking? Edit to `semi` - the next stage respects it.
- Running `auto` and want to inspect mid-cook? Edit to `manual` - the next stage gates.

## Anti-patterns

- **`auto` as the default for first-time users.** `semi` is the default for a reason - `auto` requires trust calibration that only comes from successful semi runs.
- **Removing the `ship` gate from `semi`.** Ship is the highest blast-radius stage. Keep its gate unless ship isn't in the flow at all.
- **Vague gate conditions.** "Proceed if confident" is not a gate. Every gate resolves to a checkable question.
