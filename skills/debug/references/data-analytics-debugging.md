# Data Analytics / BI Debugging

When a dashboard shows the wrong number, a metric drifts from yesterday, or a chart breaks after a model change. Numbers-look-fine bugs are the worst kind - they ship and stakeholders trust them.

## When to use

- Dashboard shows a number that "feels off" (and stakeholders are about to act on it)
- Metric drifted vs yesterday / last week / same period last year
- Two dashboards report different values for the "same" metric
- Chart broke after a dbt model change (column renamed, type changed)
- Scheduled refresh succeeded but the data is stale (BI cache bug)
- Filters behave inconsistently across charts
- New dimension produces fan-out (rows multiply unexpectedly)
- Conformance issue - same dim joined differently in two marts

## First triage - *trust nothing yet*

Before chasing logic, rule out the boring causes:

1. **Filter state** - is the user looking at the right time window / segment? (Half of "wrong number" tickets are this.)
2. **Refresh / cache** - when was the last refresh? Are you reading a cached snapshot?
3. **Permissions / row-level security** - different users see different rows; the "expected" number may be from someone with broader access
4. **Same definition?** - is the metric in two places defined the same way? "Revenue" vs "Net revenue" vs "GMV" lookalikes are common
5. **Timezone / day boundary** - is the dashboard in user TZ, server TZ, or UTC?

Resolve these first. Don't refactor SQL until you've confirmed it's actually a SQL problem.

## Wrong-number debugging - top down

Trace the metric **from where it's wrong** back to the warehouse:

```
Dashboard chart  →  BI query  →  Semantic / metric layer  →  Mart model  →  Intermediate  →  Staging  →  Source
```

For each layer, run the **same metric** and compare:

```sql
-- Mart: what does the model compute?
SELECT date_trunc('day', event_time) AS d, SUM(amount) AS revenue
FROM <project>.<schema>.fct_orders
WHERE event_time BETWEEN <start> AND <end>
GROUP BY 1 ORDER BY 1;

-- BI semantic layer: what does the chart compile to? (Lightdash: copy SQL from chart; Looker: SQL Runner)
-- Compare row-by-row - first divergence point is the layer that introduced the bug
```

Run the same period on:
- the **mart** (raw SQL)
- the **semantic layer's compiled SQL** (Lightdash → "SQL" tab; Looker → SQL Runner; Cube → "Generated SQL")
- the **dashboard tile** (export underlying data)

The first place they diverge is your bug. Common discoveries:

- Semantic layer applies a default filter (`is_deleted = false`) the mart didn't expect
- Chart-level filter quietly excludes rows
- Aggregation type wrong (avg of avg ≠ overall avg)
- Time grain mismatch (chart truncates differently than mart)

## Fan-out joins - the silent multiplier

Symptom: a number looks "too high" - usually a multiple of the real value (2×, N×).

Cause: joining a fact to a dim where the dim has multiple rows per join key, multiplying the fact rows.

Detect:

```sql
-- Before the join: row count of the fact at the grain you expect
SELECT count(*) FROM fct_orders WHERE date = '<day>';

-- After the join: same count
SELECT count(*) FROM fct_orders f JOIN dim_customer d USING(customer_id) WHERE f.date = '<day>';
```

If counts differ → the join is a fan-out. Either:
- Pre-aggregate the dim to one row per key (`select distinct` or window dedup)
- Switch to a left semi join / `EXISTS`
- Use a snapshot table with `valid_from / valid_to`

In dbt, add a **uniqueness test** on the dim to make this impossible to ship:

```yaml
columns:
  - name: customer_id
    tests:
      - unique
      - not_null
```

## Metric drift across dashboards

Two dashboards say different things about the same metric.

Diagnosis order:

