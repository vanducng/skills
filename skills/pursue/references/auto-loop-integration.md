# Auto-loop integration

How `vd:pursue` delegates iterative actions (primarily `cook` + `test`) to `/vd:auto-loop` for the Stop-hook-hosted loop, then resumes when auto-loop terminates.

## When delegation fires

An action is delegated to auto-loop when its `action-vocab.yaml` entry has `delegated_to: auto-loop`. Currently:
- `cook` — when a per-action verifier (`test_suite_passes`) is bound.
- `test` — same.

Other iterative actions (e.g. `verify_smoke` retries) could be added in v0.2 once dogfood shows the need.

## Lifecycle

```
SKILL.md executor (pursue)
        │
        ▼
   run-action.sh                          (returns dispatch_kind="skill", but...)
        │
        ▼ if action.delegated_to == auto-loop:
        │
   delegate-to-auto-loop.sh ──► build-compound-verifier.sh
        │                              │
        │                              ▼
        │                       writes verify-pursue-{action}.sh
        │                              │
        ▼                              │
   marker written:                     │
   {goal-dir}/.pursue/                 │
     delegated-to-auto-loop.json       │
        │                              │
        ▼                              │
   stdout: invocation hint             │
   { dispatch_kind: "skill",           │
     skill: "vd:auto-loop",            │
     args: "<goal> --verify <path> ..."│
     marker: "...",                    │
     verify_script: "..." }            │
        │                              │
        ▼                              ▼
   SKILL.md invokes Skill(skill: "vd:auto-loop", args: ...)
        │
        ▼ (auto-loop runs intra-session via Stop hook; Skill call returns
        │  synchronously when auto-loop terminates)
        ▼
   read-auto-loop-outcome.sh
        │  (reads .auto-loop/goal-state.json)
        ▼
   { status: ..., reason: ..., iterations: ..., last_evidence: ... }
        │
        ▼
   pursue updates state.json per outcome mapping (below)
   pursue deletes marker file
   pursue resumes executor loop (next action)
```

## Outcome mapping (6 statuses from auto-loop's state schema)

| auto-loop `status` | pursue response |
|---|---|
| `achieved` | Action passed. `state.current_action` advances; `state.last_action_result.verifier_pass=true`. |
| `budget-limited` | Same-signature-failure. If action's retry budget remaining, re-delegate (counter++). Else `state.terminal=blocked` with reason "auto-loop budget-limited". |
| `cancelled` | User-cancelled (or pursue's own `kill` propagated). `state.terminal=abandoned`. |
| `blocked` | Auto-loop's drift watchdog terminated. `state.terminal=blocked` with reason from auto-loop's `reason` field. |
| `unmet` | Loop still alive but verifier said no (should not appear post-return, only on cross-session resume). Re-poll. |
| `pursuing` | Loop still alive (same caveat). Re-poll. |

The last two (`unmet`, `pursuing`) only matter for cross-session resume. In a single intra-session run, the `Skill(skill: "vd:auto-loop", ...)` call returns ONLY when auto-loop terminates — so the status will always be one of the first four when SKILL.md reads it inline.

## Cross-session resume

When `/vd:pursue` is invoked again in a fresh session and finds the marker file `{goal-dir}/.pursue/delegated-to-auto-loop.json`, the resume path is:

1. Read marker → identify the action that was being delegated + the verify-script path.
2. Run `read-auto-loop-outcome.sh --auto-loop-state ${CWD}/.auto-loop` (auto-loop's state lives at the CWD it was invoked from).
3. If status ∈ {pursuing, unmet}: auto-loop is still alive in some other session (or died without writing terminal). Treat as `blocked` for safety; user can kill + restart.
4. If status ∈ {achieved, budget-limited, cancelled, blocked}: apply outcome mapping above.
5. Delete marker.
6. Resume executor loop.

## Compound verifier shape

`build-compound-verifier.sh` writes a single-purpose `verify-pursue-{action}.sh` that:

- Reads the per-action verifier binding from `action-vocab.yaml`.
- Interpolates placeholders (`{pr_number}`, `{plan_dir}`, `{profile.test_cmd}`) from goal.yaml + state.json + resolved profile.
- Translates the verifier's JSON args into `--key value` flags for `eval-verifier.sh`.
- Logs per-verifier output to `iterations/{NNN}-{action}-verifier.log` (debuggable on crash).
- Exits 0 iff verifier returned `pass=true`. Auto-loop reads exit code only.

**Per-action only — NOT compound across the workflow.** v0.1 binds ONE verifier per action. If a future need arises for multiple verifiers iteration-time on one action, expand `build-compound-verifier.sh`'s inner loop. The workflow-level `goal.yaml.target.verifiers` set is wholly separate; it runs at `verify_*` actions, not during cook iteration.

## Budget translation

| pursue field | auto-loop flag | translation |
|---|---|---|
| `goal.yaml.budgets.max_iterations` | `--max-iterations` | pass-through |
| `goal.yaml.budgets.token_pct_cap` (pct of session) | `--max-tokens` | estimated as `pct × 20000` (rough — auto-loop's `ccusage` probe is the authoritative measure) |
| n/a (4h default) | `--max-wallclock` | hard-coded to `4h` for v0.1; goal.yaml could expose this in v0.2 |

The token translation is intentionally rough — auto-loop has its own ccusage-based token tracking. The mismatch is acceptable because both layers have caps; whichever fires first stops the loop.

## Recursion guard

If `VD_AUTOLOOP_DEPTH > 0` (set by auto-loop when it spawns its audit subagent), `delegate-to-auto-loop.sh` refuses with exit 4. This prevents:

```
pursue → auto-loop → audit-subagent → tries to run pursue → ∞
```

Pursue's `delegate-to-auto-loop.sh` enforces depth=0 only; auto-loop itself enforces depth bounds via its own guard (see auto-loop's hard rule #5).

## Preconditions

Before delegation, `delegate-to-auto-loop.sh` checks:

1. `/vd:auto-loop` is installed — looks for `~/.claude/skills/auto-loop/SKILL.md` (post-install path) OR `~/skills/skills/auto-loop/SKILL.md` (dev path). If neither, exit with actionable install command.
2. `VD_AUTOLOOP_DEPTH ≤ 0`.
3. Per-action verifier exists for this action in action-vocab.yaml (else "no verifier needed" — pass through, don't delegate).

## Failures during delegation

| Failure | Detection | Pursue response |
|---|---|---|
| Auto-loop not installed | precondition check exits 3 | abort delegation with user-actionable message; pursue marks `terminal=blocked` |
| Recursion guard tripped | precondition check exits 4 | abort; user must restart pursue from a non-auto-loop context |
| build-compound-verifier exits 1 (no per-action verifier) | by design — caller path | pursue treats action as "no verifier" → run-action.sh standard dispatch |
| build-compound-verifier exits 2 (input error) | rare | abort; pursue marks `terminal=blocked` |

## What this design does NOT support (v0.2)

- **Multi-action delegation in one auto-loop call.** Each delegated action gets its own auto-loop invocation. If you want "cook + test together until BOTH pass", that's a v0.2 enhancement — pursue would have to build a 2-verifier compound script and pick which action's iteration counter to credit.
- **Codex /goal delegation.** v0.1 uses Claude Code's auto-loop only. Codex deferred to v0.2 per the research report.
- **Pause/resume in the middle of auto-loop.** If you `/vd:pursue kill` while auto-loop is mid-iteration, the kill propagates via `/vd:auto-loop --cancel` (Phase 6's `kill.sh` handles this), which sets status=cancelled and pursue marks abandoned. Granular pause-without-cancel isn't supported.
