---
name: astro-airflow
description: "Inspect and debug Airflow on Astronomer (Astro) deployments — fetch DAG runs, task instance logs, container logs, env vars, and deployment state without installing an MCP plugin. Use when the user mentions Astro/Astronomer, asks about DAG runs or task logs on staging/prod, says 'check the deployment', references `astro deployment`, `make airflow`, an Astro deployment ID, or a *.astronomer.run URL. Pairs the official `astro` CLI for platform ops with direct Airflow REST API calls for DAG-level data."
license: MIT
metadata:
  author: vanducng
  version: "1.0.0"
  upstream: "https://docs.astronomer.io/astro/cli/overview"
---

# astro-airflow

Read-only debugging surface for Airflow on Astro. No MCP plugin install required — uses `astro` CLI for what it exposes (container logs, env vars, deployment metadata) and `curl` against the deployment's Airflow REST API for what it doesn't (DAG runs, task instance logs).

## When to use

- User asks "what failed in `<dag_id>`" or "why is `<dag_id>` stuck" on staging/prod
- User says "check the deployment logs", "fetch task log", "clear failed tasks" on Astro
- User references an Astro deployment ID (e.g. `cmgjr4hyl001l01lrepyhz604`) or a `*.astronomer.run/<id>` URL
- A repo's CLAUDE.md mentions Astro deployments, `make airflow CMD=...`, or `astro dev start`
- Need to compare staging vs prod env vars / connections / variables
- Debugging a CI deploy that hit Astronomer

**When NOT to use:** local-only Airflow questions where `make airflow CMD=...` or the local Astro container suffices — use those directly. This skill is for *remote* (staging/prod) inspection.

## Prerequisites

- `astro` CLI installed and logged in (`astro login <org-hostname>`) — verify with `astro context list`
- `curl` and `jq` (both standard)
- A **Deployment API token** for the target deployment, stored in gopass. Mint via Astro UI → Deployment → Access → API Tokens. Use a custom least-privilege role with `deployment.get` + `deployment.airflow.*.get` permissions for read-only debugging.
- Deployment **webserver URL** (e.g. `https://<org>.astronomer.run/<deployment-short-id>/`) — find via `astro deployment inspect <deployment-id> --key metadata.airflow_api_url`

## Core: `astro` CLI for platform ops

### Discover deployments

```bash
astro deployment list                                   # all deployments in current workspace
astro deployment inspect <deployment-id>                # full deployment metadata (JSON)
astro deployment inspect <deployment-id> --key metadata.airflow_api_url
astro deployment inspect <deployment-id> --key metadata.workload_identity
```

### Container logs (scheduler / api-server / triggerer / workers)

Container-level logs — Python tracebacks, scheduler errors, OOM kills. **Not** per-task logs. Component is a **boolean flag** (`--scheduler`, `--apiserver`, `--triggerer`, `--workers`, `--webserver`), not `--component <name>`.

```bash
astro deployment logs <deployment-id> --scheduler                       # default last 500 lines
astro deployment logs <deployment-id> --scheduler --log-count 100       # tail N lines
astro deployment logs <deployment-id> --scheduler --keyword "ImportError"
astro deployment logs <deployment-id> --scheduler --error               # level filter only
astro deployment logs <deployment-id> --apiserver                       # Airflow 3.x API server
astro deployment logs <deployment-id> --webserver                       # Airflow 2.x web UI
astro deployment logs <deployment-id> --triggerer
astro deployment logs <deployment-id> --workers --keyword "OOMKilled"
```

**Limitation:** Cannot combine `--error` (level) and `--keyword` (text) in the same call — pick one. To do both, run `--keyword "ERROR"` and grep the output for what you actually want.

Use these when:
- Scheduler isn't picking up DAGs (look for parse errors) — `--scheduler --keyword "ImportError\|Broken DAG"`
- Triggerer is crashing (async task issues) — `--triggerer --error`
- Workers OOM — `--workers --keyword "OOMKilled"`
- DAG import errors not visible in UI — `--scheduler --keyword "Broken DAG"`

### Environment variables

```bash
astro deployment variable list --deployment-id <id>                # list all (values redacted by default)
astro deployment variable list --deployment-id <id> -s             # include secret values (sensitive!)
astro deployment variable create --deployment-id <id> KEY=value    # create or update
astro deployment variable update --deployment-id <id> KEY=value
astro deployment variable copy --source-id <staging> --target-id <prod>  # promote
```

