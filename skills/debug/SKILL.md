---
name: debug
description: "Debug systematically across software, data pipelines, infrastructure, and analytics. Find root cause before fixing — for bugs, test failures, CI/CD breakage, K8s/Cloud incidents, dbt/Airflow pipeline failures, schema drift, freshness violations, dashboard wrong-numbers, and performance issues. Validates at every layer; verifies with fresh evidence before claiming done."
license: MIT
argument-hint: "[error or issue description]"
metadata:
  author: vanducng
  version: "1.0.0"
---

# Debug

Comprehensive debugging across the four disciplines you work in: software, data engineering, devops, analytics. Systematic investigation, root-cause-first, defense-in-depth, and verified-before-claimed-done.

## Iron law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

Random fixes waste time and create new bugs. Find root cause → fix at source → validate at every layer → verify with fresh evidence before claiming done.

## When to use

| Surface | Triggers |
|---|---|
| **Software** | test failures, bugs, exceptions, build failures, integration regressions |
| **System** | server 5xx, CI/CD pipeline failures, deploy failures, performance degradation, OOM, timeouts |
| **Data pipeline** | DAG failures, dbt test failures, source-freshness alerts, schema drift, late/missing data, row-count anomalies, lineage breaks |
| **Infrastructure** | K8s pod CrashLoopBackOff, secret rotation issues, env-var mismatch across environments, IaC drift, image pull errors, networking/policy denial |
| **Analytics / BI** | dashboards showing wrong numbers, metric drift, exposure-aware refresh failures, BI cache staleness, broken charts after model changes |
| **Always** | before claiming work complete |

## Techniques (load on demand)

### Code-level

| # | Reference | Load when |
|---|---|---|
| 1 | `references/systematic-debugging.md` | Any bug/issue requiring investigate→fix loop |
| 2 | `references/root-cause-tracing.md` | Error deep in call stack, unclear where bad data originated |
| 3 | `references/defense-in-depth.md` | Found root cause; want validation at every layer |
| 4 | `references/verification.md` | About to claim "done", "fixed", "passing" |

### System-level

| # | Reference | Load when |
|---|---|---|
| 5 | `references/investigation-methodology.md` | Server incidents, multi-component failures |
| 6 | `references/log-and-ci-analysis.md` | CI/CD failures, server errors, deploy issues |
| 7 | `references/performance-diagnostics.md` | Slow queries, high latency, resource exhaustion |
| 8 | `references/reporting-standards.md` | Producing investigation/diagnostic report |

### Discipline-specific

| # | Reference | Load when |
|---|---|---|
| 9 | `references/data-pipeline-debugging.md` | Airflow/Dagster/Prefect DAGs, dbt models/tests, Spark, freshness, schema drift, late data, lineage |
| 10 | `references/infrastructure-debugging.md` | K8s, Docker, Terraform, Helm, secrets, multi-env config, networking, image issues |
| 11 | `references/data-analytics-debugging.md` | Wrong numbers in dashboards, metric drift, fan-out joins, BI cache, exposure refresh |
| 12 | `references/frontend-verification.md` | Implementation touches `*.tsx/jsx/vue/svelte/html/css`, UI bugs, visual regressions |

### Coordination

| # | Reference | Load when |
|---|---|---|
| 13 | `references/task-management-debugging.md` | Multi-step investigation (3+), parallel evidence collection, debugger subagents |

## Quick reference

```
Code bug                 → systematic-debugging.md (Phase 1–4)
  Deep in call stack     → root-cause-tracing.md
  Cause found            → defense-in-depth.md
  About to claim done    → verification.md

System incident          → investigation-methodology.md (5 steps)
  CI/CD failure          → log-and-ci-analysis.md
  Slow / OOM / timeout   → performance-diagnostics.md
  Need a report          → reporting-standards.md

Data pipeline broke      → data-pipeline-debugging.md
Infra / K8s / env / IaC  → infrastructure-debugging.md
Dashboard wrong numbers  → data-analytics-debugging.md
Frontend / UI            → frontend-verification.md

Multi-step investigation → task-management-debugging.md
```

## Tool integration

- **Database** — `psql` for Postgres, `bq` for BigQuery, sqlit CLI for any saved connection
- **CI/CD** — `gh` CLI for GitHub Actions logs (`gh run view --log-failed`)
- **K8s** — `kubectl logs`, `kubectl describe`, `kubectl events`, `kubectl get pods -o wide`
- **dbt** — `dbt run --select`, `dbt test`, `target/run_results.json`, `target/manifest.json`, `dbt-deps`
- **Airflow / Dagster / Prefect** — UI logs + their CLIs (`airflow tasks logs`, `dagster job execute`, `prefect flow-run logs`)
- **Tracing** — APM (Datadog, Sentry), OpenTelemetry exporters
- **Codebase scout** — `vd:scout` to map files before diving in
- **Frontend** — Chrome MCP / `vd:web-e2e` (persistent-profile browser + trace evidence) for visual verification
- **Secrets** — `sops -d` for the infra repo (age key per `.mise.toml`); never paste decrypted contents into reports
- **Skills:** `vd:research` for unknown libs; `ck:problem-solving` when stuck; `vd:gopass` for credentials

## Red flags — STOP and follow process

If catching yourself thinking:

- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "It's probably X, let me fix that"
- "Should work now" / "Seems fixed"
- "Tests pass, we're done"
- "The dashboard looks right now, ship it" *(without confirming the underlying number)*
- "Pod is running, must be fixed" *(without confirming the workload actually works)*
- "Pipeline succeeded once, must be flaky" *(without trying to reproduce)*

**All mean:** return to systematic process. Run the verification step.

## Workflow position

**Typically follows:** `vd:scout` (after locating relevant code/models/manifests)

**Typically precedes:** `vd:fix` (apply the diagnosed fix), `vd:brainstorm` (when the cause exposes a design problem worth re-deciding), `vd:plan` (when the fix is large enough to phase)

**Related:** `vd:scout` (discover before debugging), `vd:research` (investigate unknown tools/CVEs surfaced during debug)
