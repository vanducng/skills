#!/usr/bin/env bash
# kill.sh - mark a goal abandoned. Runtime-agnostic; safe to run from any shell.
#
# Usage:
#   kill.sh <goal-dir> --reason "<text>"
#
# Refuses to overwrite an existing terminal state (done/blocked/abandoned) - exit 3.

set -euo pipefail

GOAL_DIR="${1:?usage: kill.sh <goal-dir> --reason \"<text>\"}"
shift
REASON=""
while [ $# -gt 0 ]; do
  case "$1" in
    --reason) REASON="${2:?--reason requires arg}"; shift 2 ;;
    *) echo "kill.sh: unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -z "$REASON" ] && { echo "kill.sh: --reason is required" >&2; exit 2; }
[ -f "${GOAL_DIR}/state.json" ] || { echo "kill.sh: ${GOAL_DIR}/state.json not found" >&2; exit 2; }

CURRENT_TERMINAL="$("$(command -v python3)" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("terminal") or "")' "${GOAL_DIR}/state.json")"
if [ -n "$CURRENT_TERMINAL" ]; then
  echo "kill.sh: goal is already terminal (${CURRENT_TERMINAL}) - refusing to overwrite the recorded outcome." >&2
  exit 3
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf '{"terminal": "abandoned", "terminal_reason": %s}\n' \
  "$("$(command -v python3)" -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$REASON")" \
  | bash "$SCRIPT_DIR/update-state.sh" patch "$GOAL_DIR"

echo "kill.sh: ${GOAL_DIR} marked abandoned (${REASON})"
echo "kill.sh: if a vd:auto-loop is active for this goal, cancel it in its workspace with auto-loop's own cancel command (scripts/cancel-loop.sh); the conductor re-reads state.json each stage and stops on terminal."