### Deploy state

```bash
astro deployment hibernate <id> --force                # pause compute
astro deployment wake-up <id>                          # resume
astro deployment pool list --deployment-id <id>        # worker pool sizing
```

## Core: Airflow REST API for DAG runs + task logs

Astro CLI does not expose per-task logs or structured DAG run state. Hit the deployment's Airflow REST API directly. **Airflow 3.x = `/api/v2/`**, **Airflow 2.x = `/api/v1/`**.

### Setup helpers (use once per session)

```bash
# Pull token from gopass, never echo it
export ASTRO_TOKEN="$(gopass show -o <path/to/deployment-token>)"

# Deployment webserver URL
export AF_URL="https://<org>.astronomer.run/<deployment-short-id>"

# Reusable curl wrapper
af() { curl -fsSL -H "Authorization: Bearer ${ASTRO_TOKEN}" "${AF_URL}$1"; }
```

### List + inspect DAG runs

```bash
# Recent runs across all DAGs (Airflow 3.x)
af "/api/v2/dags/~/dagRuns?limit=20&order_by=-start_date" | jq '.dag_runs[] | {dag_id, run_id, state, start_date}'

# Runs for a specific DAG
af "/api/v2/dags/<dag_id>/dagRuns?limit=10&order_by=-start_date" | jq

# Only failed runs in a date window
af "/api/v2/dags/<dag_id>/dagRuns?state=failed&start_date_gte=2026-05-01T00:00:00Z" | jq

# Single run detail
af "/api/v2/dags/<dag_id>/dagRuns/<run_id>" | jq
```

### Task instances for a run

```bash
# All task instances in a run
af "/api/v2/dags/<dag_id>/dagRuns/<run_id>/taskInstances" \
  | jq '.task_instances[] | {task_id, state, try_number, duration, start_date}'

# Only the failed ones
af "/api/v2/dags/<dag_id>/dagRuns/<run_id>/taskInstances?state=failed" | jq

# Specific task instance
af "/api/v2/dags/<dag_id>/dagRuns/<run_id>/taskInstances/<task_id>" | jq
```

### Task instance log (the actual log file)

```bash
# Pick a try_number from the task instance; logs are per-try
af "/api/v2/dags/<dag_id>/dagRuns/<run_id>/taskInstances/<task_id>/logs/<try_number>" \
  | jq -r '.content'

# Tail the last 200 lines (logs can be multi-MB)
af "/api/v2/dags/<dag_id>/dagRuns/<run_id>/taskInstances/<task_id>/logs/<try_number>" \
  | jq -r '.content' | tail -n 200
```

### Other useful read endpoints

```bash
af "/api/v2/dags?limit=50&only_active=true"            # list DAGs
af "/api/v2/dags/<dag_id>"                             # DAG detail
af "/api/v2/dags/<dag_id>/details"                     # parsed DAG (schedule, tasks, etc.)
af "/api/v2/importErrors"                              # DAG parse errors
af "/api/v2/connections"                               # list connections (no secrets)
af "/api/v2/variables"                                 # list Airflow Variables (values included — careful)
af "/api/v2/pools"                                     # slot pool status (find queue starvation)
af "/api/v2/monitor/health"                            # scheduler / metadata DB health
```

## Decision tree

```
User wants...                            → Use
─────────────────────────────────────────────────────────────────────
"why did this run fail"                  → REST: dagRuns → taskInstances?state=failed → logs/<try>
"any failed DAGs today"                  → REST: /dagRuns?state=failed&start_date_gte=...
"scheduler is broken / DAGs not parsing" → astro CLI: deployment logs --component scheduler
"task log for try 2 of X"                → REST: /taskInstances/X/logs/2
"worker OOM"                             → astro CLI: deployment logs --component workers --keyword OOMKilled
"what env vars are set"                  → astro CLI: deployment variable list
"copy staging vars to prod"              → astro CLI: deployment variable copy
"DAG won't import"                       → REST: /importErrors  AND  astro logs --component scheduler
"compare schedule/tasks staging vs prod" → REST: /dags/<id>/details on both URLs
"pool is starved"                        → REST: /pools
"trigger a backfill" / "clear failed"    → DO NOT — read-only token. Ask user to use Astro UI or `make airflow`.
```

## Patterns Claude should use

### Investigate "DAG X failed" end-to-end

