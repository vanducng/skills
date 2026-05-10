# Log & CI/CD Analysis

Collect and analyze logs from servers, CI/CD pipelines, container orchestrators, and pipeline runners.

## GitHub Actions

### List and inspect

```bash
gh run list --limit 10                      # recent runs across workflows
gh run list --workflow=ci.yml --limit 5     # one workflow
gh run view <run-id>                        # step-by-step status
gh run view <run-id> --log-failed           # only failed step logs
gh run view <run-id> --log > /tmp/ci.log    # full logs
gh run rerun <run-id> --failed              # re-run failed jobs only
```

### Common failure patterns

| Pattern | Likely cause | What to check |
|---|---|---|
| Passes locally, fails CI | Environment diff | Node/Python version, OS, env vars, secrets, locale |
| Intermittent failures | Race condition / flaky test | Run 3×; check timing, shared state, ordering |
| Timeout failures | Resource limits, infinite loop | Step duration trend, CPU/mem during run |
| Permission errors | Token / OIDC / secret misconfig | `GITHUB_TOKEN` perms, secret names, `permissions:` block |
| Dependency install fails | Registry / version conflict | Lockfile diff, registry status, transitive bumps |
| Build OK, tests fail | Test env setup | DB seed, fixtures, container start, network policy |
| Deploy step fails | Cloud auth / quota | OIDC role trust, project quota, image not yet pushed |

### Analyzing failed steps

1. `gh run view <id>` — find which step failed
2. `gh run view <id> --log-failed` — focused output
3. Search for: `Error:`, `FAIL`, `exit code`, stack traces, `panic:`, `Traceback`
4. Annotations: `gh api repos/{owner}/{repo}/check-runs/{id}/annotations`

## Kubernetes

```bash
# Pod state
kubectl get pods -n <ns> -o wide
kubectl describe pod <pod> -n <ns>           # events, probes, image pull, scheduling
kubectl logs <pod> -n <ns>
kubectl logs <pod> -n <ns> --previous        # last crash
kubectl logs <pod> -n <ns> -c <container>    # specific container
kubectl logs -l app=<name> -n <ns> --tail=200

# Events (most useful when pod won't start)
kubectl get events -n <ns> --sort-by=.lastTimestamp | tail -50

# Rollout
kubectl rollout history deployment/<name> -n <ns>
kubectl rollout status deployment/<name> -n <ns>

# Resource pressure
kubectl top pod -n <ns>
kubectl top node
```

### Common K8s failure patterns

| Symptom | Investigation |
|---|---|
| `CrashLoopBackOff` | `kubectl logs --previous`; check entrypoint, env vars, secret refs |
| `ImagePullBackOff` | image tag, registry creds, network policy to registry |
| `Pending` | `kubectl describe pod` → events: insufficient CPU/mem, no matching node selector, taints |
| `OOMKilled` | bump memory limit; `dmesg` on node; review resource leak |
| Liveness probe failing | probe timing too aggressive vs warmup; check `initialDelaySeconds` |
| App reachable in-cluster, not external | Service / Ingress / Gateway / NetworkPolicy / DNS |

## Server / app logs

### Collection strategy

1. **Locations** — app logs, container stdout, web server access logs, structured-log destination (Datadog / Loki / Cloud Logging / CloudWatch / Sentry)
2. **Filter by timeframe** — narrow to incident window
3. **Correlate by request id / trace id** — follow a single request across services
4. **Look for patterns** — error spike, error rate change, unusual payloads, retry storms

### Cross-source correlation

1. Align timestamps across sources (mind timezones)
2. Build the timeline — first error → propagation → user impact
3. Identify trigger — what changed immediately before the first error
4. Map blast radius — which endpoints / tenants / regions are affected

### Key fields to prioritize

`timestamp`, `level`, `message`, `stack trace`, `request_id`, `trace_id`, `user_id`, `tenant_id`, `endpoint`, `status_code`, `duration_ms`

## CI/CD-specific data pipeline failures

| Tool | First place to look |
|---|---|
| Airflow | UI → DAG run → task instance → "Log" tab; or `airflow tasks logs <dag> <task> <execution-date>` |
| Dagster | UI → Run → Logs; or `dagster run logs <run-id>` |
| Prefect | UI → Flow Run → Logs; or `prefect flow-run logs <id>` |
| dbt (orchestrated) | `target/run_results.json` of the failing run; if not retained, re-run with `--debug` |

### dbt test failures

```bash
# Re-run a single failing test with full SQL compiled
dbt test --select test_name --store-failures --debug

# Inspect the failed-rows table dbt creates
psql -c "select * from <schema>_dbt_test__audit.<test_name> limit 50;"

# Check manifest for the model + downstream
jq '.nodes["model.<project>.<model>"]' target/manifest.json
```

## Application log pattern recognition

| Pattern | Likely class |
|---|---|
| Sudden spike | Deploy, config change, external dep failure |
| Gradual increase | Resource leak, data growth, degradation |
| Periodic failures | Cron jobs, scheduled tasks, resource contention, DST/timezone bug |
| Single endpoint | Code bug, data issue, specific dep |
| All endpoints | Infra, DB, network, auth provider |
| Timezone-shaped spike | Cron offset, daylight-savings, region rollover |

## Evidence preservation

Always capture relevant excerpts for the diagnostic report:

- Exact error messages and stack traces
- Timestamps and request/trace ids
- Before/after comparison (normal vs error state)
- Counts and frequencies
- For data issues: row-count diffs, sample rows, schema diff

Trim aggressively. A 10-line excerpt with the error is better than a 5000-line dump.
