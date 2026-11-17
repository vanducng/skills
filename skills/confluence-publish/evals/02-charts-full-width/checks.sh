#!/bin/sh
# Charts become attached media at a pixel width with their native size, never a percentage thumbnail or a local <img>/<svg>.
EVALS="$(cd "$(dirname "$0")/.." && pwd)" python3 - <<'PY'
import os, sys
sys.path.insert(0, os.environ["EVALS"])
from common import *

text, body = load("body.html")
assert_clean_markup(text, body)
want = {
    "5d0c2a3e-1b7f-4c55-9a51-2f6c0e8b1a01": (2400, 1200),
    "5d0c2a3e-1b7f-4c55-9a51-7d9e4f2a3b02": (2400, 1400),
}
seen = {}
for fig, m in media(body):
    if fig.get("data-type") != "media-single":
        fail("media not in a media-single figure")
    if fig.get("data-width-type") != "pixel":
        fail(f'figure width type {fig.get("data-width-type")!r}; a percentage renders a small thumbnail')
    if float(fig.get("data-width") or 0) < 1200:
        fail(f'figure data-width {fig.get("data-width")} is too small for a full-width page')
    if m.get("data-collection") != "contentId-100002":
        fail(f'data-collection {m.get("data-collection")!r}, expected contentId-100002')
    seen[m.get("data-id")] = (int(float(m.get("data-width") or 0)), int(float(m.get("data-height") or 0)))
for file_id, size in want.items():
    if file_id not in seen:
        fail(f"no media with fileId {file_id}")
    if seen[file_id] != size:
        fail(f"media {file_id} declares {seen[file_id]}, native size is {size}")
print("ok")
PY
