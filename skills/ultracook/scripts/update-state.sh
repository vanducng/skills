#!/usr/bin/env bash
# update-state.sh - create or atomically patch a v2 ultracook state.json.
#
# Usage:
#   update-state.sh --init --goal-dir <dir>   # stdin is a full state object
#   update-state.sh --goal-dir <dir>          # stdin is a JSON merge patch
#
# --init creates <dir>/state.json (dir is created if missing).
# Merge patch uses RFC 7396 at the top level; nested dicts merge one level;
# a JSON null clears a key (set to null). The stages array is replaced when
# present in the patch (not merged by index).
#
# updated_at is always set to now (UTC).
# Validates version=2, terminal, and stage statuses.
#
# Exit: 0 ok · 2 usage · 3 crashed prior write (state.json.tmp) · 4 invalid state
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
. "${SCRIPT_DIR}/lib.sh"

GOAL_DIR=""
INIT=0
while [ $# -gt 0 ]; do
  case "$1" in
    --goal-dir) GOAL_DIR="${2:?--goal-dir requires arg}"; shift 2 ;;
    --init)     INIT=1; shift ;;
    --help|-h)
      echo "usage: update-state.sh [--init] --goal-dir <dir>  (JSON on stdin)"
      exit 0
      ;;
    *) echo "update-state.sh: unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -n "$GOAL_DIR" ] || { echo "update-state.sh: --goal-dir required" >&2; exit 2; }

if [ "$INIT" -eq 1 ]; then
  mkdir -p "$GOAL_DIR"
else
  [ -f "${GOAL_DIR}/state.json" ] || { echo "update-state.sh: ${GOAL_DIR}/state.json not found" >&2; exit 2; }
fi

if [ -f "${GOAL_DIR}/state.json.tmp" ]; then
  echo "update-state.sh: ${GOAL_DIR}/state.json.tmp exists - previous write crashed." >&2
  echo "  recover: rm '${GOAL_DIR}/state.json.tmp' and re-derive from the last good state.json." >&2
  exit 3
fi

PYBIN="$(_uc_python)"
PATCH_JSON="$(cat)"
export GOAL_DIR PATCH_JSON INIT

"$PYBIN" - <<'PY'
import os, sys, json, datetime

goal_dir = os.environ["GOAL_DIR"]
state_path = os.path.join(goal_dir, "state.json")
tmp_path = state_path + ".tmp"
init = os.environ.get("INIT") == "1"
patch = json.loads(os.environ["PATCH_JSON"])

if not isinstance(patch, dict):
    print("update-state.sh: stdin must be a JSON object", file=sys.stderr)
    sys.exit(4)

if init:
    state = dict(patch)
else:
    with open(state_path) as f:
        state = json.load(f)

    def merge(target, src):
        if not isinstance(src, dict):
            return src
        for k, v in src.items():
            if k == "stages":
                target[k] = v
            elif isinstance(v, dict) and isinstance(target.get(k), dict):
                merge(target[k], v)
            else:
                target[k] = v
        return target

    merge(state, patch)

state["updated_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
if init and "created_at" not in state:
    state["created_at"] = state["updated_at"]

ALLOWED_TERMINAL = (None, "done", "blocked", "abandoned")
ALLOWED_STATUS = ("pending", "in_progress", "done", "skipped")

if state.get("version") != 2:
    print(f"update-state.sh: invalid version: {state.get('version')}", file=sys.stderr)
    sys.exit(4)
if state.get("terminal") not in ALLOWED_TERMINAL:
    print(f"update-state.sh: invalid terminal: {state.get('terminal')}", file=sys.stderr)
    sys.exit(4)

stages = state.get("stages")
if stages is None:
    stages = []
    state["stages"] = stages
if not isinstance(stages, list):
    print("update-state.sh: stages must be a list", file=sys.stderr)
    sys.exit(4)

ids = []
for i, st in enumerate(stages):
    if not isinstance(st, dict):
        print(f"update-state.sh: stages[{i}] must be an object", file=sys.stderr)
        sys.exit(4)
    for req in ("id", "skill", "done_when", "status"):
        if not st.get(req):
            print(f"update-state.sh: stages[{i}] missing {req}", file=sys.stderr)
            sys.exit(4)
    if st["status"] not in ALLOWED_STATUS:
        print(f"update-state.sh: stages[{i}] invalid status: {st['status']}", file=sys.stderr)
        sys.exit(4)
    ids.append(st["id"])

current = state.get("current_stage")
if current not in (None, "") and current not in ids:
    print(f"update-state.sh: current_stage {current!r} is not a stage id", file=sys.stderr)
    sys.exit(4)

with open(tmp_path, "w") as f:
    json.dump(state, f, indent=2, sort_keys=False)
    f.write("\n")
os.replace(tmp_path, state_path)
print(state_path)
PY
