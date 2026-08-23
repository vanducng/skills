---
name: astro-airflow
description: "Inspect and debug Airflow on Astronomer (Astro) deployments - DAG runs, task logs, container logs, env vars, and deployment state. Use when the user mentions Astro/Astronomer, asks about DAG runs or task logs on staging/prod, says 'check the deployment', references `astro deployment`, an Astro deployment ID, or a *.astronomer.run URL. Prefers the `af` CLI for DAG-level data and `astro` CLI for platform ops; curl is the fallback. Local astro dev -> vd:managing-astro-local-env. YAML DAG authoring -> vd:dag-factory. 'use Otto' / Airflow 2→3 upgrades -> vd:delegating-to-otto."
license: MIT
metadata:
  author: vanducng
  version: "1.2.0"
  upstream: "https://github.com/astronomer/agents/tree/main/skills/airflow"
---

# astro-airflow

Read-only debugging surface for Airflow on Astro. Pair three tools:

| Need | Tool |
|---|---|
| DAG runs, task logs, import errors, health, connections, variables, pools | `af` (Airflow REST wrapper) |
| Container logs, deployment inspect, env vars, hibernate/wake | `astro deployment ...` |
| Local `astro dev start` / parse / scheduler restart | `vd:managing-astro-local-env` |
| Create or edit YAML DAGs | `vd:dag-factory` |
| User says "use Otto", long audit, Airflow 2→3 upgrade | `vd:delegating-to-otto` |
| Deep RCA after logs are in hand | `vd:debug` then `vd:fix` |
| `af` not installed or no remote instance configured | curl against `/api/v2/` (Airflow 3) or `/api/v1/` (Airflow 2) |

**When NOT to use:** local-only Airflow (`astro dev start`, parse, pytest) - that is `vd:managing-astro-local-env`. YAML authoring is `vd:dag-factory`. This skill is remote (staging/prod) inspection, plus wiring `af` at those URLs.

## Prerequisites

- `astro` CLI ≥ 1.42, logged in (`astro login`; verify with `astro context list`)
- `curl` + `jq`
- `af` optional but preferred: `uv tool install astro-airflow-mcp` (one-shot: `uvx --from astro-airflow-mcp af`)
- A Deployment / Workspace / Organization API token in gopass for curl fallback. Mint via Astro UI → Deployment → Access → API Tokens. Least-privilege: `deployment.get` + `deployment.airflow.*.get`.

Always resolve the live deployment ID first. IDs in project docs go stale.

```bash
astro deployment list
astro deployment inspect <deployment-id> --key metadata.airflow_api_url
```

## Choose the interface

1. **Named Otto / upgrade / long investigation** → `vd:delegating-to-otto`.
2. **`af` on PATH (or `uvx --from astro-airflow-mcp af`) and a configured instance** → use `af`. See [references/af.md](references/af.md).
3. **Platform / container logs / env vars** → `astro deployment ...` below.
4. **Otherwise** → curl fallback.

`af instance discover` **creates API tokens in Astro Cloud**. Always `--dry-run` first and get explicit approval before a real discover.

```bash
uvx --from astro-airflow-mcp af instance list
uvx --from astro-airflow-mcp af instance discover --dry-run
# only after the user says yes:
# uvx --from astro-airflow-mcp af instance discover astro
uvx --from astro-airflow-mcp af instance use <name>
```

Add by hand (token from gopass, never echo it):

```bash
uvx --from astro-airflow-mcp af instance add staging \
  --url "https://<org>.astronomer.run/<short-id>" \
  --token "$ASTRO_TOKEN"
```

If `af` prints `reading from the legacy ~/.af/config.yaml`, tell the user `af migrate` exists; do not run it unasked.

## Platform ops: `astro` CLI

### Container logs

Component is a **boolean flag or `--component <name>`** (CLI 1.45+). Airflow 3.3+ parse/import lives on **`--dag-processor`**, not only `--scheduler`. Airflow 3.x API is `--apiserver`; `--webserver` is Airflow 2.x.

`--keyword` is an **exact phrase**, not a regex. Do **not** combine `--error`/`--warn`/`--info` with each other or with `--keyword` - the CLI prints usage and exits. Official help examples that show `--error --info` are wrong on 1.45.x.

`--error` is not a reliable level filter: it can return `[info]` lines whose text contains "error" (DAG ids like `el_twilio__error_code`). Prefer `--keyword "ImportError"` on `--dag-processor`.

