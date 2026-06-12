# Investigation Methodology

Five-step structured investigation for system-level issues, incidents, and multi-component failures across software, data, and infrastructure stacks.

## When to use

- Server returning 5xx or unexpected responses
- Behavior changed without obvious code changes
- Multi-component failure spanning services, DBs, queues, pipelines
- Pipeline ran "successfully" but data is wrong
- Pod / container restarted, then app degraded
- Need to understand "what happened" before fixing

## Step 1 — Initial assessment

**Establish scope and impact before diving in.**

1. **Collect symptoms** — error messages, affected endpoints/DAGs/dashboards, user reports
2. **Identify affected components** — services, databases, message queues, schedulers, BI surfaces
3. **Determine timeframe** — when did it start? Correlate with deployments / model runs / config changes / cron windows
4. **Assess severity** — users affected? data integrity at risk? revenue impact? reporting blackout?
5. **Check recent changes** — git, deploy logs, infra/IaC drift, dependency bumps, dbt model changes, schema migrations

```bash
# Recent app deploys (GitHub Actions)
gh run list --limit 10
# Recent commits across the relevant repo
git log --oneline -20 --since="2 days ago"
# Config / IaC / DAG / dbt changes
git diff HEAD~5 -- '*.env*' '*.config*' '*.yml' '*.yaml' '*.json' '*.tf' '*.sql' 'dags/' 'models/'
# K8s recent rollout
kubectl rollout history deployment/<name> -n <ns>
# dbt manifest / run results recency
ls -la target/manifest.json target/run_results.json 2>/dev/null
```

## Step 2 — Data collection

**Gather evidence systematically before analysis.**

| Source | What to pull |
|---|---|
| App logs | Filter by timeframe and affected components; look for first error in the window |
| CI/CD logs | `gh run view <run-id> --log-failed` |
| Database state | Slow queries, lock contention, recent migrations, row counts on impacted tables |
| K8s | `kubectl logs --previous`, `kubectl describe pod`, `kubectl get events --sort-by=.lastTimestamp` |
| Pipeline | Airflow/Dagster/Prefect task logs; `target/run_results.json` for dbt |
| Metrics | CPU, memory, disk, network, p50/p95/p99 latency, request rate |
| External deps | Provider status pages, third-party API health, DNS, CDN cache state |

```bash
# GitHub Actions failed run
gh run view <run-id> --log-failed
gh run view <run-id> --log > /tmp/ci.log

# K8s
kubectl logs <pod> -n <ns> --previous
kubectl describe pod <pod> -n <ns>
kubectl get events -n <ns> --sort-by=.lastTimestamp | tail -50

# dbt
cat target/run_results.json | jq '.results[] | select(.status != "success")'
```

For codebase orientation:
- `vd:scout` — locate the relevant files / models / manifests
- `repomix` — generate a fresh codebase summary if `docs/codebase-summary.md` is missing or stale

## Step 3 — Analysis

**Correlate evidence across sources.**

1. **Timeline reconstruction** — order events chronologically across all logs (mind timezones)
2. **Pattern identification** — recurring errors, time windows, affected segments (users / tenants / regions)
3. **Execution path tracing** — follow the request / job / DAG through the system
4. **Data integrity check** — for data issues, compare row counts, distributions, joins before/after
5. **Dependency mapping** — which components depend on the failing one? Which feed it?

**Key questions:**
- Does the issue correlate with a specific deploy / migration / DAG run / config change?
- Intermittent or consistent?
- All users / all rows, or a subset?
- Upstream cause (data) or downstream symptom (rendering)?
- Same problem reproducible in dev/staging?

## Step 4 — Root cause identification

**Eliminate hypotheses systematically with evidence.**

1. **List hypotheses** ranked by evidence strength
2. **Test each** — design the smallest possible experiment that confirms or rejects
3. **Validate with evidence** — logs, metrics, queries, reproduction steps
4. **Consider environmental factors** — race conditions, resource limits, env-var drift across environments, DST, off-by-timezone
5. **Document the chain** — full event sequence from trigger to symptom

**Avoid:** fixing the first hypothesis without testing alternatives. Multiple plausible causes require elimination.

## Step 5 — Solution development

**Targeted, evidence-backed fixes.**

1. **Immediate fix** — minimum change to restore service (rollback, scale, hotfix, disable a DAG, revert a model)
2. **Root cause fix** — address the underlying issue permanently
3. **Preventive measures** — monitoring, alerts, validation, dbt tests, K8s probes, defense-in-depth
4. **Verification plan** — how to confirm the fix actually works (in prod, with fresh evidence)

**Prioritize:** impact × urgency. Restore service first, then fix root cause, then prevent recurrence.

## Discipline-specific entry points

| Surface | Continue to |
|---|---|
| Code-level fix | `systematic-debugging.md` (Phases 1–4) |
| Deep call stack | `root-cause-tracing.md` |
| After fix, harden | `defense-in-depth.md` |
| Claiming done | `verification.md` |
| CI/CD failure | `log-and-ci-analysis.md` |
| Slow / OOM / latency | `performance-diagnostics.md` |
| dbt / Airflow / Spark | `data-pipeline-debugging.md` |
| K8s / Docker / IaC / multi-env | `infrastructure-debugging.md` |
| Wrong numbers in BI | `data-analytics-debugging.md` |
| Frontend / UI regression | `frontend-verification.md` |
