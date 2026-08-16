#!/usr/bin/env bash
# kill.sh - mark a goal abandoned. Runtime-agnostic; safe to run from any shell.
#
# Usage:
#   kill.sh <goal-dir> --reason "<text>"

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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf '{"terminal": "abandoned", "terminal_reason": %s}\n' \
  "$("$(command -v python3)" -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$REASON")" \
  | bash "$SCRIPT_DIR/update-state.sh" patch "$GOAL_DIR"

# Cancellation sentinel for any loop (vd:auto-loop) still watching this goal.
touch "${GOAL_DIR}/cancel.sentinel"
echo "kill.sh: ${GOAL_DIR} marked abandoned (${REASON})"