```bash
astro deployment logs <deployment-id> --scheduler --log-count 100
astro deployment logs <deployment-id> --dag-processor --keyword "ImportError"
astro deployment logs <deployment-id> --component scheduler --log-count 50   # CLI 1.45+
astro deployment logs <deployment-id> --apiserver --log-count 50
astro deployment logs <deployment-id> --triggerer --error
astro deployment logs <deployment-id> --workers --keyword "OOMKilled"
```

Use these when:

- DAGs not appearing / parse errors → `--dag-processor --keyword "ImportError"` (and `--scheduler` on older runtimes)
- Triggerer crashing → `--triggerer --error`
- Worker OOM → `--workers --keyword "OOMKilled"`

### Environment variables and deploy state

```bash
astro deployment variable list --deployment-id <id>            # values redacted
astro deployment variable list --deployment-id <id> -s         # secrets (sensitive)
astro deployment inspect <id>
astro deployment pool list --deployment-id <id>
```

Create/update/copy variables only when the user explicitly asks. Confirm the deployment ID first; Astronomer has no undo.

## DAG-level: prefer `af`

Once an instance points at the target deployment:

```bash
af health
af dags errors
af dags list
af runs list --dag-id <dag_id>
af runs diagnose <dag_id> <run_id>
af tasks logs <dag_id> <run_id> <task_id>
af tasks logs <dag_id> <run_id> <task_id> --try 2
af config pools
af api ls --filter xcom
```

Mutations (`af dags unpause`, `af runs trigger`, `af runs clear`, `af runs delete`) are **opt-in** - only when the user explicitly asks. Default is read-only.

Full command map: [references/af.md](references/af.md).

## Curl fallback (Airflow REST)

Use when `af` is missing or has no remote instance. **Airflow 3.x = `/api/v2/`**, **Airflow 2.x = `/api/v1/`**.

```bash
export ASTRO_TOKEN="$(gopass show -o <path/to/deployment-token>)"
export AF_URL="https://<org>.astronomer.run/<deployment-short-id>"
afcurl() { curl -fsSL -H "Authorization: Bearer ${ASTRO_TOKEN}" "${AF_URL}$1"; }
```

Do not name the wrapper `af()` - that shadows the real CLI.

Any Astro API token works as `Authorization: Bearer` (Deployment preferred, then Workspace, then Organization). The same value works for the `astro` CLI via `ASTRO_API_TOKEN`.

### Runs and tasks

**URL-encode `run_id`** - scheduled IDs contain `+` / `:`.

```bash
afcurl "/api/v2/dags/~/dagRuns?limit=20&order_by=-start_date" \
  | jq '.dag_runs[] | {dag_id, run_id, state, start_date}'

afcurl "/api/v2/dags/<dag_id>/dagRuns?limit=10&order_by=-start_date" | jq
afcurl "/api/v2/dags/<dag_id>/dagRuns?state=failed&start_date_gte=2026-05-01T00:00:00Z" | jq
afcurl "/api/v2/dags/<dag_id>/dagRuns/${RUN_ID}/taskInstances?state=failed" | jq
```

### Task logs (Airflow 3.x: `content` is events, not a string)

Verified on Airflow 3.1-3.3: the log endpoint returns
`{"content":[{event, timestamp, sources, ...}, ...], "continuation_token":"..."}`.
`jq -r '.content'` prints nothing useful. Iterate `.content[] | .event`.

```bash
afcurl "/api/v2/dags/<dag_id>/dagRuns/<run_id>/taskInstances/<task_id>/logs/<try_number>?full_content=true" \
  | jq -r '.content[] | select(type=="object") | .event' | grep -v '^::' | tail -n 200
```

`full_content=true` returns the first full block. Replay `continuation_token` as `?token=` until it stops advancing. Running tasks do return logs mid-run.

Airflow 2.x `/api/v1/` still returns `.content` as a plain string.

### Other reads

```bash
afcurl "/api/v2/dags?limit=50&only_active=true"
afcurl "/api/v2/dags/<dag_id>/details"
afcurl "/api/v2/importErrors"
afcurl "/api/v2/connections"
afcurl "/api/v2/variables"     # values included - do not paste secrets
afcurl "/api/v2/pools"
afcurl "/api/v2/monitor/health"
```

### Mutations (opt-in)

```bash
afw() { curl -fsSL -X "$1" -H "Authorization: Bearer ${ASTRO_TOKEN}" -H "Content-Type: application/json" "${AF_URL}$2" -d "$3"; }

afw PATCH "/api/v2/dags/<dag_id>?update_mask=is_paused" '{"is_paused": false}'
afw POST  "/api/v2/dags/<dag_id>/dagRuns" '{"dag_run_id":"manual__e2e","logical_date":null}'
afw PATCH "/api/v2/dags/<dag_id>/dagRuns/<run_id>" '{"state":"failed"}'
```

