# goal.yaml schema (v1)

The single source of truth for "what is this pursue run trying to accomplish?" Written once at intake; can be edited mid-flight (re-read each iteration).

## Top-level keys

| Key | Type | Required | Description |
|---|---|---|---|
| `version` | int | yes | Schema version. Always `1` for v0.1. |
| `slug` | string | yes | Kebab-case identifier derived from short_goal. Max 40 chars. Stable for the life of the goal. |
| `created` | RFC3339 datetime | yes | When the goal was initialized. |
| `short_goal` | string | yes | One-line user intent, verbatim from `/vd:pursue "<text>"`. |
| `project` | object | yes | See "project" below. |
| `target` | object | yes | See "target" below. |
| `actions` | list[string] | optional | Override the project profile's `default_sequence`. When omitted, profile wins. |
| `autonomy` | enum | yes | `manual` / `semi` / `auto`. Default at intake is `semi`. |
| `budgets` | object | yes | See "budgets" below. |
| `risk_tier` | enum | optional | `low` / `medium` / `high`. When `high`, Phase 2's `resolve` auto-includes `plan_audit` action. |

## `project`

| Key | Type | Description |
|---|---|---|
| `name` | string | Resolved from profile lookup. e.g. `goclaw`. |
| `remote_url` | string | Captured from `git remote get-url origin` at intake. |
| `worktree_path` | string | Absolute path to the worktree dir created by intake (`null` when `--reuse`). |
| `branch` | string | The feature branch name. |

## `target`

| Key | Type | Description |
|---|---|---|
| `kind` | enum | `local` (no ship) / `pr-only` (ship to PR, no deploy) / `cluster` (ship + deploy + cluster verify). |
| `env` | string | Free-text env hint. e.g. `staging`, `production`. |
| `verifiers` | list[Verifier] | **WORKFLOW-LEVEL verifiers — run only at dedicated `verify_*` actions post-deploy.** Per-action iteration-time verifiers come from `action-vocab.yaml`, NOT here. See "two verifier layers" below. |

## `budgets`

| Key | Type | Default | Description |
|---|---|---|---|
| `max_iterations` | int | 30 | Global iteration cap. Hard halt → `blocked`. |
| `max_rebases` | int | 3 | Per-rebase-action cap. |
| `max_ci_reruns` | int | 2 | Per-CI-rerun cap. |
| `token_pct_cap` | int | 80 | Prompt-back via `AskUserQuestion` when token usage hits this %. |

## `Verifier` (used in `target.verifiers` AND in `action-vocab.yaml`)

```yaml
type: ci_green | pod_image_matches | http_status | cmd_exits_zero | test_suite_passes | manual_confirm | shell
args:
  # type-dependent. See references/verifier-vocab.md.
```

## Two verifier layers — IMPORTANT

| Layer | Source | Runs when |
|---|---|---|
| Per-action verifiers | `action-vocab.yaml` (per action: e.g. `cook` → `test_suite_passes`) | Every iteration of the bound action (e.g. cook iteration loop) |
| Workflow-level verifiers | `goal.yaml.target.verifiers` (e.g. `ci_green`, `pod_image_matches`, `http_status`) | Only at the dedicated `verify_*` actions, POST-deploy |

**Never mix them.** Running `ci_green` during cook iteration loops would fail forever (no PR yet). Phase 5's compound verifier wraps ONLY the per-action set when delegating to `auto-loop`; `verify_*` phases run the workflow-level set separately.

## Worked example: goclaw bugfix targeting cluster

```yaml
version: 1
slug: cron-retry-fix
created: 2026-05-25T13:50:00+07:00
short_goal: "fix cron job retry logic so failed tasks re-queue at exponential backoff"

project:
  name: goclaw
  remote_url: git@github.com:dataplanelabs/goclaw.git
  worktree_path: /Users/vanducng/git/personal/dataplanelabs/worktrees/goclaw-cron-retry-fix
  branch: fix/cron-retry

target:
  kind: cluster
  env: production
  verifiers:
    - type: pod_image_matches
      args:
        deployment: goclaw
        namespace: goclaw
        expected_image_template: "ghcr.io/dataplanelabs/goclaw:{tag}-full"
    - type: http_status
      args:
        url: https://goclaw.everest.dataplanelabs.io/healthz
        expected_code: 200

autonomy: semi

budgets:
  max_iterations: 30
  max_rebases: 3
  max_ci_reruns: 2
  token_pct_cap: 80

risk_tier: medium
```

Per-action verifiers (NOT in this file — they're bound in `action-vocab.yaml`):

```yaml
# action-vocab.yaml fragment (Phase 2):
cook:
  delegated_to: auto-loop
  verifier:
    type: test_suite_passes
    args:
      target: "go test ./..."  # filled from project profile
ship:
  verifier:
    type: ci_green
    args:
      pr_number: ${state.pr_number}
```

## Mid-flight edits

Editing `goal.yaml` while pursue is running is supported — the executor re-reads on every iteration. Common edits:

- Switch `autonomy: semi → auto` to skip remaining gates.
- Bump `budgets.max_iterations` to extend a stuck run.
- Add a verifier to `target.verifiers` when post-deploy checks reveal a missing assertion.

Avoid changing `slug`, `created`, or `version` — those break resume.

## Validation

`scripts/init-goal.sh` writes goal.yaml from the intake answers; no separate validator. Consumers (resolve-workflow.sh, run-action.sh) read it via `yq` (preferred) or Python `~/.claude/skills/.venv/bin/python3 -c 'import yaml,sys; print(yaml.safe_load(sys.stdin)[...])'` (fallback). Malformed YAML → consumer errors out with the parse error; the goal is unrecoverable until the user fixes it.
