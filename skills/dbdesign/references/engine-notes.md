# Engine-Specific Notes

Use this reference when DDL must target a specific database engine.

## PostgreSQL

Design defaults:

- Prefer `timestamptz` for timestamps that represent real-world moments.
- Prefer `numeric` for money and exact measurements.
- Prefer `jsonb` over `json` when querying JSON fields.
- Use `COMMENT ON TABLE` and `COMMENT ON COLUMN` for documentation.
- Use partial indexes for active rows, sparse predicates, and soft-delete filters.
- Use GIN indexes for `jsonb`, arrays, and full-text search.
- Use BRIN indexes for very large append-only tables ordered by time or ID.
- Remember PostgreSQL has no MySQL-style `ON UPDATE CURRENT_TIMESTAMP`; use triggers or application updates.
- Use `CREATE INDEX CONCURRENTLY` for large production tables when appropriate, outside transaction blocks.

Primary key choices:

- `bigint generated ... as identity` for sequential IDs.
- `uuid` when IDs need distributed generation or unguessability.

## MySQL And MariaDB

Design defaults:

- Use InnoDB for transactions and foreign keys.
- Use `utf8mb4` charset and a modern unicode collation.
- Use `decimal` for money, not float/double.
- Use table and column comments in DDL.
- MySQL has no native partial indexes; model active-row indexes differently.
- Keep indexed `varchar` lengths practical.
- Use `datetime` when timezone conversion is not desired; understand `timestamp` range/timezone behavior.
- `ON UPDATE CURRENT_TIMESTAMP` can maintain `updated_at`.

## SQLite

Design defaults:

- Enable foreign keys per connection with `PRAGMA foreign_keys = ON`.
- Store dates/times consistently, usually ISO text or integer epoch.
- Use CHECK constraints for enum-like values.
- SQLite typing is dynamic; strict tables may be useful when available.
- Partial indexes are available in modern SQLite.
- Comments are not native; if schema documentation matters, create metadata tables or keep a design doc.
- Some ALTER TABLE operations require table rebuilds in older versions or complex changes.

## Cloudflare D1

D1 is SQLite-based. Use SQLite rules plus edge/runtime constraints:

- keep queries small and indexed
- avoid large long-running transactions
- document schema externally or with metadata tables
- design for application-level migration tooling and deployment order
- verify current platform limits in Cloudflare docs before relying on specific size or throughput ceilings

## BigQuery

BigQuery is columnar analytics storage, not OLTP.

Design defaults:

- No traditional indexes; use partitioning and clustering.
- Partition large fact/event tables by date/timestamp or integer range.
- Cluster by high-value filter/group columns, up to the engine limit.
- Use nested/repeated fields when denormalization reduces joins and matches access patterns.
- Use `OPTIONS(description=...)` for table and column descriptions.
- Avoid `SELECT *` in examples and cost-sensitive workflows.
- Design with scan cost, partition pruning, and materialized views/scheduled queries in mind.

## MongoDB

Document modeling is access-pattern driven:

- Embed one-to-few child objects that are usually read/written with the parent.
- Reference one-to-many or many-to-many relationships that grow independently.
- Avoid unbounded arrays in hot documents.
- Model indexes from query shapes and sort order.
- Use schema validation for critical fields.
- Decide whether transactions are necessary or whether document-level atomicity is enough.
- Design shard keys from cardinality, write distribution, and query routing needs.

## Engine Checklist

- [ ] DDL syntax matches target engine.
- [ ] Type choices match engine semantics.
- [ ] Comments/metadata use engine-supported mechanisms.
- [ ] Index, partition, or clustering strategy matches engine behavior.
- [ ] Migration constraints and locking behavior are considered.
- [ ] Any volatile platform limits are checked against current official docs before being quoted.
