#!/usr/bin/env bash
# read-auto-loop-outcome.sh - read .auto-loop/goal-state.json once and emit
# the terminal status + reason as JSON. Used by SKILL.md AFTER vd:auto-loop
# returns synchronously (Skill tool call exits when auto-loop's Stop hook
# terminates), OR at session-resume time when {goal-dir}/.ultracook/delegated-
# to-auto-loop.json marker exists.
#
# Usage: read-auto-loop-outcome.sh --auto-loop-state <path/to/.auto-loop>
#
# Stdout: JSON {"status": "...", "reason": "...", "iterations": N,
#               "last_evidence": "...", "raw": {...}}
# Status values (from auto-loop's state-schema.json):
#   pursuing | achieved | unmet | blocked | budget-limited | cancelled

set -uo pipefail

AUTOLOOP_DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --auto-loop-state) AUTOLOOP_DIR="${2:-}"; shift 2 ;;
    *) echo "read-auto-loop-outcome.sh: unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -z "$AUTOLOOP_DIR" ] && { echo "--auto-loop-state required" >&2; exit 2; }
STATE="${AUTOLOOP_DIR}/goal-state.json"
[ -f "$STATE" ] || { echo "read-auto-loop-outcome.sh: $STATE not found" >&2; exit 2; }

PYBIN="${HOME}/.claude/skills/.venv/bin/python3"; [ -x "$PYBIN" ] || PYBIN="$(command -v python3)"

STATE="$STATE" "$PYBIN" - <<'PY'
import os, json
s = json.load(open(os.environ["STATE"]))
status = s.get("status", "unknown")
reason = s.get("reason") or s.get("status_reason") or ""
iters  = s.get("iterations") or s.get("iteration_count") or 0
last_ev = ""
# Last verifier evidence - auto-loop stores varying field names; try common.
for k in ("last_verifier_evidence", "last_evidence", "verifier_evidence"):
    if s.get(k):
        last_ev = s[k]; break
print(json.dumps({
    "status": status,
    "reason": reason,
    "iterations": iters,
    "last_evidence": last_ev,
    "raw": s,
}))
PY
