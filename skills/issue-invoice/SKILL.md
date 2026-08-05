---
name: issue-invoice
description: "Fill a monthly hourly invoice on Google Sheets from GitHub PRs and Jira tickets, one tab per month per client. Use when the user mentions an invoice, timesheet, billable hours, logging monthly work, rolling over an invoice month, or reconciling PRs and tickets to hours."
license: MIT
argument-hint: "[client] [YYYY-MM] | rollover | --list"
metadata:
  author: vanducng
  version: "1.0.0"
---

# issue-invoice

Monthly hourly invoicing for contract clients. One Google Sheet per client, one
tab per month (`202607`, `202608`, ...). Rows are billable work reconciled from
merged GitHub PRs, linked to their tracker tickets, plus meeting rows.

Every client-specific value - spreadsheet id, org, repos, Jira host, rate - lives
in a private rules file **outside this repo**. This skill ships no client data.

## Client rules

```
~/.config/vd/invoice-rules/<client>.invoice-rules.md
```

YAML frontmatter is machine-read by the harvest script; the prose below it is for
you. See `references/client.invoice-rules.example.md` for the schema and copy it to
onboard a new client.

```bash
scripts/harvest-prs.py --list          # configured clients
```

Read the whole rules file before drafting rows. It defines the tab layout, column
formats, hour calibration, meeting cadence, and client quirks - all of which vary.

**Never write a client value into this skill.** If something is true for one client
only, it belongs in that client's rules file.

## Workflow

### 1. Read current state first

```bash
gwsj(){ gws "$@" 2>&1 | grep -v '^Using keyring backend'; }
SID=<spreadsheet from rules frontmatter>

gwsj sheets spreadsheets get --params "{\"spreadsheetId\":\"$SID\",\"fields\":\"sheets.properties\"}" \
  | jq -r '.sheets[].properties | "\(.index)\t\(.sheetId)\t\(.title)"'

# read with FORMULA or you lose the HYPERLINK/SUM formulas and will overwrite them
gwsj sheets spreadsheets values get \
  --params "{\"spreadsheetId\":\"$SID\",\"range\":\"<tab>!A1:F60\",\"valueRenderOption\":\"FORMULA\"}"
```

Locate the Total row and its exact `SUM` ranges - they drift as rows are inserted.

### 2. Harvest PRs

```bash
scripts/harvest-prs.py --client <alias> 2026-08
```

Groups PRs by the client's local working day across all configured repos, citing
each with its repo label, and flags dependency-bump PRs.

### 3. Map to tickets and hours

Pull assigned tickets for context (env var names come from the rules frontmatter):

```bash
source ~/.envrc
curl -sS -u "$JIRA_X_USER_EMAIL:$JIRA_X_API_TOKEN" \
  -G "<base_url>/rest/api/3/search/jql" \
  --data-urlencode 'jql=project = <KEY> AND assignee = currentUser() ORDER BY updated DESC' \
  --data-urlencode 'fields=summary,status,resolutiondate' \
  | jq -r '.issues[] | [.key,.fields.status.name,.fields.summary] | @tsv'
```

Most PR titles carry the ticket id; otherwise check the body
(`gh pr view N --repo <slug> --json body`) for a `Jira:` line. When neither exists,
infer from domain and **tell the user which rows were inferred**.

Size hours against the client's calibration table. **Always present the proposed
rows and the new invoice total for approval before writing** - this is money.

### 4. Write

Rows must fit between the header and the Total row; insert first if not.

