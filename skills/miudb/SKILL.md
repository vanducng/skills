---
name: miudb
description: >
  Query, inspect, and manage saved database connections through the Go `miudb`
  CLI. Use when the user asks to run SQL, list schemas, add native
  connections, smoke-test connections, inspect tunnel-backed databases, or
  produce agent-readable JSON from SQLite, Postgres, MySQL, Snowflake, or
  BigQuery.
allowed-tools:
  - Bash
metadata:
  author: vanducng
  version: "0.2.1"
  binary: miudb
---

# miudb

Headless database CLI for agent-safe SQL work against saved database
connections. Prefer direct `miudb` commands for one-shot machine-readable
output and scripted checks. Use `miudb mcp serve` only when configuring an MCP
host, and use `miudb serve` only for Neovim/custom protocol clients.

Do not use `sqlit` for miudb tasks.

## When to use

- "Run this SQL on `<connection>`"
- "List schemas/tables/columns for `<connection>`"
- "Smoke-test my saved database connections"
- "Check a tunnel-backed connection"
- "Add a new database connection"
- Any task naming a connection that appears in `miudb connections list`

## Install/verify

```bash
brew install vanducng/tap/miudb
miudb version --output json
miudb commands --output json
```

If `miudb version` reports older than `v0.2.0-go.9` or the command catalog
lacks `mcp serve`, install the tagged Go binary or build from the local
checkout.

```bash
go install github.com/vanducng/miu-db/cmd/miudb@v0.2.0-go.9
cd /Users/vanducng/git/personal/miu-db
go build -buildvcs=false -o ./.miu-db/miudb ./cmd/miudb
```

## Default local config

`miudb` uses a native Go store by default:

```text
~/.config/miu/db/connections.json
~/.config/miu/db/credentials.json
```

Sensitive values are classified before persistence. New database and SSH
passwords are stored outside `connections.json` by default using the OS
Keychain/keyring service named `miudb`.

For migrated configs, `miudb` reads `credentials-export.json` from the same
directory when `credentials.json` is absent.

Only pass `--config-dir`, `--connections-file`, `--credentials-file`,
`--credentials-export`, `--secret-source`, `--keyring-service`, or
`--gopass-prefix` when the user asks for a non-default store.

By default, secret lookup can use file credentials, the `miudb` keyring
service, and gopass paths under the `miudb` prefix. Treat `--credentials-export`
as a deprecated alias for `--credentials-file`.

## Discover commands and connections

```bash
miudb commands --output json
miudb describe connections add --output json
miudb describe connections test --output json
miudb describe query run --output json
miudb describe connections smoke --output json
miudb describe mcp serve --output json
miudb connections list --output json
```

If the named connection is not listed, stop and ask the user. Do not
substitute a similar connection.

## Add connections

SQLite:

```bash
miudb connections add \
  --name local-app \
  --db-type sqlite \
  --path ./app.db \
  --output json
```

Postgres/MySQL style TCP connection:

```bash
miudb connections add \
  --name app-dev \
  --db-type postgresql \
  --host localhost \
  --port 5432 \
  --database app \
  --username app \
  --password "$APP_DB_PASSWORD" \
  --secret-store keyring \
  --output json
```

Tunnel-backed connection:

```bash
miudb connections add \
  --name app-prod \
  --db-type mysql \
  --host prod-rds.internal \
  --port 3306 \
  --database app \
  --username app \
  --password "$APP_DB_PASSWORD" \
  --tunnel \
  --ssh-config-alias bastion \
  --secret-store keyring \
  --output json
```

Provider options:

```bash
miudb connections add \
  --name warehouse \
  --db-type snowflake \
  --host account \
  --username USER \
  --option authenticator=snowflake_jwt \
  --option warehouse=DEV_WH \
  --extra-option sslmode=require \
  --output json
```

Secret stores for new connections:

- `keyring`: OS Keychain/keyring service named `miudb` by default.
- `file`: local `credentials.json` with mode `0600`.
- `inline`: leave the value in `connections.json`.
- `none`: discard the supplied secret and require another resolver later.

Rules:

- Prefer `--secret-store keyring` for user-entered credentials.
- Use `--password-command` only when the command is already trusted by the
  user; never invent a credential command.
- Use `--secret-store file` only for disposable/local test configs or when the
  user explicitly wants a file-backed credential.
- Never print passwords, credential files, private keys, or service account
  JSON.

## Test one connection

```bash
miudb connections test <CONN> \
  --timeout 12s \
  --output json
```

