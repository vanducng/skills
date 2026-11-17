---
name: confluence-publish
description: "Publish a locally built HTML report (tables, status pills, inline SVG or Mermaid charts) to a Confluence Cloud page through the twg CLI, so it renders the way it looked locally: scripts/to_confluence.py turns the report into Confluence HTML (strong not b, no class attributes, status lozenges, info panels, a pixel width on every table cell, charts as attached media at full width) and scripts/twgj.sh reads twg JSON output. Covers create, update with a snapshot token, chart uploads and re-uploads, child page order, a Jira follow-up comment, and checking the live page. Use when the user says 'publish this report to Confluence', 'push the HTML report to the Confluence page', 'update the Confluence page with the new report', 'the Confluence table columns are all the same width', 'the chart is a tiny thumbnail on Confluence', or 'upload the charts to the page'. Not for searching or reading Confluence, space admin, or Jira work beyond the follow-up comment (twg's own skills, vd:jira)."
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
---

# confluence-publish

A report that looks right in a browser loses its look on Confluence: class-based styling is dropped, `<b>` and inline SVG do not survive, tables split columns evenly, and an image with a percentage width shows as a small thumbnail. The scripts here produce a body that keeps the layout. `S=<this skill dir>/scripts`.

## Rules

1. **Read the HTML contract once per session:** `twg confluence content body-formats html`. The update flag `--ack-body-formats` stands for having read it.
2. **Never hand-convert the report.** Run `$S/to_confluence.py`; it applies every markup rule and lints its own output (exit 1 on a problem). After editing a body by hand, run `$S/to_confluence.py --lint body.html`.
3. **Read twg JSON with `$S/twgj.sh <twg args>`**, not by parsing stdout. twg may print a YAML summary whose `output_files.stdout` is a file holding the JSON; the helper handles both shapes.
4. **Every chart is an attachment.** Render SVG and Mermaid to PNG first (`references/charts.md`: text size math, 2x export). Upload, then map the `fileId` in `media.json`.
5. **A re-upload under the same file name gets a new `fileId`.** Update `media.json`, rebuild the body and update the page, or the page keeps the old picture.
6. **Full-width page:** pass `--content-width max` on create and on every update.
7. **Updates need a fresh `snapshotToken`** from `get` right before the update. A rename is `update --title` alone: do not resend the body.
8. **A write is not proof.** Measure the live page (`references/verify.md`) before saying it is published.

## Publish a report

```bash
twg confluence content create --space-id <space-id> --parent-id <parent-id> --title "<title>" \
  --body "<p>Draft</p>" --format html --ack-body-formats --content-width max -y -o json   # new page only
PAGE=<page-id>
for f in charts/*.png; do
  $S/twgj.sh confluence content attachments upload --id "$PAGE" --file "$f" -y | jq -r '.. | .fileId? // empty'
done   # write each into media.json: {"charts/burndown.png": {"fileId": "..."}, "#velocity": {"fileId": "...", "file": "charts/velocity.png"}}
python3 $S/to_confluence.py report.html --page-id "$PAGE" --media media.json \
  --widths '{"Ticket": 120, "Status": 110, "Summary": 480}' -o body.html
TOKEN=$($S/twgj.sh confluence content get --id "$PAGE" | jq -r .data.snapshotToken)
twg confluence content update --id "$PAGE" --snapshot-token "$TOKEN" --body-file body.html \
  --format html --ack-body-formats --content-width max -y
```

- **Widths:** map the header text to px. A column you leave out gets a width from its longest cell, printed on stderr so you can pin it. Narrow columns (ids, status, dates) 90 to 130, prose 400 to 520.
- **Media keys:** an `<img src>` or its basename; an inline `<svg>` by `#id`, else `svg-1`, `svg-2` in page order. Native size comes from the PNG; figures get `data-width` 1800 in pixels, which the page clamps to its content width.
- **Markup it writes:** `<strong>`/`<em>`; status spans as `data-type="status"` lozenges (green, yellow, red, neutral by class word); note or callout divs as `panel-info` (warning, error, success when the class says so); `language-*` kept only on code blocks; marks moved off inline `<code>`.

## Around the page

- **Order children:** `twg confluence content move <page-id> --before <sibling-id> -y` (or `--after`).
- **Jira follow-up:** `twg jira workitem comment create --issue-id <KEY> --body "<text>" --body-format markdown` (no `-y`). To move the ticket, `twg jira workitem transition --id <KEY>` lists the transitions, then add `--transition-id <id>`.
