---
name: miudb
description: Query, inspect, and manage saved database connections through the `miudb` CLI (miu-db). Use when asked to set up miudb, add or import connections, smoke-test them, run SQL, inspect a schema, draw an ERD, wire the MCP server into an agent host, or read the activity log, on SQLite, Postgres, MySQL, Snowflake, or BigQuery. Output is the `miudb.cli/v1` JSON envelope; parse it, don't grep prose.
---

# miudb

`miudb` keeps saved connections, secrets, SSH tunnels, adapters, query paging,
schema inspection, and ERDs in one local Go binary. Every command prints one
JSON envelope on stdout; diagnostics go to stderr.

For anything not covered here, ask the source of truth instead of guessing:

- `miudb <command> --help` for flags and defaults; `miudb commands` and
  `miudb describe <command>` for the machine-readable catalog.
- `https://db.miu.sh/<page>.md` for raw docs: `onboarding`, `install`, `usage`,
  `authentication`, `erd`, `mcp`, `activity`, `cli-contract`, `architecture`.
  Index: `https://db.miu.sh/llms.txt`.

## Set up

Run in order and stop at the first step that needs the user.

1. `miudb version` - if missing: `curl -fsSL https://db.miu.sh/install.sh | sh`
   (Homebrew installs upgrade with `brew upgrade miudb`). `miudb upgrade --check`
   reports a newer release; upgrade only if the user agrees.
2. `miudb connections list --basic` - the `ref` column (`group/name`, or bare
   `name` when unique) is what `--connection` takes. If the connection the user
   named is missing, stop and ask. Never substitute a similar one.
3. Add a connection only when asked. Credentials come from the user's env or a
   command they trust; never ask them to paste a password into chat.
4. `miudb connections test <ref>` for one, `miudb connections smoke` for all.

## Commands

| Goal | Command |
|---|---|
| Add SQLite | `miudb connections add --name app --db-type sqlite --path ./app.db` |
| Add Postgres/MySQL | `miudb connections add --name app --db-type postgresql --host localhost --port 5432 --database app --username app --password "$APP_DB_PASSWORD"` |
| Through a bastion | add `--tunnel --ssh-config-alias <alias>` |
| Provider settings | repeat `--option k=v` (Snowflake `warehouse`, `role`; BigQuery project is `--host`) |
| Import a shared file | `miudb connections import ./conns.json --dry-run`, then without `--dry-run` |
| Test one / all | `miudb connections test <ref>` / `miudb connections smoke --timeout 20s` |
| One statement | `miudb query run --connection <ref> --sql '<SQL>' --limit 100` |
| Next page | `miudb query fetch-page --cursor <page.next_cursor>` |
| Several statements (Snowflake, MySQL) | `miudb query script --connection <ref> --sql 'a; b'` (`--atomic` for a transaction) |
| Per-call role/warehouse | add `--session role=ANALYST` (provider-specific keys, not persisted) |
| Schema | `miudb schema tree --connection <ref>` |
| ERD (SQLite, Postgres, MySQL) | `miudb erd generate -c <ref>`; `miudb erd serve -c <ref>` to open it |
| Snowflake OAuth | `miudb auth login <ref>`, `miudb auth status <ref>` |
| Activity | `miudb activity --since 24h`, `--failed`, `--connection <ref>` |

Rules:

- `-c` exists only on `erd` commands. `query run`, `schema tree`, and the rest
  need `--connection` (`-c` fails with `unknown shorthand flag`).
- `--limit` (default 100) and `--timeout` (default 30s) are global flags.
- `query run` executes whatever SQL it gets. Run mutations only when the user
  asked for them; prefer read-only SQL.
- Single-quote SQL with backticks (BigQuery, MySQL). Snowflake reserves `rows`
  as an alias; use `row_cnt`.
- `query script` is rejected on SQLite, Postgres, and BigQuery
  (`query.script_unsupported`); run statements one at a time.
- New passwords go to the `keyring` store by default (`--secret-store keyring|file|inline|none`).
  Release binaries are built without cgo, so `keyring` is an encrypted file
  keyring under `~/.config/miu/db/keyring/`, not the macOS Keychain.
