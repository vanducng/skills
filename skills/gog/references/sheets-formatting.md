# Styled Google Sheet Reports

Use this path for presentation-ready, multi-tab reports. For a small edit to an
existing Sheet, use native `gog sheets format` commands instead.

## Architecture

```text
source rows
    -> local XLSX renderer
    -> structural validation
    -> Drive upload with --convert-to sheet
    -> native Google Sheet
    -> metadata and row-count verification
    -> local sensitive-file cleanup
```

The local workbook is a rendering boundary. It keeps layout logic out of API
orchestration, reduces many formatting calls to one upload, and leaves a file
that can be validated before any external write.

## Visual hierarchy

Use a restrained semantic palette and repeat it across tabs:

| Role | Color |
|---|---|
| Title and table headers | navy `#16324F` |
| Section bars and accents | teal `#008A9A` |
| Success or completed | green `#2E7D32`, light `#E8F5E9` |
| Review or warning | amber `#F9A825`, light `#FFF4D6` |
| Blocked or missing | red `#C62828`, light `#FDE8E7` |
| Supporting labels | light blue `#E8F1FA` |
| Secondary text | gray `#5F6B76` |

A review workbook normally needs:

1. **Summary** first: title, generation time, key counts, current status, and a short decision note.
2. **Actionable records** next: rows ready for the intended operation.
3. **Exceptions** after that: missing, rejected, or decision-required rows.
4. **Audit detail** last: duplicates and original source data.

On data tabs, use one header row, freeze it, enable filters or a table, hide
gridlines, wrap long text, set deliberate column widths, and hyperlink URL
cells. Color status cells semantically; do not color every cell.

## Minimal renderer

`openpyxl` is useful when it is already available and the report needs several
styled tabs. Do not add it for a one-cell formatting change.

```python
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo

OUTPUT = Path("/tmp/review-report.xlsx")
NAVY = "16324F"
TEAL = "008A9A"
WHITE = "FFFFFF"


def add_data_tab(workbook, title, headers, rows, table_name):
    sheet = workbook.create_sheet(title)
    sheet.sheet_properties.tabColor = TEAL
    sheet.sheet_view.showGridLines = False
    sheet.freeze_panes = "A2"
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    for cell in sheet[1]:
        cell.fill = PatternFill("solid", fgColor=NAVY)
        cell.font = Font(color=WHITE, bold=True)
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
    table = Table(displayName=table_name, ref=sheet.dimensions)
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    sheet.add_table(table)
    for column in sheet.columns:
        values = [str(cell.value or "") for cell in column[:100]]
        sheet.column_dimensions[column[0].column_letter].width = min(max(map(len, values), default=12) + 2, 48)
    return sheet


workbook = Workbook()
summary = workbook.active
summary.title = "Summary"
summary.sheet_view.showGridLines = False
summary.merge_cells("A1:F2")
summary["A1"] = "Review Report"
summary["A1"].fill = PatternFill("solid", fgColor=NAVY)
summary["A1"].font = Font(color=WHITE, bold=True, size=20)
summary["A3"] = f"Generated {datetime.now():%Y-%m-%d %H:%M}"

rows = [["Complete", 12], ["Needs review", 2]]
add_data_tab(workbook, "Records", ["Status", "Count"], rows, "ReviewRecords")
workbook.save(OUTPUT)

check = load_workbook(OUTPUT, read_only=True, data_only=True)
assert check.sheetnames == ["Summary", "Records"]
assert check["Records"].max_row == len(rows) + 1
```

Keep table names unique, free of spaces, and stable. Bound automatic width
sampling so a large report does not scan every cell twice.

## Convert and upload

Confirm the destination and identity before the write. Conversion creates a
native Google Sheet and usually preserves common tab, cell, table, freeze-pane,
width, hyperlink, and chart formatting.

```bash
export GOG_HOME="${GOG_HOME:-$HOME/.config/vd/gog}"

ACCOUNT=<account>
CLIENT=<client>
FOLDER_ID=<folder-id>
FILE=/tmp/review-report.xlsx
TITLE="Review Report"

gog --account "$ACCOUNT" --client "$CLIENT" drive upload "$FILE" \
  --parent "$FOLDER_ID" --name "$TITLE" --convert-to sheet \
  --dry-run --json --no-input

gog --account "$ACCOUNT" --client "$CLIENT" drive upload "$FILE" \
  --parent "$FOLDER_ID" --name "$TITLE" --convert-to sheet \
  --json --no-input
```

Do not assume every advanced Excel feature survives conversion. Treat charts,
conditional formatting, formulas, merged cells, and print settings as visual
features that need verification.

## Verify and clean up

Use the returned spreadsheet ID rather than searching by title:

```bash
SPREADSHEET_ID=<spreadsheet-id>

gog --account "$ACCOUNT" --client "$CLIENT" --readonly \
  sheets metadata "$SPREADSHEET_ID" --json --no-input

gog --account "$ACCOUNT" --client "$CLIENT" --readonly \
  sheets get "$SPREADSHEET_ID" "'Records'!A1:A100" --json --no-input
```

Verify:

- native MIME type is `application/vnd.google-apps.spreadsheet`
- expected tab names exist in the intended order
- each data tab has its expected header plus row count
- the file is in the requested folder
- representative status colors, links, widths, and charts look correct

When the report contains personal or sensitive data, keep intermediates outside
Git and delete the local XLSX, source exports, and verification responses after
the native Sheet is verified.
