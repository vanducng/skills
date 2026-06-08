#!/usr/bin/env bash
# update-state.sh — atomic merge-patch on plans/goals/{slug}/state.json.
#
# Usage:
#   update-state.sh --goal-dir <dir>  (reads JSON merge patch from stdin)
#
# Stdin: a JSON object with the keys to overwrite. e.g.
#   {"current_action": "cook", "iteration_count": 4}
# Setting a key to null clears it (JSON Merge Patch semantics — RFC 7396).
#
# `updated_at` is auto-set to now() on every write.
# Atomic: writes state.json.tmp in the same dir then mv.
# Validates: version=1, terminal in {null,done,blocked,abandoned}.

set -euo pipefail

GOAL_DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --goal-dir) GOAL_DIR="${2:?--goal-dir requires arg}"; shift 2 ;;
    --help|-h)  echo "usage: update-state.sh --goal-dir <dir>  (patch on stdin)"; exit 0 ;;
    *)          echo "update-state.sh: unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -z "$GOAL_DIR" ] && { echo "update-state.sh: --goal-dir required" >&2; exit 2; }
[ -f "${GOAL_DIR}/state.json" ] || { echo "update-state.sh: ${GOAL_DIR}/state.json not found" >&2; exit 2; }

# Crash-recovery guard: if state.json.tmp exists, a previous write crashed.
if [ -f "${GOAL_DIR}/state.json.tmp" ]; then
  echo "update-state.sh: ${GOAL_DIR}/state.json.tmp exists — previous write crashed." >&2
  echo "  manual recovery: rm '${GOAL_DIR}/state.json.tmp' (re-derive state from goal.yaml + iterations/ if needed)." >&2
  exit 3
fi

PYBIN="${HOME}/.claude/skills/.venv/bin/python3"
if [ ! -x "$PYBIN" ]; then PYBIN="$(command -v python3)"; fi

# Read the patch from stdin BEFORE invoking python (the heredoc consumes
# python's stdin for the program source, so we relay via env var).
PATCH_JSON="$(cat)"

GOAL_DIR="$GOAL_DIR" PATCH_JSON="$PATCH_JSON" "$PYBIN" - <<'PY'
import os, sys, json, datetime

goal_dir = os.environ["GOAL_DIR"]
state_path = os.path.join(goal_dir, "state.json")
tmp_path   = state_path + ".tmp"

with open(state_path) as f:
    state = json.load(f)

patch = json.loads(os.environ["PATCH_JSON"])

# RFC 7396 JSON Merge Patch (simplified — top-level only for v0.1):
# - patch[k] = null  → remove key (set to null in our schema)
# - patch[k] = value → set
# - nested dicts: recursive merge (only one level — budgets_consumed,
#   last_action_result).
def merge(target, patch):
    if not isinstance(patch, dict):
        return patch
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(target.get(k), dict):
            merge(target[k], v)
        else:
            target[k] = v
    return target

merge(state, patch)
state["updated_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Validate.
if state.get("version") != 1:
    print(f"update-state.sh: invalid version: {state.get('version')}", file=sys.stderr)
    sys.exit(4)
if state.get("terminal") not in (None, "done", "blocked", "abandoned"):
    print(f"update-state.sh: invalid terminal: {state.get('terminal')}", file=sys.stderr)
    sys.exit(4)

# Atomic write.
with open(tmp_path, "w") as f:
    json.dump(state, f, indent=2)
    f.write("\n")
os.replace(tmp_path, state_path)
PY
