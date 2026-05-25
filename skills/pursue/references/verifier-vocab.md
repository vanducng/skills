# Verifier vocabulary (v1)

The closed set of verifier types `vd:pursue`'s executor (Phase 3+) can evaluate. Six built-ins + `shell` escape hatch. No DSL.

`verifier-vocab.yaml` is the machine-readable shadow; `scripts/lint-vocab-sync.sh` enforces the two stay in sync.

## Two layers (recap from goal-schema.md)

- **Per-action verifiers** — bound in `action-vocab.yaml` per action. Run iteration-time during the action's loop (e.g. cook → `test_suite_passes` runs every iteration of cook).
- **Workflow-level verifiers** — listed in `goal.yaml.target.verifiers`. Run only at the dedicated `verify_*` phases POST-deploy. NEVER mixed with per-action runs.

## Verifier table

| type | args (required) | exit-code contract | latency hint |
|---|---|---|---|
| `ci_green` | `pr_number: int`, `repo: string` (default = origin) | pass = all checks bucket != "pending" AND conclusion = "success" | fast (single `gh` call) |
| `pod_image_matches` | `deployment: string`, `namespace: string`, `expected_image: string`, `kube_context: string` (optional) | pass = jsonpath output == expected_image | fast |
| `http_status` | `url: string`, `expected_code: int (default 200)`, `headers: dict (optional)` | pass = curl `%{http_code}` == expected_code | network-dependent |
| `cmd_exits_zero` | `cmd: string`, `cwd: string (default ".")` | pass = shell exec exit code == 0 | varies (delegates to cmd) |
| `test_suite_passes` | `target: string` (the test command — e.g. `go test ./...`, `pytest`, `make test`) | pass = test command exit code == 0 | medium-to-slow |
| `manual_confirm` | `prompt: string` | pass = user answers "Yes" via `AskUserQuestion` (handled inline by SKILL.md — see below) | user-dependent |
| `shell` | `cmd: string`, `expected_exit: int (default 0)`, `expected_output_contains: string (optional)` | pass = exit + (optional) output match | varies |

## Runner contract (`scripts/eval-verifier.sh`)

Every verifier invocation goes through `eval-verifier.sh --type <type> --args <json>` (or via per-type flag). The runner:

1. Captures stdout + stderr to `iterations/NNN-{action}-verifier-{i}.log` (per-verifier crash-debuggable).
2. Returns JSON on stdout: `{"pass": bool, "evidence": "<short string>", "latency_ms": int}`.
3. Always exits 0 (verifier failure is data, not script error). Exit 2 reserved for "verifier crashed" — e.g. malformed JSON from underlying tool.

Phase 3's `update-state.sh` reads the runner's JSON and merges `verifier_pass` + `verifier_evidence` into `state.last_action_result`.

## `manual_confirm` sentinel pattern

Bash scripts can't invoke `AskUserQuestion`. So `eval-verifier.sh --type manual_confirm` returns:

```json
{"pass": null, "evidence": "needs_user_input", "needs_user_input": true, "prompt": "<the prompt from args>"}
```

SKILL.md (Phase 3 executor) detects `needs_user_input: true` and:
1. Invokes `AskUserQuestion(prompt)` directly.
2. Calls `eval-verifier.sh --type manual_confirm --resolve <yes|no>` to write the journal entry + return a real `{pass: bool}`.

This is the only verifier with a two-step protocol; all others are synchronous from the script's POV.

## Per-type detail

### `ci_green`

```bash
gh pr checks $pr_number --repo $repo --json name,bucket,conclusion
```

Pass when: the JSON array is non-empty AND every entry has `bucket != "pending"` AND `conclusion == "success"`. (Pending checks = not done yet; the verifier itself doesn't poll. Phase 4's `wait_ci` Monitor handles that wait, then this verifier runs once.)

### `pod_image_matches`

```bash
kubectl --context $kube_context get deployment $deployment -n $namespace -o jsonpath='{.spec.template.spec.containers[0].image}'
```

Pass when: output == `$expected_image`. Note: container index `[0]` is hard-coded for v0.1; multi-container deployments need `shell` verifier escape.

### `http_status`

```bash
curl -s -o /dev/null -w "%{http_code}" -H "$header1" ... $url
```

Pass when: code == `$expected_code`. Headers are optional list of `Key: Value`. No body assertion in v0.1; use `shell` if you need that.

### `cmd_exits_zero`

```bash
( cd $cwd && eval "$cmd" )
```

Pass when: exit code == 0. The `eval` is intentional (the cmd may include pipes, redirects). Trust the goal file — it's user-authored, not untrusted input.

### `test_suite_passes`

```bash
eval "$target"
```

Same as `cmd_exits_zero` semantically, but separate type to signal intent + allow per-runner optimization later (e.g. parsing JUnit XML for richer evidence). For v0.1 just runs + checks exit.

### `shell` (escape hatch)

```bash
output=$(eval "$cmd" 2>&1)
exit_actual=$?
```

Pass when: `exit_actual == expected_exit` AND (if `expected_output_contains` set) output contains that substring. Use sparingly — if a `shell` verifier appears more than 2-3 times in a profile, it's probably a sign for a new built-in.

## Adding a new verifier type

Three steps (mirror to action vocab):

1. Add row here.
2. Mirror in `verifier-vocab.yaml`.
3. Add a `--type X` case in `scripts/eval-verifier.sh` returning the standard JSON contract.

Test in isolation via the smoke pattern: feed a known-good and known-bad input to the new verifier; assert the JSON output.

## Non-goals (intentionally absent)

- Custom verifier code per-goal. Use `shell` cmd if the built-ins don't fit.
- Verifier composition syntax (AND/OR/NOT). The compound-verifier in Phase 5 ALWAYS runs ALL bound verifiers and ANDs the results; if you need OR, that's `shell`.
- Async verifiers (long-running, e.g. wait-for-deployment). `eval-verifier.sh` is synchronous; long-running waits use `Monitor` actions instead.
