# Playbook — Data pipeline (Airflow + dbt)

Load this when the failure is in a DAG, dbt model/test, source freshness, schema drift, late/missing data, or incremental/snapshot logic.

## First-look checklist

- **Where did it break?** Airflow task vs dbt-inside-task. Read the actual task log, not just the UI status.
- **Reproducible?** Same input data and code → same failure? If yes, run locally with `dbt run --select <model>` or the operator's local equivalent.
- **Did inputs change?** Source schema, source freshness, partition key, upstream model lineage (`dbt list --select +model`).
- **Did code change?** `git log -p` on the model, the macro, the DAG file, and `dbt_project.yml` / `profiles.yml`.
- **Idempotency state?** Incremental model: is the `unique_key` actually unique? Snapshot: did the `updated_at` collapse? Airflow task: is it safe to clear+rerun, or will it double-write?

## Airflow — fix patterns

| Symptom | Likely cause | Fix shape |
|---|---|---|
| Task fails immediately on import | Python import error in DAG file | Fix import; verify with `airflow dags list`. Don't push DAG fixes you haven't parsed locally. |
| Task fails on first op | Bad operator args / templated render error | Check `Rendered Template` in UI. Fix template vars or default_args. |
| Task succeeds but downstream sees no data | Wrong partition / wrong table / silent return | Add row-count assertion at end of task. Verify in warehouse with `sqlit` / `bq`. |
| Sensor times out | Upstream actually missing OR poke interval too tight | Confirm upstream first via direct query, **before** loosening sensor. |
| Retries succeed eventually | Real flakiness vs hidden race | Reproduce manually. If flake is real, fix the race; if not, fix the underlying cause. Loosening retries is not a fix. |
| Backfill produces wrong values | Idempotency broken (delete-insert vs merge) | Fix the operator/SQL to be re-runnable. Re-backfill the affected window after the fix. |

**Verification:** clear the task (`Clear` in UI or `airflow tasks clear`), let it run, watch the log, then query the warehouse with the exact row-count / sum that defined "correct".

## dbt — fix patterns

| Symptom | Likely cause | Fix shape |
|---|---|---|
| `not_null` / `unique` test fails | Upstream data violates contract OR model logic introduces dupes | Fix the **model SQL** (dedupe with `qualify row_number() = 1` on the right key) or fix the source. Don't relax the test. |
| `relationships` test fails | Orphan rows / FK not enforced | Add a left-anti-join filter, or backfill the missing parent rows. Document why if filter. |
| Incremental model returns wrong rows | `is_incremental()` predicate too loose / `unique_key` mismatch | Tighten the predicate. Full refresh once after the fix to heal history (`--full-refresh`). |
| Snapshot has collapsed history | `updated_at` is null or non-monotonic | Choose a real change-detection column or switch to `check` strategy. Rebuild snapshot in a non-prod env first. |
| Freshness alert | Source pipeline behind OR `loaded_at_field` wrong | Confirm latest row in warehouse before changing the freshness config. |
| Schema drift / column missing | Upstream changed | Update the staging model + add a source `tests:` entry to catch next drift early. |
| Compile error / macro fails | Recent macro edit OR package upgrade | `dbt deps`, `dbt parse`, check `target/manifest.json` diff. |

**Verification (dbt):**
```
dbt run --select <model>+1 --vars '{...}'   # or the exact target used in CI
dbt test --select <model>+
```
Then `sqlit` query (or `bq` / `psql`) for the actual row count / KPI that defined "correct".

## Cross-cutting

- **Source schema change:** add or update the source `tests:` so this isn't your future surprise.
- **Backfill plan:** state the window explicitly: `dbt run --select <model> --vars '{"start_date": "...", "end_date": "..."}'`. Don't assume the next scheduled run will heal history — it usually won't.
- **Lineage check after fix:** `dbt list --select state:modified+` to see who's downstream. Run their tests too.
- **Exposures / dashboards:** if the fix shifts a KPI, ping the exposure owner (check `meta.owner` in `exposures.yml`). Don't ship silent KPI changes.

## Done criteria (data-pipeline-specific)

- [ ] Failing model/task reran cleanly with the exact prod-style args.
- [ ] dbt tests pass for the model AND its downstream (`+model`).
- [ ] Row count / KPI verified directly in the warehouse, not inferred from "the job passed".
- [ ] Backfill window stated (or "not needed because …").
- [ ] Source `tests:` updated if upstream contract was the cause.
- [ ] Exposure owners notified if KPI shifted.
