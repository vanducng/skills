# Transactional Schema Design

Use this reference for OLTP schemas that back product workflows, CRUD apps, admin systems, and APIs.

## Contents

- Modeling
- Keys
- Constraints
- Audit And Lifecycle
- Multi-Tenancy
- Indexing
- Column Types
- OLTP Checklist

## Modeling

- One table per durable entity or relationship.
- Use junction tables for many-to-many relationships.
- Keep lifecycle state explicit with `status`, timestamps, and domain events when needed.
- Prefer 3NF for operational data, then denormalize only for proven read paths.
- Store immutable facts that matter historically, such as order item price at purchase time.
- Avoid modeling UI tabs/screens as tables unless they are real business entities.

## Keys

- Use a surrogate primary key for most entities (`id`).
- Keep business identifiers as unique constraints (`order_number`, `sku`, `email`) rather than primary keys unless they are stable and compact.
- Foreign key columns use `<entity>_id` and match the referenced type.
- Composite primary keys are useful for pure join tables, but be careful when the table later grows its own lifecycle.

## Constraints

Prefer database-enforced integrity:

- `NOT NULL` for required fields.
- `UNIQUE` for business uniqueness.
- `CHECK` for bounded numeric ranges and small state sets.
- `FOREIGN KEY` with deliberate `ON DELETE` behavior.
- Exclusion constraints or range checks for no-overlap rules where the engine supports them.

Delete behavior:

- `RESTRICT` for parent rows that must not disappear while children exist.
- `CASCADE` for owned children that have no independent meaning.
- `SET NULL` only when orphaned child rows still make sense.

## Audit And Lifecycle

Common columns:

- `created_at`
- `updated_at`
- `deleted_at` when soft delete is required
- `created_by` / `updated_by` when auditability matters
- `version` or `lock_version` for optimistic concurrency when needed

Soft delete:

- Use `deleted_at` rather than `is_deleted` when timing matters.
- Add partial/filtered indexes for active rows where supported.
- Ensure uniqueness rules account for deleted rows.
- Decide whether foreign keys can point to soft-deleted rows.

## Multi-Tenancy

Choose the tenancy model explicitly:

- shared tables with `tenant_id`
- schema per tenant
- database per tenant

For shared tables:

- include `tenant_id` in tenant-owned tables
- include tenant in unique constraints where uniqueness is tenant-scoped
- include tenant in common composite indexes
- enforce tenant boundaries in queries, policies, or row-level security
- avoid globally unique business keys unless the business requires them

## Indexing

Every index needs a named query pattern.

Common indexes:

- primary key
- unique business key
- each foreign key used in joins
- status/time indexes for queues and dashboards
- composite indexes matching `WHERE` equality columns then range/sort columns

Avoid:

- indexing every column
- duplicate indexes where a composite prefix already covers the query
- indexing low-cardinality booleans alone
- creating write-heavy indexes for rare admin queries

Composite index rule of thumb:

```sql
-- Query:
-- WHERE tenant_id = ? AND status = ? ORDER BY created_at DESC
CREATE INDEX idx_orders_tenant_status_created
ON orders (tenant_id, status, created_at DESC);
```

## Column Types

- Money: exact decimal/numeric, not float.
- Quantities: integer or exact decimal depending on fractional units.
- Timestamps: timezone-aware if supported.
- JSON: use for flexible metadata, not for fields that need constraints, joins, or frequent filters.
- Status: enum or checked string depending on migration needs.
- Text: bounded `varchar` only when the bound has domain meaning or index implications.

## OLTP Checklist

- [ ] Existing schema checked for overlap.
- [ ] Each table has one clear purpose.
- [ ] Primary keys and business unique constraints are defined.
- [ ] Foreign keys have indexes and deliberate delete behavior.
- [ ] Common query patterns map to indexes.
- [ ] Audit/lifecycle fields match repo conventions.
- [ ] Tenant boundary is explicit if applicable.
- [ ] Sensitive data, retention, and deletion behavior are documented.
- [ ] DDL includes comments/descriptions where supported.
