# Autonomy modes - manual / semi / auto

How often the conductor pauses. Set at start (`state.json.autonomy` or `--manual` / `--semi` / `--auto`) and editable mid-flight - re-read the file each stage.

## Mode definitions

| Mode | Gates on | Use when |
|---|---|---|
| `manual` | Every stage | First-time use; high-stakes goals; debugging the conductor |
| **`semi`** (default) | First `vd:plan`, `vd:ship`, and the final stage `done_when` | Normal workflow |
| `auto` | Nothing except hard gates | Trusted small fixes; user is away |

Hard gates in [`conductor.md`](conductor.md) always ask, including in `auto`.

## After a gate clears

Do not re-gate that stage. Escalate only on an exception: unrelated test failure, merge conflict, structural type/lint error that is not auto-fixable, tool/service down after retries, or a never-seen error.

## Mid-flight edits

Patch `autonomy` in `state.json`:

- `manual` → `semi` when tired of clicking
- `auto` → `manual` to inspect the next stage
- Drop a stage by setting its status to `skipped` (say why in `evidence`)

## Terminal-blocked ping

On `terminal=blocked` in `semi` or `auto`, notify the user (runtime push if available, else a loud status line): `{slug}: {terminal_reason}`. `manual` skips the ping - the user is watching.

## Anti-patterns

- **Home-grown gate scripts.** The agent applies the table above. There is no closed action vocabulary to look up.
- **`auto` as the first-run default.** Ship `semi`. `auto` needs trust from successful semi runs.
- **Removing the ship gate from `semi`.** Ship is the highest blast-radius stage. Keep it unless the pipeline has no ship stage.