- Never print passwords, credential files, private keys, or service-account JSON.
  `connections list` shows `has_password: true`, never the value.

## Output contract

```json
{ "ok": true, "api_version": "miudb.cli/v1", "kind": "query.result", "command": "query run",
  "request_id": "req_...", "summary": { "connection": "app", "db_type": "sqlite" },
  "data": { "connection": "app", "result": {
    "columns": [ { "name": "id", "type": "INTEGER", "nullable": true } ],
    "rows": [ [1], [2] ], "truncated": true } },
  "page": { "limit": 2, "next_cursor": "..." }, "artifacts": [], "warnings": [] }
```

- Branch on `ok` first. On `ok:false` read `error.code`, `error.message`,
  `error.hint`, `error.retryable`; there is no `data`. Exception: a failed
  `query script` prints `kind: query.script_result` with `ok:false`, no `error`,
  and `data.results` plus `data.errors` for the statements that ran (exit 2).
- Rows are positional arrays matching `columns`. `truncated: true` plus
  `page.next_cursor` means more rows exist.
- Exit `0` success, `2` bad input or `connection.not_found`, `1` anything else.
  `connections smoke` exits 0 even when some connections fail: read
  `data.results[].ok` and `summary.failed`.
- Output is scrubbed: credential-named fields and password-bearing URLs are
  redacted. Query values are not masked; they are the user's data.

| Error or symptom | Do |
|---|---|
| `connection.not_found` | `miudb connections list --basic`, then ask the user. |
| `unknown shorthand flag: 'c'` | Use `--connection`. |
| `connection.refused`, `localhost ... refused` | The local database or tunnel is down. Say so; do not retry in a loop. |
| SSH or tunnel error | Check the `~/.ssh/config` alias, key path, and network. |
| Secret lookup timeout | Keyring or gopass needs the user's session. Ask them. |
| BigQuery `no credentials found` | `gcloud auth application-default login`, or set `bigquery_credentials_path`. |
| Snowflake `no access token` | `miudb auth login <ref>`. |
| `query.multi_statement_not_allowed` | Use `query script` (Snowflake, MySQL). |
| `query.output_too_large` (MCP) | Lower the limit or select fewer columns. |

## ERD polish

`erd generate` writes `index.html` (offline, interactive) and `schema.json`
(`--format html,json,dbml` adds DBML) to `--out-dir`, default
`$VD_VISUALS_PATH/<ref-slug>-erd`, else `<git-root>/.work/visuals/<ref-slug>-erd`,
else `.diagrams/<ref-slug>-erd`. Without a `meta.json` every table renders
ungrouped and uncolored, and the envelope warns.

1. `miudb erd meta --stub -c <ref> --out-dir <dir>` seeds `meta.json` with
   detected framework tables and empty `groups` and `descriptions`.
2. Read `<dir>/schema.json`. FK topology, table-name prefixes, and row counts are
   enough; migration file names help too.
3. Fill `groups` with 5-9 domains, each `{ "color": "#hex", "tables": [...] }`,
   leaving no table ungrouped, and one-line `descriptions` for hub tables. Keep
   the detected `framework_tables` and `audit_columns`.
4. `miudb erd generate -c <ref> --meta <dir>/meta.json`, or `erd serve` to view.

Viewer: zoom and pan, click a table to spotlight its FK chain, double-click for
the column drawer, search, domain filters, shortest FK path, schema lint
(Insights), DBML copy, and Share links that encode filters in the URL.

## MCP

For hosts that want tools instead of a shell:
`claude mcp add --transport stdio miudb -- miudb mcp serve --transport stdio`.
Tools: `connections_list`, `connection_describe`, `connection_test`,
`connections_smoke`, `schema_tree`, `query_run`, `query_script`,
`query_fetch_page`. `query_run` is read-only unless the server starts with
`--allow-mutate`; a mutating `query_script` also needs `allow_mutate=true` per
call. Restrict with repeated `--connection <ref>`. Hosts: `mcp.md`.

## Privacy

Saved connections are private. Never copy connection names, hosts, schemas, or
query results into commits, docs, or examples; use generic `users` / `products` /
`orders` names instead.
