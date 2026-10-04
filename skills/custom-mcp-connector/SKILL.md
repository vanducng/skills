---
name: custom-mcp-connector
description: "Files the admin request that registers a remote MCP on the team Claude Desktop app. Activates when the user says 'custom mcp', 'custom connector', 'add connector', 'Claude Desktop connector', or asks to add an MCP to the team Claude account. Instance host, tracker, and credential-store names come from $HOME/.config/vd/mcp-connector.md. Do not use for implementing an MCP server, local stdio MCP config, or a one-seat Claude Code smoke test."
license: MIT
metadata:
  author: vanducng
  version: "1.0.0"
---

# Custom MCP connector

> A team Claude Desktop custom connector is an admin action. The agent files the request. It does not add the connector itself.

Instance values live outside this repo. Copy `references/mcp-connector.example.md` to `$HOME/.config/vd/mcp-connector.md` and fill it in. Read that file before filing anything. If it is missing, stop and ask for it. Do not invent a host, project key, or credential-store item.

## What this skill is, and is not

| This skill | Not this skill |
| --- | --- |
| Add a remote MCP URL to the team Claude Desktop app | Build or change the MCP server (`vd:cook`) |
| Tell the admin which host and credential-store item to use | Paste a client secret into a ticket, chat, or commit |
| File the request named in the rules file | Drive Jira field mechanics (`vd:jira`) |

## Hard rules

1. The team Claude Desktop app can add a custom connector only through an admin. An agent seat must not use Add custom connector itself. The control is admin-only, so a non-admin attempt fails and leaves no record.
2. Setup needs three values: the host URL, the Client ID, and the Client Secret. The host alone is not enough. These are the connector OAuth client credentials named in the rules file, not the product's own OAuth client (for example a Google OAuth client).
3. Read the Client ID and Client Secret from the credential store and item named in the rules file. Never copy the secret into the ticket, a comment, a log, or a commit. The ticket names the item so an admin can open it.
4. The host is the production MCP URL for that server. Staging bearer tokens are for smoke tests, not for the team Desktop connector.
5. File the issue type on the project key from the rules file, and leave it unassigned unless that file says otherwise. Use `vd:jira` for the write. Put a screenshot of Settings, Connectors, Add, Add custom connector inline in the description.

## Workflow

1. Load `$HOME/.config/vd/mcp-connector.md`. Refuse when it is missing.
2. Confirm the production MCP URL for this server. Use the host pattern in the rules file.
3. Confirm the named credential-store item has a Client ID and a Client Secret. Do not print the secret.
4. Create the request. The description states:
   - Add the connector in the Claude Desktop app: Settings, Connectors, Add, Add custom connector.
   - Host URL.
   - Client ID and Client Secret are in the named credential-store item. Do not use the product OAuth client named in the rules file.
   - Only an admin can do this.
5. Verify the stored ticket contains that host, the credential-store item name, and the inline screenshot. It must not contain a secret value.
6. After the request is done, confirm the connector is listed in Claude Desktop and a signed-in user can call one read-only tool. Do not treat the ticket as connected before that.
