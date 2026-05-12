# Verify + prevent

This is the **most-skipped** step and the one that decides whether the fix actually held. Two halves: prove the fix works with fresh evidence; leave a guard so the bug class can't recur silently.

## Iron rule

```
NO "DONE" WITHOUT A FRESH RERUN OF THE EXACT FAILING COMMAND
```

Memory of "I think it should work now" is not evidence. Re-execute. Capture output. Compare against the pre-fix baseline from Step 2.

## Verification (mandatory)

1. **Rerun the exact failing command** captured in Step 2.
   - dbt: same `dbt run --select X` / `dbt test --select X` invocation.
   - Airflow: clear the failed task instance and rerun; check the new task log.
   - Backend: re-issue the failing request (curl/HTTP client), or rerun the failing test (`go test -run`, `pytest -k`, `npm test -- -t`).
   - Frontend: reproduce in the same browser/viewport; reload from scratch; ideally screenshot.
   - CI: `gh run rerun --failed`, watch logs; or trigger the affected workflow.
   - Terraform: `terraform plan` → expect "No changes" (or precisely the expected change set); then `apply` in lower env first.
   - K8s: `kubectl rollout restart` (if config-driven); `kubectl get pods -w` for stability; `kubectl logs --previous` to confirm no new crash loop.
2. **Compare to baseline.** State both sides: before = exact error string; after = exact success output. If the "after" is qualitatively different (different log line, different status, different shape), say so — partial fix is not full fix.
3. **Run adjacent suites** that touch the same module. dbt → run downstream tests (`+model_name`). Backend → run the package's test file, not just the single test. Frontend → run e2e for the affected flow if one exists.
4. **Parallel verification** when possible: typecheck + lint + unit + build in parallel `Bash` invocations.

If verification fails → back to Step 2 (re-diagnose with the new evidence). **3 failed verification cycles → STOP**, surface to the user, question whether the architecture / approach is wrong.

## Regression guard (mandatory unless `--no-prevent`)

Add a test/check that **fails without the fix** and **passes with it**. Confirm both directions when feasible (revert the fix locally, see the test fail, restore).

Per surface:

| Surface | Guard |
|---|---|
| **Backend** | Unit test exercising the cause; if user-reachable, integration test against the API. |
| **Frontend** | Component test for the broken state; e2e if reachable from user flow. |
| **dbt** | A dbt test (`not_null`, `accepted_values`, `dbt_utils.expression_is_true`, custom singular test) targeting the invariant that broke. |
| **Airflow** | Task-level assertion (e.g. row-count check, freshness sensor) or a unit test on the operator code. |
| **CI/CD** | A workflow step that fails fast on the bad-input condition (e.g. schema diff, lockfile drift, secret-presence check). |
| **Terraform** | A policy check (OPA/conftest), `terraform validate`, or an integration test in CI; failing-`plan` test if structural. |
| **K8s** | Liveness/readiness probe that catches the failure mode; or a Helm test / `kubectl wait` in the deploy job. |

A regression guard is **not** the same as adding logging. Logging helps you debug next time; a guard prevents the failure.

## Defense-in-depth (recommended)

Where cheap, add a guard one layer *above* the bug:
- DB constraint / `NOT NULL` / check constraint when the cause was bad data.
- Type narrowing / parsed-don't-validate when the cause was a wrong shape.
- Schema test at the source for upstream drift.
- Resource limits / PDB / probe for a runaway pod.
- CI guard for the class of misconfiguration that caused the incident.

One layer up is enough. Don't add five guards; pick the one that gives the most coverage per line of code.

## Done criteria

- [ ] Baseline command reran; output captured and compared.
- [ ] Adjacent suites pass.
- [ ] Regression guard added (or `--no-prevent` with explicit user OK and a follow-up ticket).
- [ ] Defense-in-depth considered; added where cheap.
- [ ] No new TODOs about the fix itself.
- [ ] Diff is minimal and matches the diagnosis.

Only after every box → declare done.
