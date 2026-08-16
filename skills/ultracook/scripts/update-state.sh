#!/usr/bin/env bash
# update-state.sh - create or atomically patch {goal-dir}/state.json (schema v2).
#
# Usage:
#   update-state.sh init <goal-dir>          (full initial state on stdin)
#   update-state.sh patch <goal-dir>         (JSON merge patch on stdin)
#
# Patch semantics: RFC 7396-style recursive merge; setting a key to null clears it.
# `updated_at` is auto-set on every write. Atomic: write state.json.tmp, then rename.
# Validates: version=2, terminal in {null, done, blocked, abandoned}.

set -euo pipefail

CMD="${1:?usage: update-state.sh <init|patch> <goal-dir>}"
GOAL_DIR="${2:?usage: update-state.sh <init|patch> <goal-dir>}"
case "$CMD" in
  init)
    mkdir -p "$GOAL_DIR"
    [ -f "${GOAL_DIR}/state.json" ] && { echo "update-state.sh: ${GOAL_DIR}/state.json already exists" >&2; exit 2; }
    ;;
  patch)
    [ -f "${GOAL_DIR}/state.json" ] || { echo "update-state.sh: ${GOAL_DIR}/state.json not found" >&2; exit 2; }
    ;;
  *) echo "update-state.sh: unknown command: $CMD" >&2; exit 2 ;;
esac

if [ -f "${GOAL_DIR}/state.json.tmp" ]; then
  echo "update-state.sh: ${GOAL_DIR}/state.json.tmp exists - previous write crashed." >&2
  echo "  manual recovery: rm '${GOAL_DIR}/state.json.tmp' and re-derive from state.json." >&2
  exit 3
fi

INPUT_JSON="$(cat)"

CMD="$CMD" GOAL_DIR="$GOAL_DIR" INPUT_JSON="$INPUT_JSON" "$(command -v python3)" - <<'PY'
import os, sys, json, datetime

cmd = os.environ["CMD"]
goal_dir = os.environ["GOAL_DIR"]
state_path = os.path.join(goal_dir, "state.json")
tmp_path = state_path + ".tmp"
payload = json.loads(os.environ["INPUT_JSON"])

if cmd == "init":
    state = payload
    state.setdefault("version", 2)
    state["created_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
else:
    with open(state_path) as f:
        state = json.load(f)
    def merge(target, patch):
        for k, v in patch.items():
            if isinstance(v, dict) and isinstance(target.get(k), dict):
                merge(target[k], v)
            else:
                target[k] = v
    merge(state, payload)

state["updated_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

if state.get("version") != 2:
    print(f"update-state.sh: invalid version: {state.get('version')}", file=sys.stderr)
    sys.exit(4)
if state.get("terminal") not in (None, "done", "blocked", "abandoned"):
    print(f"update-state.sh: invalid terminal: {state.get('terminal')}", file=sys.stderr)
    sys.exit(4)

with open(tmp_path, "w") as f:
    json.dump(state, f, indent=2)
    f.write("\n")
os.replace(tmp_path, state_path)
PY
