#!/usr/bin/env bash
# should-gate.sh — decide whether the executor should gate on this action.
#
# Usage: should-gate.sh --mode <manual|semi|auto> --action <name> --phase-state <first|repeat>
# Exit:
#   0 = GATE (caller invokes AskUserQuestion)
#   1 = PROCEED (no gate)
#   2 = invalid input

set -o pipefail

MODE=""; ACTION=""; PHASE_STATE="first"
while [ $# -gt 0 ]; do
  case "$1" in
    --mode)        MODE="${2:-}"; shift 2 ;;
    --action)      ACTION="${2:-}"; shift 2 ;;
    --phase-state) PHASE_STATE="${2:-}"; shift 2 ;;
    --help|-h)     echo "usage: should-gate.sh --mode {manual|semi|auto} --action <name> --phase-state <first|repeat>"; exit 0 ;;
    *) echo "should-gate.sh: unknown arg: $1" >&2; exit 2 ;;
  esac
done

[ -z "$MODE" ]   && { echo "should-gate.sh: --mode required" >&2; exit 2; }
[ -z "$ACTION" ] && { echo "should-gate.sh: --action required" >&2; exit 2; }

case "$MODE" in
  manual) exit 0 ;;
  auto)   exit 1 ;;
  semi)
    # Semi gates on first-plan / ship / verify_smoke, OR if vocab marks `semi`.
    case "$ACTION" in
      plan)
        [ "$PHASE_STATE" = "first" ] && exit 0
        exit 1
        ;;
      ship|verify_smoke|brainstorm)
        # brainstorm is the design phase; semi gates the FIRST design call.
        exit 0
        ;;
      *)
        # Check action-vocab.yaml gate_default — does it include "semi"?
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        VOCAB="$(dirname "$SCRIPT_DIR")/references/action-vocab.yaml"
        PYBIN="${HOME}/.claude/skills/.venv/bin/python3"; [ -x "$PYBIN" ] || PYBIN="$(command -v python3)"
        gates="$("$PYBIN" - "$VOCAB" "$ACTION" <<'PY'
import sys, yaml
v = yaml.safe_load(open(sys.argv[1]))
a = v.get('actions', {}).get(sys.argv[2], {})
print(','.join(a.get('gate_default') or []))
PY
)"
        case ",$gates," in
          *,semi,*) exit 0 ;;
          *)        exit 1 ;;
        esac
        ;;
    esac
    ;;
  *)
    echo "should-gate.sh: invalid mode: $MODE" >&2
    exit 2
    ;;
esac
