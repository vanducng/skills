---
name: smartsheet
description: Operate the `smartsheet` CLI for bounded sheet discovery and reads, explicitly authorized bulk row additions or updates, structured JSON automation, and verified write workflows. Use when the user says "smartsheet", asks to list sheets, read or add/update rows, or script Smartsheet through its JSON contract.
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
---

# Smartsheet

Use `smartsheet` as the canonical binary. Treat generated help and structured responses as the runtime contract.

## Start safely

1. Confirm the installed command and version:

   ```bash
   command -v smartsheet
   smartsheet --version
   ```

2. Discover the exact command before acting:

   ```bash
   smartsheet --help
   smartsheet sheets get --help
   smartsheet rows add --help
   smartsheet rows update --help
   ```

3. Use the caller-provided `SMARTSHEET_API_TOKEN` environment variable without printing its value. The CLI does not store credentials or load `.env` automatically.

## Use the JSON contract

- Parse stdout only after a successful exit.
- Parse failure stderr as `{ "ok": false, "error": { ... } }`.
- Branch on `error.code` and retry only when `error.retryable` is `true`.
- Follow `error.next_steps` in order.
- Treat `--help` and `--version` as human-readable output.

## Read with bounds

Start with the smallest useful page and capture exact IDs before retrieving more data:

```bash
smartsheet sheets list --page 1 --page-size 25
smartsheet sheets get 1234567890123456 --page 1 --page-size 100
```

Use `--row-ids` and `--column-ids` when IDs are known. Continue to another page only when the current provider response proves it is needed. Do not build hidden auto-pagination loops.

## Change rows

Do not add or update live rows unless the user explicitly authorizes the target sheet and operation.

1. Read the current target rows and columns.
2. Read the exact write command help.
3. Put the smallest requested change in a reviewed JSON file.
4. Submit one batch containing 1 to 500 rows.
5. Capture the returned row IDs.
6. Read those IDs back and verify the requested cells.

```bash
smartsheet rows add 1234567890123456 --input @rows-to-add.json
smartsheet rows update 1234567890123456 --input @rows-to-update.json
smartsheet sheets get 1234567890123456 \
  --page-size 25 \
  --row-ids 1111111111111111 \
  --column-ids 3333333333333333
```

The CLI does not expose delete or dry-run commands. Do not invent them. Never retry an unconfirmed write until a read proves whether Smartsheet committed it.

## Handle failures

Report the command category, safe error code, message, retryability, and ordered next steps. Never include tokens, `.env` contents, or full provider payloads. For command usage failures, run the nearest `--help` command. For write transport or provider failures, reconcile the current sheet before deciding whether to retry.

## Verify completion

Finish every write with a bounded read-back. State the sheet and affected row IDs plus the safe fields that prove the requested values. For repository changes, run format check, typecheck, unit tests, package smoke, and only explicitly authorized live tests.