```bash
# insert N rows before the Total row (0-based startIndex = totalRow-1)
gwsj sheets spreadsheets batchUpdate --params "{\"spreadsheetId\":\"$SID\"}" --json '{"requests":[
  {"insertDimension":{"range":{"sheetId":SHEET_ID,"dimension":"ROWS","startIndex":40,"endIndex":49},"inheritFromBefore":true}}]}'

# copy formatting onto new rows - blank rows carry no currency/wrap format
gwsj sheets spreadsheets batchUpdate --params "{\"spreadsheetId\":\"$SID\"}" --json '{"requests":[
  {"copyPaste":{
    "source":{"sheetId":SHEET_ID,"startRowIndex":10,"endRowIndex":11,"startColumnIndex":0,"endColumnIndex":6},
    "destination":{"sheetId":SHEET_ID,"startRowIndex":11,"endRowIndex":49,"startColumnIndex":0,"endColumnIndex":6},
    "pasteType":"PASTE_FORMAT"}}]}'

gwsj sheets spreadsheets values update \
  --params "{\"spreadsheetId\":\"$SID\",\"range\":\"<tab>!A11:F49\",\"valueInputOption\":\"USER_ENTERED\"}" \
  --json "$(cat /tmp/values.json)"

# repoint Total across the whole block
gwsj sheets spreadsheets values update \
  --params "{\"spreadsheetId\":\"$SID\",\"range\":\"<tab>!E50:F50\",\"valueInputOption\":\"USER_ENTERED\"}" \
  --json '{"values":[["=SUM(E11:E49)","=SUM(F11:F49)"]]}'
```

### 5. Verify

Re-read the block and assert: row count, hours sum equals the Total cell, dates
ascending, no dates outside the month, no blank ticket/note cells. Then screenshot
with `ego-browser` for a visual pass.

## Monthly rollover

```bash
gwsj sheets spreadsheets batchUpdate --params "{\"spreadsheetId\":\"$SID\"}" --json '{"requests":[
  {"duplicateSheet":{"sourceSheetId":OLD_SHEET_ID,"insertSheetIndex":0,"newSheetName":"202609"}}]}'
```

Then: update the invoice number and date cells, `values clear` the old data block
(formatting survives), write the new month from the first data row, leave the
remaining rows blank and inside the `SUM` range so later additions total
automatically, and carry over any meeting belonging to the new month.

## Gotchas

Each of these cost real time. Do not rediscover them.

- **`gws` prints `Using keyring backend: keyring` on stdout** and breaks every `jq`
  pipe. Always use the `gwsj` wrapper.
- **A failing `jq` pipe does not mean the API call failed.** `gws` already sent the
  request. Re-read state before retrying - a blind `insertDimension` retry
  double-inserts rows.
- **`gh pr list` defaults to 30 and truncates silently.** The harvest script guards
  this; if you query by hand, pass `--limit 400`.
- **PR timestamps are UTC; the working day is the client's timezone.** Off-by-one
  here misfiles work across day and month edges.
- **`gws auth login` takes no `--account`.** Use `gws auth login -s sheets,drive`.
  Token death shows as `401 Failed to get token` / `invalid_rapt` and needs
  interactive browser approval - ask the user, it cannot be done headlessly.
- **Calendar is a separate scope** (`-s sheets,drive,calendar`), else
  `403 insufficientPermissions`. Without it, ask for meeting dates.
- **The `jira` CLI may point at a different instance.** Use the REST call above with
  the client's env vars; `jira me` can report the wrong user.
- **Total `SUM` ranges go stale.** One client's read `=SUM(E11:E18)` while data ran
  to row 25. Verify hours x rate equals the amount.
- **PR numbers collide across repos.** Cite with the repo label from the rules file.

## Convention: private config for skills

This skill follows a pattern worth reusing whenever a skill needs real
credentials, hosts, org names, or customer identifiers:

```
~/skills/skills/<skill>/                        tracked, public, zero private data
  references/<thing>.<skill>-rules.example.md   placeholder schema
~/.config/vd/<skill>-rules/<alias>.<skill>-rules.md   private, per-instance
```

The private half lives outside the repo, so it is excluded by construction - no
`.gitignore` entry to forget, nothing to leak in a diff, and adding a client never
touches version control. The skill resolves an alias at runtime and fails with the
list of configured aliases when one is missing. `vd:jira` uses the same layout with
`~/.config/vd/jira-rules/`.
