---
name: braze
description: Operate the Braze platform through braze-cli category commands for campaigns, Canvas, catalogs, analytics, messaging, SMS, subscriptions, users, templates, and content blocks. Use when the user asks to inspect Braze data, diagnose permissions, change opt-in or opt-out state, or validate and ship the Braze CLI.
license: MIT
allowed-tools:
  - Bash
metadata:
  version: "1.2.0"
  binary: braze
---

# Braze

Operate Braze through the installed `braze` binary. Generated help and JSON responses are the runtime contract.

## Start safely

```bash
command -v braze
braze --version
braze --help
braze workspace list
```

If the binary is missing, report it and offer `npm install --global braze-cli`. Do not install or upgrade it unless the user asks.

Configure the CLI interactively, then verify without exposing values:

```bash
braze login
braze workspace list
```

Copy the REST endpoint and API key from [**Settings > APIs and Identifiers > API Keys**](https://www.braze.com/docs/api/basics#endpoints) in Braze. The App ID is optional. Login masks the API key and writes the user config with mode `0600`. Do not inspect, print, copy, or commit credential values.

**Credentials come only from the saved config file.** `BRAZE_REST_ENDPOINT` and `BRAZE_API_KEY` in the environment are **ignored** - exporting them does nothing. `loadSavedConfig` reads `$XDG_CONFIG_HOME/braze/config.json` (default `~/.config/braze/config.json`) and nothing else; the environment is consulted only to locate that file. Verified: with both env vars set but an empty config dir, `workspace list` reports `api_key_configured: false`.

This matters when a task needs a *different* key than the saved one (a read-only token, another workspace). Exporting env vars silently keeps using the saved key and the request fails with a confusing `403 permission_error` that looks like a missing scope. Point the CLI at a scratch config instead:

```bash
TMP=$(mktemp -d); mkdir -p "$TMP/braze"
printf '{"BRAZE_REST_ENDPOINT":"%s","BRAZE_API_KEY":"%s"}\n' "$ENDPOINT" "$KEY" > "$TMP/braze/config.json"
chmod 600 "$TMP/braze/config.json"
XDG_CONFIG_HOME="$TMP" braze workspace list      # confirm it resolved
# ... run the read commands ...
rm -rf "$TMP"                                     # never leave the key on disk
```

## Discover commands by category

Start at the resource category, then inspect the exact leaf help before relying on flags:

```bash
braze campaign --help
braze campaign list --help
braze subscription --help
braze subscription update --help
```

Leaf help is the function contract. It includes the detailed purpose, permission, authoritative Braze documentation, safe JSON input, executable command, and typed option constraints. Follow the linked Braze page when nested object semantics or provider behavior affect the request.

The CLI groups operations under categories such as `campaign`, `canvas`, `catalog`, `cdi`, `content-block`, `custom-attribute`, `event`, `kpi`, `message`, `purchase`, `sdk-authentication`, `segment`, `send`, `session`, `sms`, `subscription`, `template`, and `user`.

## Read with discovery

1. Run the smallest list request.
2. Capture the exact resource ID without echoing unrelated provider data.
3. Run the detail or analytics command with the smallest useful page or time range.
4. Report the command, required permission, HTTP outcome, response type, and bounded record count.

```bash
braze campaign list --page 0
braze campaign get --campaign-id <campaign-id>
braze campaign data-series --campaign-id <campaign-id> --length 7
```

The CLI does not auto-paginate. A successful empty collection proves the read worked but not that the workspace contains matching data. HTTP 400 or 404 from a synthetic missing identifier may prove authentication, routing, and permission, but it is not evidence that resource data was fetched.

## Protect opt-in and opt-out changes

Treat subscription, SMS, messaging, and user mutations as externally visible writes. Require explicit authorization for the target identifiers and intended state.

1. Read the current subscription state.
2. Confirm the exact group, identifiers, and `subscribed` or `unsubscribed` target.
3. Inspect leaf help and build the smallest request.
4. Add `--confirm` only after review.
5. Read the same target again and verify the resulting state.

Use `use_double_opt_in_logic` only when the user explicitly wants Braze's double opt-in behavior. Do not infer `opted_in`, `subscribed`, and `unsubscribed` semantics from ordinary language when the choice changes delivery eligibility.

Never retry an ambiguous write until a read proves whether Braze committed it. Writes without `--confirm` must stop before loading credentials or contacting Braze.

## Use the JSON contract

- Parse stdout only after exit status 0.
- Parse failures from stderr as `{ "ok": false, "error": { ... } }`.
- Read commands retry transient failures with bounded backoff. Retry again only when the final error sets `error.retryable` to true.
- Treat HTTP 403 as a missing leaf permission and report the permission named by command help.
- Keep provider payloads, user identifiers, phone numbers, emails, and credentials out of logs.
- Use `--input @request.json` for reviewed complex objects and explicit flags for small inputs.
- **Pass array options as one comma-separated value, never as a repeated flag.** `string[]` options are split on commas; repeating the flag keeps only the **last** value and fails silently - the call succeeds and quietly returns one record. Batching 50 identifiers this way collapses to 1 with no error.

  ```bash
  braze user export-ids --external-ids "id1,id2,id3"          # correct
  braze user export-ids --external-ids id1 --external-ids id2 # WRONG - only id2 is sent
  braze user export-ids --input '{"external_ids":["id1","id2"]}'  # also correct
  ```

  The same applies to every `string[]` option (`--email`, `--phone`, `--fields-to-export`, …). When a batched read returns fewer records than identifiers supplied, suspect this before suspecting the data.

## Validate the CLI repository

When the current repository is the `braze-cli` source, run:

```bash
npm ci
npm run verify
npm run test:live
```

The live matrix executes every read command and emits safe metadata. Supply `BRAZE_LIVE_*` fixtures when validation must fetch a specific resource. `verification: authorized_no_fixture` is acceptable only for an absent resource returning HTTP 400 or 404; authentication, permission, output, and embedded item errors fail the run.

Before package delivery, verify CI, the packed artifact, the registry-installed binary, the published npm version, and one bounded live read from the installed package.
