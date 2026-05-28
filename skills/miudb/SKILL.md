---
name: miudb
description: >
  Query and inspect saved miu-db database connections through the Go `miudb`
  CLI. Use when the user asks to check migrated Python miu-db connections, run
  SQL, list schemas, smoke-test connections, inspect tunnels, or produce
  agent-readable JSON from SQLite, Postgres, MySQL, Snowflake, or BigQuery.
allowed-tools:
  - Bash
metadata:
  author: vanducng
  version: "0.1.0"
  binary: miudb
---

# miudb

Headless database CLI for agent-safe SQL work against saved miu-db
connections. Prefer this over the Python `miu-db` TUI when the task needs
machine-readable output, scripted checks, or Neovim/agent integration.

## When to use

- "Check current connections migrated from Python miu-db"
- "Run this SQL on `<connection>`"
- "List schemas/tables/columns for `<connection>`"
- "Smoke-test my saved database connections"
- "Check a tunnel-backed connection"
- Any task naming a connection that appears in `miudb connections list`

Use `sqlit` instead only when the user explicitly asks for `sqlit` or needs a
database type not yet covered by `miudb`.

## Install/verify

```bash
brew install vanducng/tap/miudb
miudb version --output json
```

Alternative:

```bash
go install github.com/vanducng/miu-db/cmd/miudb@v0.2.0-go.4
```

## Default local config

The current Go preview can read the existing Python miu-db config and exported
credentials:

```bash
MIUDB_CONFIG_DIR=/Users/vanducng/.config/miu/db
MIUDB_CREDENTIALS=/Users/vanducng/.config/miu/db/credentials-export.json
```

Most commands should include both flags explicitly:

```bash
miudb \
  --config-dir "$MIUDB_CONFIG_DIR" \
  --credentials-export "$MIUDB_CREDENTIALS" \
  <command> \
  --output json
```

## Discover commands and connections

```bash
miudb commands --output json
miudb describe query run --output json
miudb describe connections smoke --output json

miudb \
  --config-dir "$MIUDB_CONFIG_DIR" \
  --credentials-export "$MIUDB_CREDENTIALS" \
  connections list \
  --output json
```

If the named connection is not listed, stop and ask the user. Do not
substitute a similar connection.

## Smoke-test migrated connections

Use this to verify which saved Python miu-db connections currently work from
the Go CLI:

```bash
miudb \
  --config-dir "$MIUDB_CONFIG_DIR" \
  --credentials-export "$MIUDB_CREDENTIALS" \
  connections smoke \
  --timeout 12s \
  --concurrency 4 \
  --output json
```

Interpretation:

- Top-level `ok: false` can be expected when local-only databases are stopped.
- Check `.data.results[]` for per-connection pass/fail.
- Local failures like `localhost:3307 refused` usually mean a local service or
  tunnel is not running.
- Tunnel failures can mean SSH alias/key/remote network issues.

Summarize results without printing passwords or secret file contents.

## Run a query

```bash
miudb \
  --config-dir "$MIUDB_CONFIG_DIR" \
  --credentials-export "$MIUDB_CREDENTIALS" \
  query run \
  --connection <CONN> \
  --sql '<SQL>' \
  --limit 100 \
  --output json
```

Rules:

- Keep `--limit` bounded unless the user explicitly asks for a large export.
- Prefer read-only SQL unless the user explicitly authorizes mutation.
- Use single quotes around SQL containing BigQuery/MySQL backticks.
- If SQL contains single-quoted literals and backticks, write it to a temp
  `.sql` file only if the CLI supports file input in the current version;
  otherwise escape carefully.

## Fetch paged results

If `query run` returns a cursor or truncation marker, continue with:

```bash
miudb \
  --config-dir "$MIUDB_CONFIG_DIR" \
  --credentials-export "$MIUDB_CREDENTIALS" \
  query fetch-page \
  --cursor <CURSOR> \
  --output json
```

## Inspect schema

