# MCP connector rules

Copy this file to `$HOME/.config/vd/mcp-connector.md`. Keep the filled copy outside Git. It names the tracker project, the production host pattern, and the credential-store item. It does not contain the client secret.

## Tracker

- Project key: `<project-key>`
- Issue type: `<issue-type>`
- Assignee: leave unassigned

## Connector

- Host URL: `https://<mcp-host>/<server>/mcp`
- Credential store: `<password-manager>`
- Item name: `<item-name>`
- The Client ID and Client Secret live in that item. The ticket names the item. Never paste the secret.
- Do not use the product OAuth client named here: `<product-oauth-client>`

## Notes

- An existing connector on the same host, if any: `<existing-connector>`
- Screenshot: Settings, Connectors, Add, Add custom connector. Attach it inline in the description.
