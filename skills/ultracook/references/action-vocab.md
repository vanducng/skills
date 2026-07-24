# Action vocabulary (v1)

The closed set of actions `vd:ultracook`'s executor (Phase 3) can dispatch. Each action maps to one existing `vd:*` skill OR a shell command, with optional verifier binding + parallelism + gating hint.

`action-vocab.yaml` in this same directory is the **machine-readable shadow** of this table. They must stay in sync; `scripts/lint-vocab-sync.sh` enforces this (run in Phase 2's smoke test, can be wired to CI later).

## Action table

| name | dispatch | default_args | verifier (per-action) | parallel_with | gate_default | delegated_to |
|---|---|---|---|---|---|---|
| `scout` | skill `vd:scout` | - | - | `[research]` | never | - |
| `research` | skill `vd:research` | - | - | `[scout]` | never | - |
| `brainstorm` | skill `vd:brainstorm` | `--deep` | - | - | `semi`,`manual` | - |
| `plan` | skill `vd:plan` | `--deep` | `cmd_exits_zero(test -d {plan_dir})` | - | `semi`,`manual` | - |
| `plan_audit` | skill `vd:plan-audit` | `{plan_dir}` | - | - | when risk_tier=high | - |
| `cook` | skill `vd:cook` | `--auto {plan_dir}` | `test_suite_passes` (per profile) | - | never (long-running) | `vd:auto-loop` |
| `code_review` | agent `code-reviewer` | - | - | `[test]` | never | - |
| `test` | skill `vd:test` | - | `test_suite_passes` | `[code_review]` | never | `vd:auto-loop` |
| `ship` | skill `vd:ship` | `{ship_mode}` (from profile) | `ci_green({pr_number})` | - | `semi`,`manual` | - |
| `wait_ci` | monitor `gh pr checks {pr_number}` | - | - | - | never | - |
| `image_build_wait` | monitor `gh run view {run_id}` | - | - | - | never | - |
| `reconcile` | shell `{profile.deploy.reconcile_cmd}` | - | - | - | never | - |
| `rollout_check` | shell `{profile.deploy.rollout_cmd}` | - | `cmd_exits_zero({profile.deploy.rollout_cmd})` | - | never | - |
| `verify_pod_image` | shell `kubectl get …` | - | `pod_image_matches` (from target.verifiers) | - | never | - |
| `verify_smoke` | shell `{profile.verify.smoke_cmd}` | - | workflow-level set from `target.verifiers` | - | `semi`,`manual` | - |
| `debug` | skill `vd:debug` | - | - | - | never | - |
| `fix` | skill `vd:fix` | - | - | - | never | - |
| `docs` | skill `vd:docs` | - | - | - | never | - |
| `journal` | skill `vd:journal` | - | - | - | never (auto on terminal) | - |
| `done` | terminal | - | - | - | - | - |
| `block` | terminal | - | - | - | - | - |

## Column semantics

- **dispatch** - how SKILL.md invokes the action. One of:
  - `skill <name>` - invoke via `Skill(skill: "<name>", args: ...)`.
  - `agent <subagent-type>` - invoke via `Agent(subagent_type: ..., prompt: ...)`.
  - `monitor <cmd>` - invoke via `Monitor` tool; the command polls + emits events.
  - `shell <cmd-template>` - invoke via `Bash`; template variables resolve from profile + state.
  - `terminal` - no dispatch; the executor sets `state.terminal=<name>` and exits the loop.
- **default_args** - concatenated to dispatch when no goal.yaml override. Template variables `{plan_dir}`, `{pr_number}`, `{run_id}`, `{ship_mode}` come from state/profile.
- **verifier (per-action)** - runs every iteration of this action (e.g. cook's `test_suite_passes` runs every iteration of the cook loop). NOT the same as workflow-level `target.verifiers`.
- **parallel_with** - list of action names this action can run alongside in the same iteration (independent work, no file ownership clash). Phase 3+'s executor can fire a batch in a single tool message.
- **gate_default** - autonomy modes in which this action gates by default (`AskUserQuestion` before execute). Either `never`, one or more of `{manual, semi}`, or a conditional like `when risk_tier=high`. The `--manual` mode forces a gate on EVERY action regardless of this column; `--auto` forces no gate ever.
- **delegated_to** - `vd:auto-loop` when this action's iteration is hosted by that skill (Phase 5). The compound verifier is built from the per-action verifier set.

## Adding a new action

Three steps:

1. Add a row here with all columns filled.
2. Mirror in `action-vocab.yaml` (machine-readable).
3. Add the dispatch implementation in `scripts/run-action.sh` (Phase 3) - pattern-match on the action name; dispatch via the column shape.

If adding requires a NEW dispatch type (not skill/agent/monitor/shell/terminal), that's a v0.2 change; document the design first.

## Adding a new verifier type → see `verifier-vocab.md`

Verifier types are a separate closed-set vocabulary. Adding one requires updating:
- `verifier-vocab.md` (this table's sibling)
- `verifier-vocab.yaml`
- `scripts/eval-verifier.sh` (Phase 3)

## Non-goals (intentionally absent)

- Mid-pipeline branching (`if cook fails → debug → re-cook`). Phase 3's executor handles this via the same-signature-failure recognizer + `state.last_failure_signature`; it's runtime control flow, not vocab.
- Custom verifier types per-action via inline lambdas. Use the `shell` verifier as the escape hatch.
- A DAG-style dependency graph. The action list in `goal.yaml.actions` is a linear sequence; parallelism is a hint inside an iteration, not a top-level DAG. Multi-goal DAGs are v0.2.