```bash
export ASTRO_TOKEN="$(gopass show -o <path/to/staging-token>)"
export AF_URL="https://<org>.astronomer.run/<deployment-short-id>"
af() { curl -fsSL -H "Authorization: Bearer ${ASTRO_TOKEN}" "${AF_URL}$1"; }

# 1. Get most recent failed run
RUN_ID=$(af "/api/v2/dags/<dag_id>/dagRuns?state=failed&limit=1&order_by=-start_date" \
         | jq -r '.dag_runs[0].run_id')

# 2. Find failed task(s)
af "/api/v2/dags/<dag_id>/dagRuns/${RUN_ID}/taskInstances?state=failed" \
  | jq '.task_instances[] | {task_id, try_number}'

# 3. Pull the log for the failed task's last try (substitute TASK_ID and TRY from step 2)
af "/api/v2/dags/<dag_id>/dagRuns/${RUN_ID}/taskInstances/<task_id>/logs/<try>" \
  | jq -r '.content' | tail -n 200
```

### Compare staging vs prod env vars

```bash
diff \
  <(astro deployment variable list --deployment-id <staging-id> -s | sort) \
  <(astro deployment variable list --deployment-id <prod-id>    -s | sort)
```

### Tail scheduler logs for parse errors after a deploy

```bash
astro deployment logs <id> --scheduler --log-count 200 \
  --keyword "ImportError\|SyntaxError\|Broken DAG"
```

## Safety rules

- **Read-only by default.** This skill never triggers DAGs, clears tasks, or mutates state via API. If the user needs that, point them to the Astro UI or local `make airflow CMD='dags trigger ...'`.
- **Token discipline.** Pull from gopass. Never echo `$ASTRO_TOKEN` to stdout. Never write it to a file outside the gopass store. Never commit to git.
- **Distinct tokens per environment.** Don't reuse one token for staging + prod — different blast radii.
- **`--keyword` is regex, not glob.** Escape special chars (`.`, `(`, `|`).
- **Log fetch is heavy.** Task logs on Astro can be multi-MB (Kubernetes pod logs in S3). Always tail with `| tail -n 200` unless explicitly asked for full log.
- **Don't paste secret values into chat** when listing variables — summarize names only.
- **Confirm deployment ID before mutating** any env var. Astronomer offers no undo for `variable update`.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | token expired or wrong scope | Re-mint in Astro UI, update gopass |
| `403 Forbidden` on POST endpoints | token uses `WORKSPACE_MEMBER` role (POST blocked by auth proxy) | Use `DEPLOYMENT_ADMIN` or a custom role with required perms |
| `404` on `/api/v2/...` | deployment runs Airflow 2.x, not 3.x | Try `/api/v1/...` |
| `astro deployment logs` flag error `unknown flag: --component` | wrong CLI syntax | Use boolean flags: `--scheduler`, `--apiserver`, `--triggerer`, `--workers`, `--webserver` |
| `cannot query for more than one log level and/or keyword at a time` | combining `--error` + `--keyword` | Run one, grep the output for the other |
| `astro deployment logs` returns nothing | wrong component flag for Airflow version | Airflow 3.x uses `--apiserver`, not `--webserver` |
| Empty `dag_runs` array | DAG never ran, or `start_date_gte` filter too narrow | Drop the filter, check `paused` state on the DAG |
| Log fetch returns truncated content | response paginated via `continuation_token` | Loop with `?token=<continuation_token>` until empty |
| `astro` CLI returns "context not found" | not logged into the right org | `astro context list && astro context switch <name>` |

## Discovery

```bash
astro context list                          # which org/workspace am I in
astro deployment list                       # available deployments
astro version                               # CLI version (some flags need ≥ 1.30)
astro deployment inspect <id> | jq          # everything about a deployment

# Find an Airflow API endpoint surface
af "/api/v2/"                               # 3.x root
af "/api/v1/"                               # 2.x root
```

## References

- Astro CLI: https://docs.astronomer.io/astro/cli/overview
- Astro CLI command reference: https://docs.astronomer.io/astro/cli/reference
- Astro Deployment API tokens: https://docs.astronomer.io/astro/deployment-api-tokens
- Custom Deployment roles: https://docs.astronomer.io/astro/customize-deployment-roles
- Airflow 3.x REST API: https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html
- For a structured MCP alternative (adds a plugin to the deployment image, more setup), see Astronomer's `astro-airflow-mcp` package.
