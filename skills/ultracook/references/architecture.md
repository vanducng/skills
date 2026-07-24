# Architecture: two-layer SKILL.md ↔ bash-script pattern

## The constraint

Runtime tools (`AskUserQuestion`, `Skill`, `Monitor`, `ScheduleWakeup`, `Agent`, `Edit`, `Read`, `Write`) **only execute from a Claude Code session context**. They cannot be invoked from a bash script.

Yet bash is the right language for filesystem operations, parsing TOML/YAML/JSON, slug derivation, atomic writes, git worktree creation, etc. - fast, well-known, no runtime dependency.

So `vd:ultracook` is structured in two layers:

```
┌────────────────────────────────────────────────────────────────┐
│ SKILL.md (Claude Code session)                                 │
│   - Reads user prompt                                          │
│   - Invokes AskUserQuestion, Skill, Monitor, Agent             │
│   - Interprets bash-script outputs (env vars, JSON, exit code) │
│   - Decides which runtime tool to call next                    │
└──────────────────────┬─────────────────────────────────────────┘
                       │  passes env vars + reads stdout/exit
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ scripts/*.sh (subprocess)                                      │
│   - Pure filesystem + git + jq/yq work                         │
│   - Returns: stdout (JSON or env-var hints), exit code         │
│   - Logs evidence to <state-base>/{slug}/iterations/NNN-*.log  │
└────────────────────────────────────────────────────────────────┘
```

## Worked example: intake

`SKILL.md`:
```
1. AskUserQuestion("target kind?") → user picks "cluster"
2. AskUserQuestion("action shape?") → user picks "fix-and-ship"
3. AskUserQuestion("branch name?") → user picks "fix/cron-retry"
4. AskUserQuestion("autonomy?") → user picks "semi"
5. Bash: ULTRACOOK_TARGET_KIND=cluster ULTRACOOK_ACTION_SHAPE=fix-and-ship \
        ULTRACOOK_BRANCH=fix/cron-retry ULTRACOOK_AUTONOMY=semi \
        bash ~/skills/skills/ultracook/scripts/init-goal.sh "fix cron retry"
6. Read script stdout → extract goal-dir path → print to user
```

`init-goal.sh` is pure: it doesn't ask anything, it just transforms env vars + a positional arg into filesystem state.

## Worked example: executor loop (Phase 3+)

`SKILL.md`:
```
loop:
  state = Read(<state-base>/{slug}/state.json)
  if state.terminal != null: break

  next_action = bash ~/skills/skills/ultracook/scripts/resolve-next.sh --goal-dir ...
  # script returns JSON like {"action": "plan", "skill_invocation": "vd:plan --deep ..."}

  if should_gate(state.autonomy, next_action.action):
    AskUserQuestion("Run {action}? run/skip/quit")
    if user said skip/quit: handle

  # Now the SKILL.md does the actual invocation:
  if next_action.skill_invocation:
    Skill(skill: next_action.skill_to_invoke, args: next_action.args)
  elif next_action.shell:
    Bash(next_action.shell)
  elif next_action.monitor:
    Monitor(...)

  bash ~/skills/skills/ultracook/scripts/append-journal.sh --action {name} ...
  bash ~/skills/skills/ultracook/scripts/update-state.sh < state-patch
```

## What this means for contributors

1. **Bash scripts never directly invoke runtime tools.** They `echo` hints to stdout that SKILL.md interprets.
2. **SKILL.md is the only layer that calls `Skill`, `AskUserQuestion`, `Monitor`, `Agent`.**
3. **All filesystem mutations happen in scripts**, never in SKILL.md prose (so they're testable in isolation via `bash -n` + integration tests).
4. **Communication channels:**
   - Env vars in → scripts (set by SKILL.md before invocation)
   - JSON / env-var hints / exit codes out → SKILL.md parses
   - Logs to `iterations/NNN-*.log` for forensics

## Anti-patterns

| Bad | Good |
|---|---|
| `init-goal.sh` calls `AskUserQuestion` directly | SKILL.md calls `AskUserQuestion`, passes answers to script via env vars |
| `eval-verifier.sh` invokes the next-action Skill | `eval-verifier.sh` returns `{pass, evidence}` JSON; SKILL.md decides whether to call the next Skill |
| Status / kill logic embedded in SKILL.md markdown narrative | Status / kill live in `scripts/status.sh` and `scripts/kill.sh`; SKILL.md routes the sub-verb to the script |
| Long bash heredoc inside SKILL.md to generate a script at runtime | Scripts are checked-in files; SKILL.md just calls them |

## Why this matters

Without this separation, the skill becomes either:
- An untestable wall of markdown narrative ("the assistant should run X then Y then Z") that drifts from reality, OR
- A bash mega-script that pretends to be deterministic but actually needs runtime tools mid-flow and so silently fails when run standalone.

Phase 3 extends this doc with the executor-specific diagrams (action-dispatch flow, journal-write contract, eval-verifier sentinel pattern for `manual_confirm`).
