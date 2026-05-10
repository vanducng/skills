# Data Pipeline Debugging

dbt, Airflow / Dagster / Prefect, Spark, streaming. The class of failure that *looks* successful in monitoring but ships wrong data.

## When to use

- DAG / job failure
- dbt model or test failure
- Source freshness alert
- Schema drift between upstream and downstream
- Late-arriving / missing data
- Row counts diverge from yesterday or from upstream
- Lineage / dependency break (downstream model fails because upstream changed)
- Idempotency violation — re-running produces different output
- Spark stage stall / OOM / shuffle skew

## Root-cause hierarchy

Pipeline failures cluster into a few classes. Identify which one **first** before fixing.

| Class | What "fixed" looks like | Common false fix |
|---|---|---|
| **Source data** | Upstream contract restored | Re-running the DAG (data still wrong) |
| **Schema drift** | Schema diff resolved on both sides | Casting in SQL (hides the drift, ships next week) |
| **Logic bug** | Updated SQL / transform | Backfilling without finding the cause |
| **Orchestration** | Scheduling / dependency / pool fix | Bumping concurrency until it works |
| **Idempotency** | Job is replay-safe | Marking the job "manual-only" |
| **Resource** | Memory / slot / partition tuned | Bumping memory until it stops crashing |
| **Backpressure** | Downstream catches up | Disabling alerts |

## dbt failures

### dbt run failure

```bash
# Re-run the failing model in isolation, with full SQL compiled
dbt run --select <model_name> --debug

# Show compiled SQL without running
dbt compile --select <model_name>
cat target/compiled/<project>/models/<path>/<model>.sql

# What changed since last successful run?
git log --oneline -- models/<path>/<model>.sql

# Inspect manifest for upstream/downstream
jq '.nodes["model.<project>.<model>"]' target/manifest.json
jq '.parent_map["model.<project>.<model>"]' target/manifest.json
jq '.child_map["model.<project>.<model>"]' target/manifest.json
```

Look at `target/run_results.json` for failure timing and message:

```bash
jq '.results[] | select(.status != "success") | {unique_id, status, message, execution_time}' target/run_results.json
```

### dbt test failure — wrong rows

Use `--store-failures` to materialize the offending rows for inspection:

```bash
dbt test --select <test_or_model> --store-failures
```

Then in the warehouse:

```sql
-- failure table is created in <schema>_dbt_test__audit
SELECT * FROM <schema>_dbt_test__audit.<failure_table> LIMIT 100;
```

For relationships / unique / not_null tests, the failure rows tell you exactly which key/value pair triggered. **Don't add `where` filters to silence the test** — that hides the contract break.

### Source freshness violation

```bash
dbt source freshness --select source:<source_name>
```

Investigation:

1. Is the upstream loader running? (Airflow / Fivetran / Stitch / dlt status.)
2. Is the source watermark column updating? (`select max(<freshness_col>) from <source>`.)
3. Is upstream credentials / connection still valid?
4. Is the freshness window correct, or did upstream cadence legitimately change?

### Schema drift

Symptom: dbt errors with `column "x" of relation "..." does not exist`, or downstream model shows `null` where data should be.

```sql
-- Compare info_schema before and after suspected change
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = '<schema>' AND table_name = '<table>'
ORDER BY ordinal_position;
```

Decide:

- Add the new column to staging model + schema.yml + downstream
- Or add `on_schema_change: append_new_columns` if drift is expected
- Don't auto-cast away type changes — they bury data quality issues

### Idempotency check

A pipeline that doesn't replay safely is a time bomb. To check:

1. Pick a small partition / day
2. Run twice
3. Compare: row counts, hashes, key uniqueness

```sql
SELECT count(*), count(DISTINCT <pk>), md5(string_agg(md5(t.*::text), '' ORDER BY <pk>))
FROM <model> t WHERE <partition_col> = '<day>';
```

If results differ between runs → the model isn't idempotent. Common causes: `current_timestamp` in the SQL, non-deterministic ordering, append-only without dedup, surrogate keys from `row_number()` over unstable orders.

## Airflow / Dagster / Prefect

### Airflow

```bash
# Task logs
airflow tasks logs <dag_id> <task_id> <execution_date>

# Why is a task not running?
airflow tasks states-for-dag-run <dag_id> <execution_date>

# Pool / concurrency
airflow pools list
airflow config get-value core parallelism
airflow config get-value core dag_concurrency
```

Common failures:
- **Task stuck in `queued`** → pool full, executor saturated, scheduler heartbeat
- **Task `up_for_retry`** → infrastructure / transient cause; retry policy
- **Task `failed` immediately** → import error in DAG file; check scheduler logs for `DagBag` errors
- **DAG not appearing** → import error, file not in `DAGS_FOLDER`, `is_paused_upon_creation`

### Dagster

```bash
dagster run logs <run_id>
dagster asset materialize --select <asset_name>
```

Useful patterns:
- **Asset partition missing** — check `materialize_partitions` invocation; partition definition matches expected key
- **Asset stale** — upstream materialized after downstream; reconciliation sensor

### Prefect

```bash
prefect flow-run logs <flow_run_id>
prefect deployment ls
prefect work-pool ls
```

## Spark / PySpark

| Symptom | Investigation |
|---|---|
| Stage skew (one task takes 10× the others) | Salt the join key, broadcast small dim, repartition |
| Shuffle spill / OOM on executor | Increase executor mem, reduce partitions size, avoid wide transforms |
| Driver OOM | `collect()` / `toPandas()` on large data — replace with file write |
| Slow `groupBy` | Pre-aggregate, use `reduceByKey` / window |
| Task stuck "running" | Check Spark UI → executor logs → likely GC death |

Spark UI is the ground truth — stages, tasks, shuffle read/write, GC time, peak memory. Don't debug from logs alone.

## Streaming (Kafka / Pub/Sub)

| Symptom | Check |
|---|---|
| Consumer lag growing | Throughput vs production rate; partition rebalance; processing time per message |
| Duplicate / out-of-order messages | Idempotent consumer, watermark logic, exactly-once semantics |
| Schema registry mismatch | Producer wrote schema v2, consumer expects v1 |
| Dead-letter queue filling | Look at the DLQ message — usually deserialization or downstream rejection |

## Backfill discipline

A backfill is a destructive replay. Before running:

1. Confirm the **window** (start / end timestamps, inclusive/exclusive)
2. Confirm the **target** (table, partition, schema)
3. Confirm **idempotency** — re-running the window must not duplicate
4. Confirm **downstream impact** — what materializes after this lands?
5. Run a **small slice first** (one day) and verify row counts before going wide

Defense-in-depth (`defense-in-depth.md`) applies here too — add bounds checks at the entry points of backfill logic so an off-by-one window can't wipe a year of data.

## Data quality validation after a fix

Don't claim "pipeline fixed" without:

- **Row count vs baseline** (yesterday or N days ago) within tolerance
- **Distribution check** — top-N values match expected; null rate hasn't moved
- **PK / FK** — uniqueness still holds; FKs resolve
- **dbt tests pass** for the model and immediate downstream
- **One spot check** of a known-good record end-to-end

Then go to `verification.md` for the general gate.
