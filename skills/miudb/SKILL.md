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
brew install vanducng/tap/miudb   # first install
miudb upgrade                      # self-update to the latest release
miudb version --output json        # v0.8.0 or newer
miudb commands --output json
```

If the catalog lacks a command you need, run `miudb upgrade`, or build from the
local checkout:

```bash
cd <your-miu-db-checkout>          # your local clone of the miu-db source repo
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
miudb connections list --basic --output json   # scannable: ref/name/group/db_type/host
```

Connections are addressed by **`group/name`** (e.g. `cnb/cdljn-prod`); a bare
`name` works when it is unique across groups. The `ref` column from `--basic` is
exactly what to pass to `--connection`/`-c`. If the named connection is not
listed, stop and ask the user. Do not substitute a similar connection.

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

- `keyring`: OS Keychain/keyring service named `miudb` on CGO-enabled builds.
  Release binaries (`brew install`) are CGO-disabled and fall back to an
  encrypted file keyring at `~/.config/miu/db/keyring/<connection>:<kind>`
  (JWE / PBES2-HS256+A128KW, one file per secret) - NOT the OS Keychain, so
  `security find-generic-password -s miudb ...` finds nothing there.
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

Verify where a secret landed (cheapest first, never reveals the value):

- `miudb connections list --output json` -> `has_password: true`, and the
  connection's `secrets[]` shows `provider: keyring` + `ref`.
- `ls ~/.config/miu/db/keyring/` -> `<connection>:db` file on release builds
  (contents are JWE-encrypted; the raw password is not in the file).
- `miudb connections test <CONN>` -> `ok: true` proves it resolves end-to-end.

## Test one connection

```bash
miudb connections test <CONN> \
  --timeout 12s \
  --output json
```

Use `connections test` when the user names one connection or asks whether one
connection is reachable. This opens the connection and may create an SSH
tunnel, but does not run user SQL.

## OAuth login for Snowflake and BigQuery

Acquire and store an OAuth token for a connection supporting OAuth (Snowflake, BigQuery):

```bash
miudb auth login <CONN> --output json
miudb auth status <CONN> --output json
miudb auth logout <CONN> --output json
```

Tokens are stored in the keyring service. On CGO-disabled builds (release binaries), fallback to file-based credential storage.

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

## Run multi-statement scripts

For Snowflake and MySQL, execute multiple statements in one script; each statement produces one result set:

```bash
miudb query script \
  --connection <CONN> \
  --sql 'SELECT 1; SELECT 2' \
  --output json
```

Postgres rejects multi-command scripts; run statements individually with `query run`.

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

## Generate an ERD (interactive diagram)

`miudb erd` turns a connection into a self-contained, offline interactive ER diagram (Cytoscape) plus a DBML export. Tier-1: MySQL, Postgres. Snowflake/BigQuery/DuckDB return a clean "unsupported" error.

```bash
# interactive offline index.html + schema.json + schema.dbml (default --format html)
miudb erd generate -c <group/name> --out-dir .diagrams/<name>-erd --output json
# serve it; auto-opens the browser for an interactive terminal (--no-open to suppress);
# --from <dir|schema.json> renders an existing export with no DB
miudb erd serve -c <group/name> --output json
```

Short flags on every `erd` command: `-c`/`--connection`, `-s`/`--schema`,
`-m`/`--meta`, `-f`/`--format`, `-p`/`--port`. A connection with no default
database (e.g. a server-level DSN) errors with a clear "pass --schema" hint.

Two layers:
- **Deterministic (miudb):** introspect -> `schema.json` (the render source-of-truth) -> DBML + HTML. No LLM.
- **Agentic (you):** author `meta.json` to add **colored domain groups** + table **descriptions**. Without it, tables render as Framework/Other with no colors (`erd generate` emits a warning saying so).

### Agentic polish recipe (how to make a good diagram)

1. Scaffold: `miudb erd meta --stub --connection <CONN> --out-dir <dir>` - auto-detects framework tables (Laravel/Rails/Django/Prisma) and seeds blank `groups`/`descriptions`. The envelope `data.next_step` reminds you what to fill.
2. Read `<dir>/schema.json` (the IR: `tables[] -> {pk, columns, fks, indexes, rows}`). Cheap, high-signal inputs: FK topology (which tables connect), table-name prefixes, FK hub degree, and row counts. Migration *filenames* (`ls database/migrations` / `db/migrate`) are a strong signal too - you do NOT need to read their contents.
3. Edit `meta.json`:
   - **`groups`**: cluster every non-framework table into 5-9 domains. Densely-FK-connected tables belong together; split by name prefix and responsibility (catalog vs apply vs analytics vs CMS vs auth). Each group = `{ "color": "#hex", "tables": [...] }`. Put core domains in saturated colors, infra/marketing in muted. Palette: `#2563eb` blue, `#16a34a` green, `#9333ea` purple, `#d97706` amber, `#dc2626` red, `#0d9488` teal, `#db2777` pink, `#475569` slate.
   - **`descriptions`**: 1 line per important table (hubs + biggest by rows), inferred from name + columns + FK role (self-ref FK -> "conditional/nested"; double-FK + unique pair -> "junction"; `*_id` hub -> "owns/links X").
   - leave **`framework_tables`** / **`audit_columns`** as detected.
4. Regenerate: `miudb erd generate --connection <CONN> --meta <dir>/meta.json` (or `erd serve`). Iterate.

Single-pass works: stub -> fill -> generate. Aim to leave 0 tables ungrouped (the renderer buckets ungrouped non-framework tables as "Other").

**Worked example (a ~100-table SaaS schema):** the stub detects the framework tables; the FK hubs (a high-degree `users`/`accounts` table, a few central domain tables) plus name prefixes map cleanly to ~6-8 domains (e.g. Catalog, Orders, Billing, Analytics, Content, Auth) - grouping every non-framework table with colors + hub descriptions in one pass. Use generic examples; never paste real connection/schema names into the diagram metadata you commit.

**Viewer (the rendered `index.html`):** click a table to spotlight its FK chain; **Focus** (View options) hides everything except the selected table + its relations - best for reading a dense schema; **DBML** (toolbar) shows the dbdiagram.io/dbdocs source with Copy; Domain Groups has **all**/**clear**; the header shows live visible/total counts; hover truncated names for the full value. Initial zoom is clamped so columns stay legible - the **Fit** button zooms to the whole graph. State (filters/selection) is encoded in the share URL.

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

## Query activity log

Each session captures activity events in a per-session JSONL log. Query and prune it with:

```bash
miudb activity --connection <CONN> --since 24h --output json
miudb activity --failed --since 7d --output json
miudb activity prune --older-than 30d --output json
```

Use `--since` to filter by relative duration (e.g. `24h`, `7d`); omit to read all captured events. Use `--failed` to show only failed queries.

## Output contract

- stdout is JSON.
- stderr is diagnostics only.
- `ok: false` is a structured failure, not necessarily a shell failure.
- Command descriptions are available via `miudb describe <command>`.
- Output is secret-hardened: credential-named values, password-bearing URLs, and
  `key=secret` assignments are redacted before stdout (`connections list` shows
  `has_password: true`, never the value). Query-result *values* are NOT masked  - 
  they're the user's data. Do not inspect credential stores unless asked.
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
