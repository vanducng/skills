---
name: dbdesign
description: "Design and review production database schemas, data models, ERDs, migration plans, and storage patterns. Use for OLTP schema design, OLAP/star-schema modeling, fact/dimension tables, indexes, constraints, partitioning, multi-tenant data models, CSV/JSON-to-table design, schema review, migration risk review, and database design documents across PostgreSQL, MySQL, SQLite/D1, BigQuery, and MongoDB. Does not execute DDL by default."
license: MIT
metadata:
  author: vanducng
  version: "1.0.0"
---

# DB Design

Design database schemas from requirements, existing data, and query patterns. This skill covers modeling decisions and review quality; use `vd:sqlit` or `vd:miudb` to inspect live databases, `vd:diagram` for ERDs, and `vd:cnpg` for CloudNativePG provisioning.

## Reference Router

Read only what the task needs:

- `references/workflow.md`: intake, schema inspection, output format, and approval gates.
- `references/transactional.md`: OLTP entities, relationships, constraints, indexes, soft delete, tenancy, and audit columns.
- `references/analytics.md`: OLAP/star schema, facts, dimensions, SCD, summaries, and incremental refresh design.
- `references/engine-notes.md`: PostgreSQL, MySQL/MariaDB, SQLite/D1, BigQuery, and MongoDB-specific design notes.
- `references/migration-review.md`: migration safety, rollout sequencing, backfills, rollback, partitioning, and risk checks.
- `references/design-doc.md`: compact database design document template.

## Workflow

1. Identify the database engine and context: new schema, extension of existing schema, analytics model, data import, migration review, or design doc.
2. Inspect existing schema before proposing changes when a database or repo is available. Use `vd:miudb`, `vd:sqlit`, migrations, ORM models, dbt models, or schema files as source of truth.
3. Capture requirements before DDL:
   - entities and relationships
   - main reads/writes/reports
   - expected scale and growth
   - tenancy, permissions, privacy, retention, and audit needs
   - consistency requirements and transaction boundaries
4. Load the relevant references:
   - OLTP or CRUD app -> `transactional.md`
   - analytics/reporting -> `analytics.md`
   - engine-specific DDL -> `engine-notes.md`
   - migration/change review -> `migration-review.md`
   - design document -> `design-doc.md`
5. Propose the model first, then DDL. Do not execute DDL unless the user explicitly asks and the environment is safe.
6. Explain tradeoffs: normalization vs denormalization, surrogate vs natural keys, JSON vs columns, partitioning, index cost, retention, and operational risk.
7. Finish with a checklist and open questions. If assumptions remain, label them instead of pretending certainty.

## Design Defaults

- Model the business language first; table names should reflect domain concepts, not UI screens.
- Prefer boring relational constraints for integrity: primary keys, foreign keys, unique constraints, checks, and NOT NULL.
- Index from actual query patterns, not from every column.
- Add comments/descriptions for tables and important columns when the engine supports them.
- Use exact numeric types for money and measured quantities.
- Store timestamps consistently; prefer timezone-aware types when the engine supports them.
- Plan retention and deletion behavior up front, especially for PII and audit logs.
- Separate operational tables from analytics/reporting models when workloads diverge.
- Treat schema migrations as production changes: reversible when possible, staged when large, and tested with realistic data.

## Validate DBML with dbdocs

When the design uses DBML (you write or edit a `.dbml` file):

- **Gate:** after writing/editing the file, run `dbdocs validate <path/to/schema.dbml>`. A clean parse (`Parse succeeded without errors.`) is required before the design is done. `dbdocs` is the validator (e.g. `dbdocs/0.14.0`).
- **No apostrophes inside single-quoted notes.** `note: 'the row''s id'` is not valid DBML and fails with `Expect a comma ','` — reword to drop the apostrophe ("the id on this row"); triple-quoted `'''...'''` notes are fine.
- **Avoid reserved/ambiguous words as column names** (e.g. `index`, `now`) — they can break the parser; document the column in the table `Note` instead, or quote/rename it.

## Hard Rules

- Do not invent a schema when existing tables might already cover the domain. Inspect first or ask for the schema.
- Do not execute DDL by default. Present DDL and migration steps for approval.
- Do not generate irreversible destructive migrations without an explicit warning and safer alternatives.
- Do not design indexes without naming the query pattern each index serves.
- Do not put secrets, credentials, or real PII in design docs, examples, PR bodies, or committed files.
- Do not preserve old source skill names or Claude-specific paths in new work.
