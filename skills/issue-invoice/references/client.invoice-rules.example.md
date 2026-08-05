---
client: Example
timezone: UTC
github_author: <github-login>
spreadsheet: <google-sheets-file-id>
rate: 100
invoice_prefix: INV-EXAMPLE
repos:
  - slug: <org>/<repo>
    label: ""
  - slug: <org>/<other-repo>
    label: "other "
jira:
  base_url: https://example.atlassian.net
  project: EXAMPLE
  token_env: JIRA_EXAMPLE_API_TOKEN
  email_env: JIRA_EXAMPLE_USER_EMAIL
---

# Invoice rules: example

Copy this file to `~/.config/vd/invoice-rules/<client>.invoice-rules.md`.
Keep the local copy outside Git - it holds the spreadsheet id, org names, and
Jira host for a real client.

## Frontmatter

Machine-read by `scripts/harvest-prs.py`. Everything below the frontmatter is
prose for the agent.

| Key | Meaning |
|---|---|
| `client` | Display name used in summaries |
| `timezone` | IANA zone defining the working day. PR timestamps are UTC and must be converted before grouping |
| `github_author` | PR author login to filter on |
| `spreadsheet` | Google Sheets file id |
| `rate` | Hourly rate, written to column D |
| `invoice_prefix` | Invoice number becomes `<prefix>-<YYYYMM>` |
| `repos[].slug` | `owner/repo` to harvest |
| `repos[].label` | Prefix used when citing that repo's PRs. Required whenever two repos have overlapping PR number ranges, e.g. `(other PR #201)` vs `(PR #1234)` |
| `jira.*` | Base URL, project key, and the env var names holding credentials. **Names only - never the secrets** |

## Tab layout

Describe where the invoice number, date, header row, and Total row live, so a
future session does not have to rediscover the grid.

## Column conventions

Spell out each column's exact format, especially any formulas (`=HYPERLINK(...)`,
`=D{row}*E{row}`) - these are easy to silently replace with plain text.

## Hour calibration

A PRs-per-day to hours table the client has already accepted, plus any cap on a
single row.

## Meetings

Cadence and duration, and whether they come from a calendar or are supplied manually.

## Client-specific notes

Anything that changes how work maps to billable rows: bot-authored PRs to exclude,
where ticket ids live, recurring inferred mappings.
