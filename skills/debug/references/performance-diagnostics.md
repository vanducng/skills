# Performance Diagnostics

Identify bottlenecks, analyze query performance, develop optimization strategies. Covers app code, OLTP/OLAP databases, data pipelines, and BI surfaces.

## When to use

- Response times degraded vs baseline
- App feels slow or unresponsive
- Queries taking too long (warehouse or transactional)
- High CPU / memory / disk / network utilization
- Pipeline runs are expanding (longer than yesterday, missing SLA)
- Dashboard takes minutes to load
- Resource exhaustion / OOM

## Diagnostic process

### 1. Quantify

Measure before optimizing. Establish baseline and current state - with numbers.

- Expected vs actual response time?
- When did degradation start? (Correlate with deploys, model changes, data volume.)
- Which endpoints / queries / DAGs / dashboards are affected?
- Consistent or intermittent?
- Specific tenant / segment / region?

### 2. Identify the bottleneck layer

```
Request → Network → Web server → App → Cache → Database / Warehouse → Filesystem
                                          ↓
                                External APIs / Services / Pipelines
```

| Layer | Check | Tool |
|---|---|---|
| Network | Latency, DNS, TLS handshake | `curl -w` timing, traceroute, network logs |
| Web server | Request queue, connection count | Server metrics, access logs |
| App | CPU profiling, GC, heap | APM (Datadog/Sentry/NR), pprof, py-spy, `process.memoryUsage()` |
| Cache | Hit rate, eviction | Redis `INFO stats`, app metrics |
| Database (OLTP) | Query time, locks, conn pool | `EXPLAIN ANALYZE`, `pg_stat_statements`, `pg_stat_activity` |
| Warehouse (OLAP) | Slot/scan/cost | BigQuery query plan, Snowflake QUERY_HISTORY, query profile |
| Filesystem | I/O wait, disk usage | `iostat`, `df -h`, `du -sh` |
| External APIs | Response time, timeouts, retries | Request logging with durations, vendor status |

## Database - Postgres / MySQL / MariaDB

### Postgres slow queries

```sql
-- Requires pg_stat_statements
SELECT query, calls, mean_exec_time, total_exec_time, rows
FROM pg_stat_statements
ORDER BY mean_exec_time DESC LIMIT 20;

-- Active right now
SELECT pid, now() - pg_stat_activity.query_start AS duration, state, query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;

-- Locks
SELECT blocked.pid AS blocked_pid, blocking.pid AS blocking_pid,
       blocked.query AS blocked_query, blocking.query AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking ON blocking.pid = ANY(pg_blocking_pids(blocked.pid));

-- Table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC LIMIT 20;

-- Missing index candidates (high seq scans)
SELECT relname, seq_scan, seq_tup_read, idx_scan
FROM pg_stat_user_tables
WHERE seq_scan > 100 AND seq_tup_read > 10000
ORDER BY seq_tup_read DESC;

-- Connection pool
SELECT count(*), state FROM pg_stat_activity GROUP BY state;
```

### Postgres query plans

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) <query>;
```

Look for: sequential scans on large tables, nested loops with high row counts, sorts without indexes, excessive buffer hits, hash joins spilling to disk.

### Lock investigation

```sql
SELECT * FROM pg_locks WHERE NOT granted;
```

## Warehouse - BigQuery / Snowflake / Redshift

### BigQuery

```bash
# Cost / bytes scanned for a query
bq query --use_legacy_sql=false --dry_run "<sql>"

# Recent jobs
bq ls -j --max_results=20 -a
bq show -j <job_id>     # job stats: bytes processed, slot ms, plan
```

Look for:

- **Bytes scanned** - partition/cluster pruning working?
- **Slot ms** - long-running stages, hot stages
- **Stage skew** - one stage doing 90% of the work → reshuffle / repartition
- **Reading the same table multiple times** in one query → CTE materialization, intermediate table

### Snowflake

```sql
-- Recent expensive queries
SELECT query_id, query_text, total_elapsed_time, bytes_scanned, warehouse_name
FROM table(information_schema.query_history(result_limit => 100))
WHERE start_time > dateadd('hour', -2, current_timestamp())
ORDER BY total_elapsed_time DESC;
```

Then `SELECT system$explain_plan_json('<sql>');` or use the Query Profile UI for stage breakdown. Watch for spilling to local/remote disk.

## App-layer bottlenecks

| Issue | Symptom | Fix |
|---|---|---|
| N+1 queries | Many small DB calls per request | Batch / eager-load / dataloader |
| Memory leak | Memory grows monotonically | Heap profile, check listeners, caches without eviction |
| Blocking I/O | High response time, low CPU | Async, connection pooling |
| CPU-bound | High CPU, scales with load | Algorithm review, caching, offload to worker |
| Connection exhaustion | Intermittent timeouts | Pool sizing, connection reuse, idle timeout |
| Large payload | Slow transfers, high mem | Pagination, streaming, compression |
| GC pauses | Periodic latency spikes | Tune GC, reduce allocation rate |

## Data pipeline performance

| Symptom | Investigation |
|---|---|
| dbt run getting longer | `dbt run --select state:modified+ --defer` partial; check materialization (table → incremental); review tests; look at `target/run_results.json` durations |
| One model dominates runtime | Add clustering / partitioning; reduce columns scanned; review join keys |
| Spark stage skew | Salted joins, broadcast small tables, repartition |
| Airflow concurrency | `parallelism`, `dag_concurrency`, `max_active_tasks_per_dag`; pool sizing |
| Slot starvation (BQ) | Reservation / on-demand mix; query concurrency limits |

## Optimization strategy

**Priority order:**

1. **Quick wins** - missing index, fix N+1, enable cache, partition pruning, broadcast join
2. **Configuration** - pool sizes, timeouts, buffer sizes, worker count, DAG concurrency
3. **Code / SQL changes** - algorithm, data structure, model materialization (table vs incremental vs view)
4. **Architecture** - caching layer, read replica, async processing, CDN, columnar store, materialized view

**Always:** measure after each change. One change at a time.

## Reporting

Include in the diagnostic:

- **Baseline vs current** with numbers (latency p95, query duration, bytes scanned, $)
- **Bottleneck identified** with evidence (plan, profile, log snippet)
- **Root cause** explanation
- **Recommended fixes** with expected impact and effort
- **Verification plan** - how to confirm improvement landed
