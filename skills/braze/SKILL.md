---
name: braze
description: Operate Braze through the braze-cli category commands for campaigns, Canvas, catalogs, analytics, messaging, SMS, subscriptions, users, templates, and content blocks. Use when the user asks to inspect Braze data, diagnose REST permissions, change opt-in or opt-out state, or validate and ship the Braze CLI.
license: MIT
allowed-tools:
  - Bash
metadata:
  version: "1.0.0"
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

Use `BRAZE_REST_ENDPOINT`, `BRAZE_API_KEY`, and optional `BRAZE_APP_ID`. The CLI also reads the current directory's `.env` and supports the compatibility keys `braze_host`, `braze_api_token`, and `braze_login`. Never print, copy, or commit credential values.

## Discover commands by category

Start at the resource category, then inspect the exact leaf help before relying on flags:

```bash
braze campaign --help
braze campaign list --help
braze subscription --help
braze subscription update --help
```

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
- Branch on `error.code` and retry only when `error.retryable` is true.
- Treat HTTP 403 as a missing leaf permission and report the permission named by command help.
- Keep provider payloads, user identifiers, phone numbers, emails, and credentials out of logs.
- Use `--input @request.json` for reviewed complex objects and explicit flags for small inputs.

## Validate the CLI repository

When the current repository is the `braze-cli` source, run:

```bash
npm ci
npm run verify
npm run test:live
```

The live matrix executes every read command and emits safe metadata. Supply `BRAZE_LIVE_*` fixtures when validation must fetch a specific resource. `verification: authorized_no_fixture` is acceptable only for an absent resource returning HTTP 400 or 404; authentication, permission, output, and embedded item errors fail the run.

Before package delivery, verify CI, the packed artifact, the registry-installed binary, the published npm version, and one bounded live read from the installed package.
