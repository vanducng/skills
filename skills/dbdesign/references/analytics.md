# Analytics Schema Design

Use this reference for reporting, BI, warehouse, mart, and aggregated models.

## Contents

- First Decision: Grain
- Facts
- Dimensions
- Date Dimension
- Summaries And Aggregates
- Naming
- Metrics
- Analytics Checklist

## First Decision: Grain

Define what one row means before naming tables.

Examples:

- one row per order
- one row per order item
- one row per account per day
- one row per event
- one row per product per warehouse per snapshot

If grain is unclear, stop and ask. Most analytics model bugs come from mixed grain.

## Facts

Fact tables store measurements at a declared grain.

Common fact types:

- **Transaction fact:** one business event, such as an order or payment.
- **Periodic snapshot:** state at fixed intervals, such as daily inventory.
- **Accumulating snapshot:** process lifecycle with milestone timestamps, such as application funnel.
- **Factless fact:** occurrence/coverage without numeric measures, such as attendance or eligibility.

Fact table fields:

- surrogate fact key when useful
- natural/source event IDs for lineage
- foreign keys to dimensions
- degenerate dimensions such as order number
- measures with clear additivity rules
- load metadata: source, batch/run ID, loaded_at

## Dimensions

Dimensions describe facts.

- Use surrogate keys when dimensions change over time.
- Keep natural/source keys for traceability.
- Track slowly changing dimensions only when historical correctness requires it.
- Do not create dimensions for every low-value attribute; balance usability and maintenance.

Slowly changing dimension choices:

- **Type 1:** overwrite; no history.
- **Type 2:** new row with `effective_from`, `effective_to`, `is_current`.
- **Type 6/hybrid:** only when the reporting requirement demands both current and historical views.

## Date Dimension

A date dimension is useful when reporting needs fiscal calendars, holidays, week logic, or consistent date grouping. It is not always required in engines with strong date functions, but it can simplify BI semantics.

Common fields:

- `date_key`
- `full_date`
- `year`
- `quarter`
- `month`
- `week_of_year`
- `day_of_week`
- `is_weekend`
- fiscal calendar fields when needed

## Summaries And Aggregates

Create aggregate tables when:

- dashboard queries are repeated and expensive
- users need stable metric definitions
- source-level detail is too large for interactive BI
- freshness requirements tolerate scheduled refresh

Always define:

- source fact table
- aggregation grain
- refresh cadence
- incremental predicate/watermark
- late-arriving data strategy
- uniqueness key for upsert/merge

## Naming

Choose one convention and keep it consistent:

- `fact_orders`, `fact_order_items`
- `dim_customer`, `dim_product`
- `agg_daily_sales`, `summary_daily_sales`
- staging/intermediate/mart prefixes when the repo already uses dbt-style layers

## Metrics

For every measure:

- define formula
- define grain
- define filters/exclusions
- define null handling
- define additive behavior: additive, semi-additive, non-additive
- define currency/timezone conversion if relevant

## Analytics Checklist

- [ ] Grain is declared for every fact and aggregate.
- [ ] Facts and dimensions are separated by purpose.
- [ ] Measures have formulas and additivity rules.
- [ ] Source lineage and load metadata are present.
- [ ] SCD strategy is explicit where dimensions change.
- [ ] Aggregate refresh and late-data handling are defined.
- [ ] BI/dashboard query patterns map to partitioning/clustering/index strategy.
- [ ] Metric definitions avoid double counting across joins.
