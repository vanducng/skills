#!/usr/bin/env bash
# The person added a condition, so the answer is their exact words, not an option the bot picked.
set -u
[ -s call.json ] || { echo "no call.json"; exit 1; }
python3 - <<'PY' || exit 1
import json, sys
c = json.load(open("call.json"))
a = c.get("args", {})
want = "go with the second one, but only after Friday's release"
problems = []
if c.get("tool") != "rig_question_answer": problems.append(f"tool is {c.get('tool')!r}, want rig_question_answer")
if a.get("qitemId") != "qitem-20261122093000-1a2b3c4d5e6f7a8b": problems.append("wrong qitemId")
if a.get("revision") != "r3": problems.append("wrong or missing revision")
if "choices" in a: problems.append("chose an option for the person; their answer carries a condition")
if a.get("words") != want: problems.append(f"words are {a.get('words')!r}, want the person's exact text")
print("\n".join(problems) or "ok"); sys.exit(1 if problems else 0)
PY
