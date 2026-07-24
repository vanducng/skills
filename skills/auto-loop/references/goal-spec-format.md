# goal.md spec format

`goal.md` is the user-authored spec read by the loop. All fields except `# Goal` and `verify:` are optional and have documented defaults.

## Schema

```markdown
# Goal
<free text - the objective. Single paragraph or short bullet list. Be specific
about what "done" looks like; the audit subagent reads this verbatim.>

# Verify
verify: `<shell command>`

# Scope
allow: <glob>, <glob>
deny: <glob>, <glob>

# Caps
max_iterations: 40
max_tokens: 2_000_000
max_wallclock: 4h
restart_at_context_pct: 70
max_restarts: 5
```

## Field reference

| Field | Required | Default | Notes |
|---|---|---|---|
| `# Goal` (block) | yes | - | Free-text objective. |
| `verify:` | yes | - | Shell command in backticks; exit 0 = pass. Run 2× per gate check. |
| `allow:` | no | repo root | Comma-separated globs. Files outside this list trigger a soft warning in next-iter prompt (not blocking). |
| `deny:` | no | empty | Comma-separated globs. Edits inside these globs trigger an immediate blocker. |
| `max_iterations` | no | 40 | Hard cap. |
| `max_tokens` | no | 2_000_000 | Advisory unless `ccusage` present. |
| `max_wallclock` | no | `4h` | Floor cap - always enforced. Format: `30m`, `2h`, `4h30m`. |
| `restart_at_context_pct` | no | 70 | Phase-restart trigger. |
| `max_restarts` | no | 5 | Anti-thrash safeguard. |

## Parser behaviour

- Blank lines and `# heading` lines are skipped.
- Fields that take a single value (`verify:`, `max_iterations:`, etc.) accept `key: value` syntax; trailing comments after `#` are stripped.
- Underscores in numeric values (`2_000_000`) are tolerated.
- Missing `# Goal` or `verify:` → parser exits non-zero with a one-line error to stderr.
- Unknown keys → silent ignore (forward-compat).

## Example

```markdown
# Goal
All bats tests in tests/ pass. Lint clean (ruff). No new files outside tests/ or src/.

# Verify
verify: `bats tests/ && ruff check .`

# Scope
allow: src/**/*.py, tests/**/*.bats
deny: .env, secrets/**

# Caps
max_iterations: 30
max_wallclock: 2h
```

## Equivalent CLI

The above can also be expressed inline:

```
vd:auto-loop "all bats tests pass + ruff clean; no new files outside tests/ or src/" \
  --verify "bats tests/ && ruff check ." \
  --max-iterations 30 \
  --max-wallclock 2h
```

A mixed invocation (`--goal-file goal.md --max-iterations 50`) is allowed; CLI flags override `goal.md` values.
