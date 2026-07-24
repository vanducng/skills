# vd:auto-loop - usage

Drive a Claude Code session toward a verifiable goal until done or a hard cap fires.

## Quick start

```
vd:auto-loop "all bats tests pass + ruff clean" --verify "bats tests/ && ruff check ."
```

Goal text is positional. Verifier is a shell command - exit 0 means pass. The loop runs both 2× per gate check and additionally consults a fresh-context audit subagent before declaring `achieved`.

## Common invocations

```
# Default loop with explicit caps
vd:auto-loop "<goal>" --verify "<cmd>" --max-iterations 40 --max-wallclock 4h

# Read goal from goal.md (multi-line, scope, caps inline)
vd:auto-loop --goal-file goal.md

# Inspect a running loop
vd:auto-loop --status

# Stop a running loop
vd:auto-loop --cancel

# Delegate to Codex /goal
vd:auto-loop "<goal>" --verify "<cmd>" --codex
```

## Modes

| Mode | Trigger | What it does |
|---|---|---|
| Default | `<goal> --verify <cmd>` | Intra-session Stop-hook loop; two-vote gate; hard caps. |
| Status | `--status` | Read-only snapshot of the active loop (state, iter, caps, recent gate decisions). |
| Cancel | `--cancel` | Marks state `cancelled`, removes Stop hook, leaves working tree intact. |
| Codex | `--codex` | Delegates to `codex /goal` (requires codex ≥ 0.128.0 + ChatGPT auth). |

## Caps & defaults

| Flag | Default | Always enforced? |
|---|---|---|
| `--max-iterations` | 40 | Yes |
| `--max-tokens` | 2_000_000 | Only when token probe is `exact` or `approximate`; advisory on `fallback` |
| `--max-wallclock` | 4h | **Yes - floor cap** |
| `--restart-pct` | 70 | Yes (context-%-triggered phase restart) |

## Goal spec format

A multi-line goal can live in `goal.md`. See `references/goal-spec-format.md` for the full grammar. Minimum:

```markdown
# Goal
<free text>

# Verify
verify: `<shell command>`
```

## Files written

The loop writes only inside `.auto-loop/` and `.claude/settings.local.json`:

```
.auto-loop/
├── goal-state.json          # Single source of truth (atomic writes)
├── heartbeat.json           # PID + session_id; auto-purges on dead PID
├── hooks-backup.json        # Restored on --cancel
├── gate-history.jsonl       # One line per gate decision
├── restart-history.jsonl    # One line per phase-restart
├── verifier-{iter}.log      # stdout/stderr per iter (rotates, keeps 20)
├── audit-{iter}.json        # Audit subagent vote + reason
└── compaction-{iter}.md     # Compacted summary on phase-restart
```

`.auto-loop/` is gitignored at the repo root.

## Failure modes & exit cues

| Status | Meaning | Where to look |
|---|---|---|
| `pursuing` | Loop in flight | `--status` |
| `achieved` | Verifier + audit both voted achieved | Done. |
| `unmet` | Model claimed done; gate disagreed | `gate-history.jsonl` |
| `blocked` | Drift watchdog escalated; audit voted blocked | `audit-{iter}.json` |
| `budget-limited` | Hard cap fired (iter/tokens/wallclock) | Last `goal-state.json` |
| `cancelled` | User invoked `--cancel` | Working tree intact. Logs preserved. |

## See also

- `references/goal-spec-format.md` - full goal.md grammar
- `references/architecture.md` - state machine + script contracts
- `references/smoke-test.md` - reproducible end-to-end recipe
- `references/troubleshooting.md` - common failures and fixes
- `references/codex-delegation.md` - when `--codex` is the right call
