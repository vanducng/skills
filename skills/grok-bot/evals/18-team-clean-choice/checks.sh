#!/usr/bin/env bash
. "$(dirname "$0")/../bot-checks.sh"

reply_ok
python3 - <<'PY2' || exit 1
import json, os, sys
calls = [json.loads(l) for l in open("calls.jsonl") if l.strip()] if os.path.exists("calls.jsonl") else []
ans = [c for c in calls if c.get("tool") == "rig_question_answer"]
if not ans: sys.exit("no rig_question_answer call")
a = ans[-1]["args"]
if a.get("qitemId") != "qitem-20261123040000-dddd000000000001" or a.get("revision") != "r2": sys.exit("wrong qitemId or revision")
if a.get("choices") not in (["opt-b"], "opt-b", ["B"], "B"): sys.exit(f"choices are {a.get('choices')!r}, want the second option")
PY2
echo ok
