#!/bin/sh
# A re-upload has a new fileId: the body must point at it, and the update must carry the fresh snapshot token and max width.
EVALS="$(cd "$(dirname "$0")/.." && pwd)" python3 - <<'PY'
import os, re, sys
sys.path.insert(0, os.environ["EVALS"])
from common import *

NEW, OLD = "c3e1f9a7-6b2d-4e8f-a1c4-5d7b9e0f2a02", "0a4b7c1d-2e3f-4a5b-8c6d-9e0f1a2b3c01"
if not os.path.isfile("publish.sh"):
    fail("no publish.sh")
sh = open("publish.sh", encoding="utf-8").read()
if not re.search(r"confluence\s+content\s+update", sh):
    fail("publish.sh does not update the page")
for flag in ("--snapshot-token", "--format html", "--ack-body-formats", "--content-width max", "100003"):
    if flag not in sh:
        fail(f"publish.sh misses {flag}")
if "snap-7f3a9c2e41" not in sh and "snapshotToken" not in sh:
    fail("publish.sh does not use the fresh snapshot token")
m = re.search(r"--body-file[ =]+[\"']?([^\s\"']+)", sh)
if not m:
    fail("publish.sh has no --body-file")
text, body = load(m.group(1))
assert_clean_markup(text, body)
ids = [a.get("data-id") for _, a in media(body)]
if NEW not in ids:
    fail("the body does not point at the re-uploaded fileId")
if OLD in ids:
    fail("the body still points at the old fileId")
for fig, _ in media(body):
    if fig.get("data-width-type") != "pixel":
        fail("the chart lost its pixel width")
assert_tables_sized(body)
print("ok")
PY