Use `connections test` when the user names one connection or asks whether one
connection is reachable. This opens the connection and may create an SSH
tunnel, but does not run user SQL.

## Smoke-test connections

```bash
miudb connections smoke \
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
miudb query run \
  --connection <CONN> \
  --sql '<SQL>' \
  --limit 100 \
  --output json
```

Rules:

- Keep `--limit` bounded unless the user explicitly asks for a large export.
- Prefer read-only SQL unless the user explicitly authorizes mutation.
- Use single quotes around SQL containing BigQuery/MySQL backticks.
- If SQL contains single-quoted literals and backticks, escape carefully; do
  not assume file input exists unless `miudb describe query run` says it does.

## Fetch paged results

If `query run` returns a cursor or truncation marker, continue with:

```bash
miudb query fetch-page \
  --cursor <CURSOR> \
  --output json
```

## Inspect schema

```bash
miudb schema tree \
  --connection <CONN> \
  --output json
```

Metadata SQL recipes also work through `query run`.

### BigQuery

```bash
miudb query run \
  --connection <conn> \
  --sql 'SELECT schema_name FROM INFORMATION_SCHEMA.SCHEMATA' \
  --output json
```

Use single quotes for BigQuery table references:

```bash
miudb query run \
  --connection <conn> \
  --sql 'SELECT * FROM `dataset`.`table` LIMIT 10' \
  --limit 10 \
  --output json
```

### MySQL

```bash
miudb query run --connection <conn> --sql 'SHOW DATABASES' --output json
miudb query run --connection <conn> --sql 'SHOW TABLES' --output json
miudb query run --connection <conn> --sql 'DESCRIBE `table_name`' --output json
```

### Postgres and Snowflake

```bash
miudb query run --connection <conn> --sql 'SELECT table_schema, table_name FROM information_schema.tables WHERE table_type = ''BASE TABLE''' --output json
miudb query run --connection <conn> --sql 'SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = ''table_name'' ORDER BY ordinal_position' --output json
```

### SQLite

```bash
miudb query run --connection <conn> --sql "SELECT name FROM sqlite_master WHERE type = 'table'" --output json
miudb query run --connection <conn> --sql "PRAGMA table_info('table_name')" --output json
```

## Stdio protocol

For Neovim or client integration, use the experimental stdio server:

```bash
miudb serve --protocol jsonrpc --output json
```

Use this only for client/protocol tasks. For normal agent work, call the direct
CLI commands above.

## MCP server

For MCP-native hosts such as Codex, Claude Code, Cursor, and VS Code, use:

```bash
miudb mcp serve --transport stdio
```

Useful flags:

- `--connection <name>`: repeat to restrict visible/callable connections.
- `--limit <n>`: default row limit for MCP query tools.
- `--max-limit <n>`: maximum accepted MCP query limit.
- `--max-bytes <n>`: maximum serialized bytes per tool/resource response.
- `--allow-mutate`: allow mutation SQL through MCP `query_run`; unsafe.

MCP tools exposed by the server:

- `connections_list`
- `connection_describe`
- `connection_test`
- `connections_smoke`
- `schema_tree`
- `query_run`
- `query_fetch_page`

MCP `query_run` is read-only by default and rejects mutation SQL unless
`--allow-mutate` is explicitly provided. Stdout is reserved for MCP frames;
startup errors and diagnostics go to stderr.

## Output contract

- stdout is JSON.
- stderr is diagnostics only.
- `ok: false` is a structured failure, not necessarily a shell failure.
- Command descriptions are available via `miudb describe <command>`.
- Connection output redacts secrets; do not inspect credential stores unless
  the user explicitly asks.
- The command catalog currently includes `connections test`, `mcp serve`, and
  the native `serve` protocol; choose the narrowest command that matches the
  user's use case.

## Failure modes

- **connection not found** -> run `connections list`, then ask the user.
- **localhost refused** -> local database/tunnel is not running.
- **secret timeout** -> keyring/gopass lookup may need user session access.
- **SSH/tunnel error** -> check `~/.ssh/config`, key path, username, and network.
- **BigQuery auth error** -> verify `options.bigquery_credentials_path`.
- **Snowflake JWT error** -> verify `options.private_key_file`.
- **query too large** -> lower `--limit` or ask before exporting.

## Anti-patterns

- Do not run Python `miu-db` TUI for agent tasks.
- Do not use `sqlit`.
- Do not guess connection names.
- Do not print credentials, private keys, or service account JSON.
- Do not run destructive SQL without explicit user approval.
- Do not omit `--output json` for agent-consumed results.
- Do not use unbounded queries in conversation context.
