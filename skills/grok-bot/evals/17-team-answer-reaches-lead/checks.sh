#!/usr/bin/env bash
. "$(dirname "$0")/../bot-checks.sh"

reply_ok
python3 - <<'PY2' || exit 1
import json, sys
calls = [json.loads(l) for l in open("calls.jsonl") if l.strip()] if __import__("os").path.exists("calls.jsonl") else []
qid = "qitem-20261123030000-cccc000000000001"
upd = [c for c in calls if c.get("tool") == "rig_queue_update" and c.get("args", {}).get("qitemId") == qid]
if not upd: sys.exit("the answer was not recorded on the lead's item (rig_queue_update on its qitemId)")
a = upd[-1]["args"]
if a.get("state") != "done": sys.exit(f"state is {a.get('state')!r}, want done")
if str(a.get("resolution", "")).strip() != "A": sys.exit(f"resolution is {a.get('resolution')!r}, want the person's exact words: A")
if any(c.get("tool") == "rig_queue_create" for c in calls): sys.exit("created a new row instead of answering the lead's item")
PY2
echo ok
