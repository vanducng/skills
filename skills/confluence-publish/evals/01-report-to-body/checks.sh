#!/bin/sh
# A report becomes a Confluence body: <strong>, no class attributes, status lozenges, an info panel, and a width on every cell.
EVALS="$(cd "$(dirname "$0")/.." && pwd)" python3 - <<'PY'
import os, sys
sys.path.insert(0, os.environ["EVALS"])
from common import *

text, body = load("body.html")
assert_clean_markup(text, body)
assert_tables_sized(body)
colors = {a.get("data-color") for t, a in body.tags if t == "span" and a.get("data-type") == "status"}
if not {"green", "yellow", "red"} <= colors:
    fail(f"status pills not lozenges with green/yellow/red (got {sorted(c for c in colors if c)})")
if not any(t == "div" and a.get("data-type") == "panel-info" for t, a in body.tags):
    fail("the note is not an info panel")
table = body.tables[0]
for narrow in ("Ticket", "Status"):
    if max(column_widths(table, narrow)) > 180:
        fail(f"{narrow} column wider than 180px")
if min(column_widths(table, "Summary")) < 360:
    fail("Summary column narrower than 360px")
for tag, a in body.tags:
    if tag == "code" and a.get("class", "").startswith("language-"):
        break
else:
    fail("the bash code block lost its language-bash class")
print("ok")
PY
