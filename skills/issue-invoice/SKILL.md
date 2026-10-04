---
name: issue-invoice
description: "Fill a monthly hourly invoice on Google Sheets from GitHub PRs, Jira tickets, Gmail, and calendar meetings that have a transcript, one tab per month per client. Use when the user mentions an invoice, timesheet, billable hours, logging monthly work, rolling over an invoice month, meeting transcripts, or reconciling PRs and tickets to hours."
license: MIT
argument-hint: "[client] [YYYY-MM] | rollover | --list"
metadata:
  author: vanducng
  version: "1.0.0"
---

# issue-invoice

Monthly hourly invoicing for contract clients. One Google Sheet per client, one
tab per month (`202607`, `202608`, ...). Rows are billable work reconciled from
GitHub PRs, linked to their tracker tickets, plus meeting rows.

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
export GOG_HOME="$HOME/.config/vd/gog"
ACCT=<gog_account from rules, --account org with --user person>
CLIENT=<gog client from the account registry>
QUOTA=<quota project from the account registry, omit the flag if absent>
SID=<spreadsheet from rules frontmatter>

gog --account "$ACCT" --client "$CLIENT" ${QUOTA:+--quota-project "$QUOTA"} \
  sheets metadata "$SID" --json

# FORMULA or the next write flattens HYPERLINK/SUM
gog --account "$ACCT" --client "$CLIENT" ${QUOTA:+--quota-project "$QUOTA"} \
  sheets get "$SID" '<tab>!A1:F80' --render FORMULA --json
```

Read the account registry before the first call. Pass `--client` from it. Pass `--quota-project` when that file names one, or Sheets returns API-not-enabled.

Tab names are not always `YYYYMM`. Use the tab the user opened.

Locate the Total row and its exact `SUM` ranges. Match the previous month's total block, including a grand total if that tab has one. The Total sits one blank row under the last work row, with the same label, number formats, and borders as the previous month. If the template left that Total far below a short month, move it up and point `SUM` at the new block. Clear the old Total so only one remains. Do not add section subtotal rows unless the previous month has them or the user asks.

### 2. Harvest PRs

```bash
scripts/harvest-prs.py --client <alias> 2026-08
```

Groups PRs by the client's local working day across all configured repos, citing
each with its repo label, and flags dependency-bump PRs.

All PR states are harvested, not just merged - a superseded or closed PR still
represents work done. Unmerged ones are marked `[not merged]` so you can judge
whether they are billable or were abandoned.

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

### 3b. Gmail for work the PR list does not show

Some billable work never becomes a PR: a design pass, a data fix, a login or report investigation. Search the client's mailbox for that month before closing the rows.

```bash
export GOG_HOME="$HOME/.config/vd/gog"
gog --account "$ACCT" --client "$CLIENT" --readonly --gmail-no-send \
  gmail search 'after:YYYY/MM/01 before:YYYY/MM+1/01 <requestor or feature words>' \
  --max 30 --json --no-input
```

Use the thread for the requestor, the scope, and any hour cap they already agreed. Cite it in the note. Say which rows were inferred from mail.

### 3c. Meetings that actually happened

Event titles and duration live in the client rules. A calendar hold is not billable by itself.

Include the instance only when it has its own transcript:

- a Gemini `Notes:` message for that date, or
- a notes attachment whose file id belongs to that instance

A recurring series often copies one shared notes doc onto every instance. That shared file is not a transcript. Skip the hold when it is the only attachment, and skip instances with no notes email and no unique notes doc.

Column B stays `Meeting`. Column C is the event title from the rules.

### 4. Write

Rows must fit between the header and the Total row; insert first if not.

```bash
export GOG_HOME="$HOME/.config/vd/gog"
# insert N rows before the Total row (start is 1-based; the API startIndex is start-1)
gog --account "$ACCT" sheets insert "$SID" <tab> ROWS <start> --count N --inherit-from-before

gog --account "$ACCT" sheets copy-paste "$SID" '<tab>!A11:F11' '<tab>!A12:F49' --type FORMAT

gog --account "$ACCT" sheets update "$SID" '<tab>!A11:F49' --input USER_ENTERED --values-json @/tmp/values.json

gog --account "$ACCT" sheets update "$SID" '<tab>!E50:F50' --input USER_ENTERED --values-json '[["=SUM(E11:E49)","=SUM(F11:F49)"]]'
```

### 5. Verify

Re-read the block and assert: row count, hours sum equals the Total cell, dates
ascending, no dates outside the month, no blank ticket/note cells. Then screenshot
with `ego-browser` for a visual pass.

## Monthly rollover

```bash
export GOG_HOME="$HOME/.config/vd/gog"
gog --account "$ACCT" api call sheets v4 spreadsheets.batchUpdate --allow-write \
  --params "{\"spreadsheetId\":\"$SID\"}" \
  --body '{"requests":[{"duplicateSheet":{"sourceSheetId":OLD_SHEET_ID,"insertSheetIndex":0,"newSheetName":"202609"}}]}'
```

Then: update the invoice number and date cells, `values clear` the old data block
(formatting survives), write the new month from the first data row, leave the
remaining rows blank and inside the `SUM` range so later additions total
automatically, and carry over any meeting belonging to the new month.

## Gotchas

Each of these cost real time. Do not rediscover them.

- **Always `export GOG_HOME=$HOME/.config/vd/gog`.** A bare `gog` stores tokens
  under `~/.config/gogcli` and this skill will not see them.
- **Person-user alias only** (refresh token). Do not use `*-sa` or `--access-token`
  for invoice writes. See `vd:gog` person-user auth.
- **A failing `jq` pipe does not mean the API call failed.** Re-read state before
  retrying - a blind row insert doubles rows.
- **`gh pr list` defaults to 30 and truncates silently.** The harvest script guards
  this; if you query by hand, pass `--limit 400`.
- **PR timestamps are UTC; the working day is the client's timezone.** Off-by-one
  here misfiles work across day and month edges.
- **Token death** (`invalid_grant` / `invalid_rapt`) needs `gog auth add --force-consent`
  for that person alias. Weekly death means the OAuth app is still in Testing -
  publish it; do not keep re-authing.
- **Calendar is a separate scope.** If `gog calendar` 403s, ask for meeting dates
  or re-add with calendar in `--services`.
- **A shared series notes doc is not attendance.** Count a meeting only from a unique notes doc or a notes email for that date.
- **`invalid_rapt` after a cloud scope was added.** If the account file forbids scopes such as BigQuery or `cloud-platform`, re-auth with that file's `--services` list and check the new token does not still carry them. Extra cloud scopes put the refresh token under workspace session control.
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