```bash
miudb \
  --config-dir "$MIUDB_CONFIG_DIR" \
  --credentials-export "$MIUDB_CREDENTIALS" \
  schema tree \
  --connection <CONN> \
  --output json
```

Metadata SQL recipes also work through `query run`:

### BigQuery

```bash
miudb \
  --config-dir "$MIUDB_CONFIG_DIR" \
  --credentials-export "$MIUDB_CREDENTIALS" \
  query run \
  --connection <conn> \
  --sql 'SELECT schema_name FROM INFORMATION_SCHEMA.SCHEMATA' \
  --output json
```

Use single quotes for BigQuery table references:

```bash
miudb \
  --config-dir "$MIUDB_CONFIG_DIR" \
  --credentials-export "$MIUDB_CREDENTIALS" \
  query run \
  --connection <conn> \
  --sql 'SELECT * FROM `dataset`.`table` LIMIT 10' \
  --limit 10 \
  --output json
```

### MySQL

```bash
miudb --config-dir "$MIUDB_CONFIG_DIR" --credentials-export "$MIUDB_CREDENTIALS" query run --connection <conn> --sql 'SHOW DATABASES' --output json
miudb --config-dir "$MIUDB_CONFIG_DIR" --credentials-export "$MIUDB_CREDENTIALS" query run --connection <conn> --sql 'SHOW TABLES' --output json
miudb --config-dir "$MIUDB_CONFIG_DIR" --credentials-export "$MIUDB_CREDENTIALS" query run --connection <conn> --sql 'DESCRIBE `table_name`' --output json
```

### Postgres and Snowflake

```bash
miudb --config-dir "$MIUDB_CONFIG_DIR" --credentials-export "$MIUDB_CREDENTIALS" query run --connection <conn> --sql 'SELECT table_schema, table_name FROM information_schema.tables WHERE table_type = ''BASE TABLE''' --output json
miudb --config-dir "$MIUDB_CONFIG_DIR" --credentials-export "$MIUDB_CREDENTIALS" query run --connection <conn> --sql 'SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = ''table_name'' ORDER BY ordinal_position' --output json
```

### SQLite

```bash
miudb --config-dir "$MIUDB_CONFIG_DIR" --credentials-export "$MIUDB_CREDENTIALS" query run --connection <conn> --sql "SELECT name FROM sqlite_master WHERE type = 'table'" --output json
miudb --config-dir "$MIUDB_CONFIG_DIR" --credentials-export "$MIUDB_CREDENTIALS" query run --connection <conn> --sql "PRAGMA table_info('table_name')" --output json
```

## Stdio protocol

For Neovim or client integration, the preview exposes experimental stdio
serving:

```bash
miudb \
  --config-dir "$MIUDB_CONFIG_DIR" \
  --credentials-export "$MIUDB_CREDENTIALS" \
  serve \
  --output json
```

Use this only for client/protocol tasks. For normal agent work, call the direct
CLI commands above.

## Output contract

- stdout is JSON.
- stderr is diagnostics only.
- `ok: false` is a structured failure, not necessarily a shell failure.
- Command descriptions are available via `miudb describe <command>`.
- Connection output redacts secrets; do not inspect credential files unless the
  user explicitly asks.

## Failure modes

- **connection not found** -> run `connections list`, then ask the user.
- **localhost refused** -> local database/tunnel is not running.
- **SSH/tunnel error** -> check `~/.ssh/config`, key path, username, and network.
- **BigQuery auth error** -> verify `options.bigquery_credentials_path`.
- **Snowflake JWT error** -> verify `options.private_key_file`.
- **query too large** -> lower `--limit` or ask before exporting.

## Anti-patterns

- Do not run Python `miu-db` TUI for agent tasks.
- Do not guess connection names.
- Do not print credentials, private keys, or service account JSON.
- Do not run destructive SQL without explicit user approval.
- Do not omit `--output json` for agent-consumed results.
- Do not use unbounded queries in conversation context.
