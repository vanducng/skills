# Autonomy modes - `manual` / `semi` / `auto`

Three modes control how often `vd:ultracook`'s executor pauses for user confirmation. Mode is set at intake (`goal.yaml.autonomy`) and can be edited in-place mid-flight - the executor re-reads goal.yaml each iteration.

## Mode definitions

| Mode | Gates on… | Use when |
|---|---|---|
| `manual` | EVERY action | Debugging the skill; first-time use; high-stakes goals |
| **`semi`** (default) | First `plan` (initial design approval), `ship` (high blast radius), final `verify_*` actions | Normal workflow - most goals run here |
| `auto` | Nothing (only stops on terminal state) | Trusted small fixes; CI-driven runs; user is away |

## Implementation: `scripts/should-gate.sh`

```
should-gate.sh --mode <mode> --action <name> --phase-state <first|repeat>
  → exit 0  = GATE  (caller AskUserQuestion's the user)
  → exit 1  = PROCEED (no gate)
  → exit 2  = invalid input
```

The `--phase-state` arg distinguishes "first time we hit this action this run" vs "we're retrying" - only `semi` mode uses this to gate on the FIRST `plan` but not on plan re-runs.

## Gate selection per mode (default policies)

`semi` gates when ANY of:
- action = `plan` AND phase_state = first
- action = `ship`
- action = `verify_smoke`
- action's `gate_default` in action-vocab.yaml contains `"semi"`

`manual` gates always.

`auto` gates never.

User-level override: even in `auto`, a goal.yaml field `gates: [list]` (v0.2) could force gates on named actions. Not in v0.1 - edit autonomy mode instead.

## Terminal-blocked push notification

On `state.terminal = blocked` in `semi` or `auto` mode, SKILL.md emits `PushNotification` with:

```
title:  "vd:ultracook blocked"
body:   "{slug}: {blocker_reason}"
deep_link: "<path-to-journal-entry>"
```

This pages the user if they walked away. `manual` mode skips the push (user is present and watching).

## Mid-flight edits

Switching modes by editing `goal.yaml.autonomy` is the supported override path. Examples:

- Stuck in `manual` and tired of clicking? Edit to `semi` - the next iteration's `should-gate.sh` call respects the new mode.
- Running `auto` and want to inspect mid-cook? Edit to `manual` - the next action will gate.
- Want to skip the `verify_smoke` gate? Either drop the action from `goal.yaml.actions`, or move to `auto`.

## Anti-patterns

- **Hardcoding gates inside scripts.** All gate logic flows through `should-gate.sh`. Other scripts call it; no script makes gate decisions independently.
- **`auto` mode default for first-time users.** The skill ships `semi` as the intake default for a reason - `auto` requires trust calibration that only comes from successful semi runs.
- **Removing the `ship` gate from `semi`.** Ship is the highest blast-radius action. Always keep its semi gate unless you also remove ship from the sequence entirely.