1. **Definition** - open both compiled SQL queries side-by-side. Same source? Same filters? Same grain?
2. **Semantic-layer divergence** - both use the metric definition, or one has a hand-rolled query?
3. **Refresh time** - different cache state?
4. **Currency / unit** - one returns cents, the other dollars
5. **Inclusion rules** - `is_test_account`, `is_internal`, deleted records

Fix at the **definition** layer. If both dashboards reference the same metric in the semantic layer, only one definition exists to break.

## BI cache / refresh issues

| Symptom | Cause | Action |
|---|---|---|
| Numbers stuck on yesterday | Cache not invalidated | Force refresh; check refresh schedule; check exposure-aware refresh |
| Chart shows old data, table shows new | Per-tile cache TTL | Align cache TTLs to the slowest tile, or invalidate on model materialize |
| Scheduled refresh "succeeded" but data old | Ran against a stale source view, or partition wasn't loaded yet | Check upstream load completion before BI refresh; introduce a sensor |
| Some rows updated, others stale | Partial refresh, partition-by-partition | Confirm all partitions in the window were re-materialized |

For Lightdash: check `manifest.json` exposures - the BI knows which dbt models back which dashboards; refresh order should follow the lineage.

## Schema-change-broke-the-chart

Symptom: a chart errors with `column "x" does not exist` or returns null where it shouldn't.

Cause: an upstream dbt model renamed/dropped a column the BI references.

Investigation:

1. **Lineage** - `target/manifest.json` `child_map` for the model that changed. Cross-reference exposures.
2. **Where is the column referenced?** - grep BI YAML / LookML / Lightdash YAML / SQL of saved questions
3. **Compatibility** - can you reintroduce the column as an alias on the new schema? `select new_name as old_name` for one release window while consumers update

Add an **exposure** in `schema.yml` for every dashboard that depends on a model - this surfaces the dependency in `dbt docs` and lineage tools, so the next renamer sees what they're about to break.

## Conformance issues

Two marts join `customer_id` differently → numbers don't reconcile.

Causes:
- Different grain in the conformed dim (`dim_customer` includes test accounts in one mart, not in the other)
- SCD type-1 vs type-2 mismatch - one mart joins the current customer state, another joins the state at event time
- Late-arriving records - the dim row for a customer didn't exist when the fact landed

Fix at the dim level - one canonical `dim_customer` everyone uses, with explicit semantics on `is_test_account`, `valid_from`, `valid_to`.

## Time / timezone bugs

| Bug | Symptom | Fix |
|---|---|---|
| UTC vs local TZ | Day-boundary metrics shift by ~5–8h | Standardize: store UTC, render local; document everywhere |
| DST transition | One day has 23 or 25 hours; aggregates blip | Use date arithmetic in the warehouse's stable type, not naive timestamps |
| Week start | "Week 1" includes different days in two reports | Settle on ISO weeks (Mon–Sun) or US (Sun–Sat); document |
| Snapshot at midnight skipped | Data exists only between 00:00 and the BI refresh; midnight queries return empty | Refresh after the load completes, not on a clock |

## Performance - dashboard takes minutes to load

Same playbook as warehouse perf (`performance-diagnostics.md` § Warehouse). Most BI slowness is one of:

- Dashboard fires N queries, each hitting the same large table → consolidate via a mart or materialized view
- No partition / cluster pruning - chart filter doesn't push down to the warehouse
- Heavy `JOIN` on a non-clustered key
- "Top 1000 by date" with no pre-aggregation

Inspect the BI's compiled SQL → run `EXPLAIN` / view the query plan. The fix usually lives in the mart, not the dashboard.

## After-fix verification (specific to analytics)

Don't claim "metric fixed" without:

- **Re-run the mart** and compare to baseline (yesterday or N days ago)
- **Re-render the dashboard** and confirm the number visually
- **Cross-check** another consumer of the same metric - if metric drift was the symptom, both should now agree
- **One spot-check** of a single record's contribution end-to-end (source row → mart → semantic layer → chart)

Then `verification.md` - fresh evidence before claiming done.
