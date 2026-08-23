#!/usr/bin/env bash
# kill.sh - mark a ultracook goal abandoned.
#
# Refuses to overwrite an already-terminal state (done/blocked/abandoned).
# Does not write a cancel.sentinel - auto-loop has its own cancel.
#
# Usage: kill.sh --goal-dir <dir> --reason "<text>"
#
# Stdout: JSON {"abandoned": true|false, ...}
# Exit: 0 abandoned · 2 usage · 3 already terminal · 4 flip failed
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
. "${SCRIPT_DIR}/lib.sh"

GOAL_DIR=""
REASON=""
while [ $# -gt 0 ]; do
  case "$1" in
    --goal-dir) GOAL_DIR="${2:-}"; shift 2 ;;
    --reason)   REASON="${2:-}"; shift 2 ;;
    --help|-h)  echo "usage: kill.sh --goal-dir <dir> --reason <text>"; exit 0 ;;
    *) echo "kill.sh: unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -n "$GOAL_DIR" ] || { echo "kill.sh: --goal-dir required" >&2; exit 2; }
[ -n "$REASON" ] || REASON="user-requested kill"
[ -f "${GOAL_DIR}/state.json" ] || { echo "kill.sh: ${GOAL_DIR}/state.json not found" >&2; exit 2; }

PYBIN="$(_uc_python)"

CURRENT_TERMINAL="$("$PYBIN" -c "import json; print(json.load(open('${GOAL_DIR}/state.json')).get('terminal') or 'null')")"
if [ "$CURRENT_TERMINAL" != "null" ]; then
  echo "kill.sh: already terminal ($CURRENT_TERMINAL); refusing to clobber" >&2
  printf '{"abandoned": false, "already_terminal": "%s"}\n' "$CURRENT_TERMINAL"
  exit 3
fi

REASON_JSON="$("$PYBIN" -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$REASON")"

NEEDS_CANCEL="false"
AUTOLOOP_DIR="null"
MARKER="${GOAL_DIR}/.ultracook/delegated-to-auto-loop.json"
if [ -f "$MARKER" ]; then
  NEEDS_CANCEL="true"
  AUTOLOOP_DIR="\"$(dirname "$GOAL_DIR")/.auto-loop\""
  echo "kill.sh: goal was delegated to vd:auto-loop - cancel that loop before relying on this abandon." >&2
fi

if ! printf '{"terminal": "abandoned", "terminal_reason": %s}\n' "$REASON_JSON" \
  | bash "${SCRIPT_DIR}/update-state.sh" --goal-dir "$GOAL_DIR" >/dev/null; then
  echo "kill.sh: terminal flip failed" >&2
  printf '{"abandoned": false, "flip_failed": true, "reason": %s}\n' "$REASON_JSON"
  exit 4
fi

printf '{"abandoned": true, "needs_auto_loop_cancel": %s, "auto_loop_state_dir": %s, "reason": %s}\n' \
  "$NEEDS_CANCEL" "$AUTOLOOP_DIR" "$REASON_JSON"
