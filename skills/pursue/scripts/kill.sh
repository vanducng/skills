#!/usr/bin/env bash
# kill.sh — write state.terminal=abandoned for a pursue goal.
#
# If a .pursue/delegated-to-auto-loop.json marker exists, kill.sh ALSO emits
# a hint that SKILL.md should invoke /vd:auto-loop --cancel BEFORE marking
# abandoned (bash can't call Skill directly).
#
# Usage: kill.sh --goal-dir <dir> --reason "<text>"
#
# Stdout: JSON {"abandoned": true, "needs_auto_loop_cancel": bool, "auto_loop_state_dir": "<path or null>"}
# Exit: 0 on success, non-zero on error.

set -uo pipefail

GOAL_DIR=""; REASON=""
while [ $# -gt 0 ]; do
  case "$1" in
    --goal-dir) GOAL_DIR="${2:-}"; shift 2 ;;
    --reason)   REASON="${2:-}"; shift 2 ;;
    --help|-h)  echo "usage: kill.sh --goal-dir <dir> --reason <text>"; exit 0 ;;
    *) echo "kill.sh: unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -z "$GOAL_DIR" ] && { echo "--goal-dir required" >&2; exit 2; }
[ -z "$REASON" ]   && REASON="user-requested kill"
[ -f "${GOAL_DIR}/state.json" ] || { echo "${GOAL_DIR}/state.json not found" >&2; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYBIN="${HOME}/.claude/skills/.venv/bin/python3"; [ -x "$PYBIN" ] || PYBIN="$(command -v python3)"

# Check current terminal — refuse to clobber a non-null terminal.
CURRENT_TERMINAL="$("$PYBIN" -c "import json; print(json.load(open('${GOAL_DIR}/state.json')).get('terminal') or 'null')")"
if [ "$CURRENT_TERMINAL" != "null" ]; then
  echo "kill.sh: already terminal ($CURRENT_TERMINAL); refusing to clobber" >&2
  printf '{"abandoned": false, "already_terminal": "%s"}\n' "$CURRENT_TERMINAL"
  exit 3
fi

# Auto-loop marker check.
MARKER="${GOAL_DIR}/.pursue/delegated-to-auto-loop.json"
NEEDS_CANCEL="false"
AUTOLOOP_DIR="null"
if [ -f "$MARKER" ]; then
  NEEDS_CANCEL="true"
  # Auto-loop's state lives at CWD/.auto-loop when invoked (we assume invoker
  # CWD == goal worktree root, which Phase 5's delegate-to-auto-loop.sh expects).
  AUTOLOOP_DIR="\"$(dirname "$GOAL_DIR")/.auto-loop\""
fi

# Write final journal entry.
bash "${SCRIPT_DIR}/append-journal.sh" --goal-dir "$GOAL_DIR" --action killed \
  --exit-code 0 --verifier-pass null --verifier-evidence "killed: $REASON" >/dev/null

# Mark terminal=abandoned via update-state.sh.
REASON_ESC="$(printf '%s' "$REASON" | "$PYBIN" -c 'import json,sys; print(json.dumps(sys.stdin.read()))')"
printf '{"terminal": "abandoned", "terminal_reason": %s}\n' "$REASON_ESC" \
  | bash "${SCRIPT_DIR}/update-state.sh" --goal-dir "$GOAL_DIR"

# Emit hint for SKILL.md.
printf '{"abandoned": true, "needs_auto_loop_cancel": %s, "auto_loop_state_dir": %s, "reason": %s}\n' \
  "$NEEDS_CANCEL" "$AUTOLOOP_DIR" "$REASON_ESC"
