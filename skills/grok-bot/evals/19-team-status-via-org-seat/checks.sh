#!/usr/bin/env bash
# A rig's status is asked of the org seat as a task, not read off rig_ps (which sees only the seat's own rig).
. "$(dirname "$0")/../bot-checks.sh"
reply_ok
[ -z "$(computer_calls)" ] || { echo "used a computer: $(computer_calls | head -1)"; exit 1; }
python3 - <<'PY2' || exit 1
import json, os, sys
calls = [json.loads(l) for l in open("calls.jsonl") if l.strip()] if os.path.exists("calls.jsonl") else []
tasks = [c for c in calls if c.get("tool") == "rig_queue_create"]
if not tasks: sys.exit("no task to the org seat (rig_queue_create)")
a = tasks[0].get("args", {})
dest = str(a.get("destination") or a.get("destinationSession") or a.get("to") or "")
if not dest.startswith("grok-bot@acme-grokbot"): sys.exit(f"the task goes to {dest!r}, want the org seat grok-bot@acme-grokbot")
if "orchard" not in json.dumps(a).lower(): sys.exit("the task does not ask about orchard")
PY2
grep -Eiq 'running|idle' reply.md && ! grep -Eiq 'asked|task|request|will (tell|report|let)' reply.md && { echo "answered orchard's status from rig_ps"; exit 1; }
echo ok
