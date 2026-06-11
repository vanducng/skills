# Migration And Review Reference

Use this reference for schema-change plans, migration SQL review, partitioning, backfills, and production safety.

## Contents

- Migration Risk Classes
- Safe Expansion/Contraction
- Backfills
- Index Rollout
- Partitioning
- Rollback
- Review Checklist

## Migration Risk Classes

Low risk:

- add nullable column
- add table not used yet
- add non-unique index concurrently/online where supported
- add comments

Medium risk:

- add NOT NULL with a safe default/backfill
- add unique constraint after deduplication
- change query path to a new index
- introduce soft delete or status lifecycle

High risk:

- drop/rename columns or tables
- change column type
- rewrite large table
- add foreign key validation to a large existing table
- add unique constraint without duplicate audit
- backfill large data in one transaction
- partition existing hot table
- move tenant boundaries

## Safe Expansion/Contraction

Prefer staged changes:

1. **Expand:** add new nullable column/table/index.
2. **Backfill:** fill in bounded batches.
3. **Dual-write or compatibility:** app writes old and new if needed.
4. **Read switch:** app reads new path.
5. **Validate:** row counts, checksums, constraints, sample queries.
6. **Contract:** remove old column/table only after confidence and rollback window.

## Backfills

Backfill plan should include:

- batch size
- ordering key
- retry behavior
- idempotency
- progress tracking
- lock/timeout limits
- rate limiting
- verification query
- rollback or stop condition

Avoid one giant `UPDATE` on hot production tables.

## Index Rollout

For each index, name:

- query pattern served
- expected selectivity
- write cost
- existing overlapping indexes
- online/concurrent creation support
- verification via `EXPLAIN` / query plan

Remove redundant indexes only after observing real usage or confirming overlap.

## Partitioning

Partition only when it solves a real problem:

- retention/drop old data
- query pruning on partition key
- maintenance isolation
- very large append-only table

Do not partition small tables. Partitioning adds planning, migration, uniqueness, and operational complexity.

Common partition keys:

- time range for events/orders/logs
- tenant hash only when tenant distribution and query routing justify it
- integer range for very large ordered IDs

## Rollback

Every migration plan needs one of:

- reversible rollback SQL
- feature-flag/application rollback path
- restore-from-backup plan
- explicit statement that rollback is not practical, plus mitigation

Irreversible operations must be called out directly.

## Review Checklist

- [ ] Existing data profiled for duplicates/nulls before constraints.
- [ ] DDL lock behavior understood for target engine.
- [ ] Large writes are batched and idempotent.
- [ ] New constraints have validation strategy.
- [ ] App deploy order is compatible with schema state.
- [ ] Rollback path is explicit.
- [ ] Verification queries are included.
- [ ] Migration does not expose or log PII.
- [ ] Indexes are tied to query patterns.
- [ ] Analytics changes define refresh/backfill behavior.