**`max_active_runs=1`:** unpausing can spawn a scheduled run, so a manual trigger sits queued behind it. Terminate the redundant queued run if the user wants only one.

## Decision tree

```
User wants...                            → Use
─────────────────────────────────────────────────────────────────────
"use Otto" / AF2→3 upgrade / long audit  → vd:delegating-to-otto
"why did this run fail"                  → af runs diagnose  (else curl dagRuns → failed TIs → logs)
"any failed DAGs today"                  → af runs list / curl /dagRuns?state=failed
"scheduler broken / DAGs not parsing"    → astro logs --dag-processor  AND  af dags errors
"task log for try 2 of X"                → af tasks logs ... --try 2
"worker OOM"                             → astro logs --workers --keyword OOMKilled
"what env vars are set"                  → astro deployment variable list
"pool is starved"                        → af config pools
"trigger / clear failed"                 → only if user asks; prefer af, else curl. Never with a read-only token.
```

## Investigate "DAG X failed"

```bash
# 1. most recent failed run
af runs list --dag-id <dag_id>
# fallback:
RUN_ID=$(afcurl "/api/v2/dags/<dag_id>/dagRuns?state=failed&limit=1&order_by=-start_date" \
         | jq -r '.dag_runs[0].run_id')

# 2. diagnose (af) or list failed tasks (curl)
af runs diagnose <dag_id> "$RUN_ID"
afcurl "/api/v2/dags/<dag_id>/dagRuns/${RUN_ID}/taskInstances?state=failed" \
  | jq '.task_instances[] | {task_id, try_number}'

# 3. logs - NEVER jq -r '.content' on Airflow 3
af tasks logs <dag_id> "$RUN_ID" <task_id>
afcurl "/api/v2/dags/<dag_id>/dagRuns/${RUN_ID}/taskInstances/<task_id>/logs/<try>?full_content=true" \
  | jq -r '.content[] | select(type=="object") | .event' | grep -v '^::' | tail -n 200
```

## Safety rules

- **Read-only by default.** Do not trigger, clear, pause, or update variables unless the user asks.
- **Token discipline.** Pull from gopass. Never echo `$ASTRO_TOKEN`. Never write it outside the password store. Never commit it.
- **Distinct tokens per environment.**
- **`--keyword` is an exact phrase.** Do not pass `foo|bar` regex.
- **Log fetch is heavy.** Tail with `| tail -n 200` unless asked for the full log.
- **Do not paste secret variable values into chat.**
- **Confirm deployment ID** (`astro deployment list`) before any mutation.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | token expired or wrong scope | Re-mint in Astro UI, update gopass |
| `403 Forbidden` on POST | token role is `WORKSPACE_MEMBER` (POST blocked) | `DEPLOYMENT_ADMIN` or a custom role with the write perm |
| `404` on `/api/v2/...` | Airflow 2.x | Use `/api/v1/` |
| `astro deployment logs` prints Flags/Usage and exits | combined `--error`+`--keyword` or two level flags; or bad deployment ID | One filter only; re-run `astro deployment list` |
| `unknown flag: --component` | Astro CLI < 1.45 | Upgrade, or use `--scheduler` / `--dag-processor` / `--apiserver` |
| `--error` returns `[info]` lines | text contains "error" (DAG id, message) | Use `--keyword` on `--dag-processor` instead |
| `No matching logs` with `foo\|bar` | `--keyword` is exact phrase, not regex | Search one literal at a time |
| Empty `dag_runs` | never ran, or date filter too tight | Drop the filter; check `is_paused` |
| Log body looks empty | `jq -r '.content'` on Airflow 3 events | Use `.content[] \| .event` |
| Truncated logs | `continuation_token` | Loop `?token=` until unchanged |
| `af: command not found` | CLI not installed | `uvx --from astro-airflow-mcp af` |
| `af` only shows localhost | no remote instance | `instance discover --dry-run` then ask; or `instance add` |
| `context not found` | wrong org | `astro context list && astro context switch <name>` |

## Discovery

```bash
astro version
astro context list
astro deployment list
astro deployment inspect <id> --key metadata.airflow_api_url
uvx --from astro-airflow-mcp af instance list
```

## References

- `af` command map: [references/af.md](references/af.md)
- Official Airflow ops skill (af-centric): https://github.com/astronomer/agents/blob/main/skills/airflow/SKILL.md
- Astro CLI: https://docs.astronomer.io/astro/cli/overview
- Airflow 3 REST API: https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html
- Otto delegation: `vd:delegating-to-otto`
