# Database Design Workflow

Use this reference for intake, inspection, output shape, and approval gates.

## Intake

Before designing, establish:

- **Engine:** PostgreSQL, MySQL/MariaDB, SQLite/D1, BigQuery, MongoDB, or unknown.
- **Workload:** OLTP, OLAP, ETL/control, event log, search, cache, or mixed.
- **Change type:** new schema, extend existing, review draft SQL, design from CSV/JSON, migration plan, or design doc.
- **Existing sources:** live database, migrations, ORM models, dbt models, SQL files, spreadsheets, API contracts, product requirements.
- **Scale:** row counts now/later, write rate, read rate, retention, hot paths, and batch sizes.
- **Business rules:** uniqueness, lifecycle states, tenancy, permissions, privacy, auditability, and deletion policy.

If any of these are missing and materially affect the design, ask a targeted question before writing DDL.

## Inspect Existing Schema

Use available sources in this order:

1. Live schema via `vd:miudb` or `vd:sqlit`.
2. Migration files and schema dumps.
3. ORM models and validation schemas.
4. dbt/source/semantic models for analytics.
5. Sample data files only when schema sources do not exist.

Useful inspection targets:

- table names, columns, types, nullability, defaults
- primary keys, unique constraints, foreign keys
- indexes and partial indexes
- comments/descriptions
- row counts and high-cardinality tables
- migration history and naming conventions
- soft-delete and audit patterns
- tenancy boundaries

Never duplicate an existing table just because the name differs. Map the requirement onto the current domain model first.

## Requirement Questions

Ask only what blocks a useful design:

- "What are the main entities and lifecycle states?"
- "Which queries or reports must be fast?"
- "What is the row granularity?"
- "Is this single-tenant, tenant-scoped, or cross-tenant?"
- "What data is sensitive or subject to retention/deletion rules?"
- "Which writes need to be transactional?"
- "What is the expected row count and growth?"
- "Is historical state required or can current state overwrite old values?"

## Output Format

For schema design:

1. **Summary:** new tables, changed tables, removed/deprecated tables.
2. **ERD or relationship list:** cardinality and delete behavior.
3. **DDL:** complete enough to review, including constraints, indexes, and comments.
4. **Query patterns:** map each important query to its supporting indexes/partitioning.
5. **Migration plan:** sequence, backfill, validation, rollback.
6. **Tradeoffs:** alternatives rejected and why.
7. **Checklist:** remaining risks and open questions.

For review:

```text
file:line - Severity - Issue. Why it matters. Suggested fix.
```

Severity:

- `Blocker`: data loss, invalid integrity, unsafe migration, unbounded production lock, or security/privacy leak.
- `High`: missing key constraint/index, bad tenancy boundary, scale-breaking table design.
- `Medium`: ambiguous naming, weak comments, inefficient but tolerable access pattern.
- `Low`: polish and maintainability.

## Approval Gate

DDL is a proposal until the user explicitly asks to execute it. If execution is requested:

- confirm environment and connection
- confirm backup/rollback path
- prefer transaction or dry run where supported
- run the smallest verification query after applying
- never run destructive production DDL without explicit confirmation
