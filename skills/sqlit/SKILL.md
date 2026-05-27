---
name: sqlit
description: >
  Query data from any saved database connection (BigQuery, Postgres, MySQL,
  MSSQL, SQLite, Snowflake, DuckDB, etc.) via the `sqlit` CLI. Use when the
  user asks to inspect tables, run SQL, list schemas, count rows, export data,
  or references a saved sqlit connection by name.
allowed-tools:
  - Bash
metadata:
  author: vanducng
  version: "0.2.0"
  binary: sqlit
---

# sqlit

Scriptable CLI for ad-hoc SQL against any saved connection.

## When to use

- "Run this SQL on `<connection>`" / "show me 10 rows of X" / "count rows in Y"
- "What tables / columns are in Z?"
- "Export Z as JSON/CSV"
- Any task naming a connection that appears in `sqlit connections list`

**Never run bare `sqlit`** — it launches a TUI and hijacks the terminal.

## Discover connections

```bash
sqlit connections list                # name | type | host:port/db | auth
sqlit connections list --format json  # full structured (host, port, default db, tunnel, options)
```

If the named connection isn't listed, **stop and ask** — don't substitute.

## Run a query

```bash
sqlit query -c <CONN> -q '<SQL>' --format <table|csv|json> [-d <db>] [--limit N]
```

| Flag | Purpose | Default |
|------|---------|---------|
| `-c, --connection` | Saved connection name (required) | — |
| `-q, --query` / `-f, --file` | Inline SQL / SQL file path | — |
| `-d, --database` | Override connection's default database | — |
| `-o, --format` | `table` \| `csv` \| `json` | `table` |
| `-l, --limit` | Max rows (`0` = unlimited) | `1000` |

## ⚠ Shell-quoting (CRITICAL)

Wrap SQL in **single quotes** when it contains backticks (BigQuery, MySQL).
Backticks inside double quotes trigger shell command substitution and the
query never reaches sqlit.

```bash
# ✅
sqlit query -c bq -q 'SELECT * FROM `dataset`.`table` LIMIT 10' --format json
# ❌ shell tries to execute `dataset` and `table`
sqlit query -c bq -q "SELECT * FROM `dataset`.`table` LIMIT 10"
```

If your SQL contains a single-quoted literal too, use `-f file.sql`.

## Metadata recipes

### BigQuery
```bash
# datasets
sqlit query -c <conn> -q 'SELECT schema_name FROM INFORMATION_SCHEMA.SCHEMATA' --format table
# tables in dataset (+ row counts)
sqlit query -c <conn> -q 'SELECT table_id AS table_name, row_count, size_bytes
  FROM `<dataset>`.__TABLES__ ORDER BY size_bytes DESC' --format table
# columns
sqlit query -c <conn> -q 'SELECT column_name, data_type, is_nullable
  FROM `<dataset>`.INFORMATION_SCHEMA.COLUMNS
  WHERE table_name = "<table>" ORDER BY ordinal_position' --format table
```

### MySQL
MySQL `schema` = `database`. If the connection has no default DB (check via
`--format json` → `endpoint.database`), pass `-d <db>` or fully-qualify
`` `db`.`table` ``.
```bash
sqlit query -c <conn> -q "SHOW DATABASES" --format table
sqlit query -c <conn> -d <db> -q "SHOW TABLES" --format table
sqlit query -c <conn> -d <db> -q "DESCRIBE <table>" --format table
# Count/find tables matching a pattern in the connection's default db
sqlit query -c <conn> -q "SELECT COUNT(*) FROM information_schema.tables
  WHERE table_schema = DATABASE() AND table_name LIKE '%<pattern>%'" --format table
# Same search across ALL accessible schemas (useful when default db is empty)
sqlit query -c <conn> -q "SELECT table_schema, COUNT(*) AS n FROM information_schema.tables
  WHERE table_name LIKE '%<pattern>%' GROUP BY table_schema" --format table
sqlit query -c <conn> -d <db> -q "SHOW CREATE TABLE <table>" --format table
```

### Postgres / MSSQL / Snowflake
```bash
sqlit query -c <conn> -q "SELECT table_schema, table_name
  FROM information_schema.tables WHERE table_type='BASE TABLE'" --format table
sqlit query -c <conn> -q "SELECT column_name, data_type, is_nullable
  FROM information_schema.columns WHERE table_name='<table>'
  ORDER BY ordinal_position" --format table
```

### SQLite / DuckDB
```bash
sqlit query -c <conn> -q "SELECT name FROM sqlite_master WHERE type='table'" --format table
sqlit query -c <conn> -q "PRAGMA table_info('<table>')" --format table
```

## Scripting

```bash
# pipe JSON to jq
sqlit query -c <conn> -q 'SELECT id, name FROM users LIMIT 5' --format json | jq -r '.[].name'
# CSV to file (strip the leading "(N row(s) returned)" line)
sqlit query -c <conn> -q 'SELECT * FROM events' --format csv | tail -n +3 > events.csv
# multi-statement script
sqlit query -c <conn> -f migration.sql --format table
```

## Failure modes

- **"Connection 'X' not found"** → `sqlit connections list`, ask user.
- **Empty output, fast exit, no error** → shell ate the backticks. Use single quotes.
- **MySQL `(1046, "No database selected")`** → add `-d <db>` or qualify with `` `db`.`table` ``.
- **`(0 row(s) returned)` on a populated table** → check `-d` override; on BigQuery, verify connection's project.

## Anti-patterns

- ❌ Bare `sqlit` (launches TUI, blocks).
- ❌ Guessing connection names — list first.
- ❌ Backticks inside `--query "..."` — single quotes only.
- ❌ `--limit 0` when piping into the conversation — can blow context.
- ❌ Destructive DML (`DROP`, `TRUNCATE`, unscoped `DELETE`) without explicit user OK.
