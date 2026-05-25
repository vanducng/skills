#!/usr/bin/env bash
# status.sh — print a one-screen status summary for a pursue goal.
#
# Usage:
#   status.sh [--goal-dir <dir>]
#
# If --goal-dir omitted, auto-detects: scans CWD's plans/goals/*/ and picks
# the most recent with state.terminal=null. If none found, prints "no
# in-progress goal" and exits 4.
#
# Exit codes (scriptable):
#   0 = terminal=done
#   1 = terminal=blocked
#   2 = terminal=abandoned
#   3 = in-progress (terminal=null)
#   4 = no goal found
#   5 = error reading state

set -uo pipefail

GOAL_DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --goal-dir) GOAL_DIR="${2:-}"; shift 2 ;;
    --help|-h)  echo "usage: status.sh [--goal-dir <dir>]"; exit 0 ;;
    *) echo "status.sh: unknown arg: $1" >&2; exit 5 ;;
  esac
done

# Auto-detect: most recent plans/goals/*/ with terminal=null.
if [ -z "$GOAL_DIR" ]; then
  candidates=()
  for d in plans/goals/*/; do
    [ -d "$d" ] || continue
    if [ -f "$d/state.json" ]; then candidates+=("$d"); fi
  done
  if [ "${#candidates[@]}" -eq 0 ]; then
    echo "status.sh: no goal-dir found under ./plans/goals/" >&2
    exit 4
  fi
  # Sort by name (timestamp-prefix → most recent last).
  IFS=$'\n' SORTED=($(sort <<< "${candidates[*]}"))
  GOAL_DIR="${SORTED[-1]}"
fi

[ -f "${GOAL_DIR}/state.json" ] || { echo "status.sh: ${GOAL_DIR}/state.json not found" >&2; exit 5; }
[ -f "${GOAL_DIR}/goal.yaml" ]   || { echo "status.sh: ${GOAL_DIR}/goal.yaml not found"   >&2; exit 5; }

PYBIN="${HOME}/.claude/skills/.venv/bin/python3"; [ -x "$PYBIN" ] || PYBIN="$(command -v python3)"

GOAL_DIR="$GOAL_DIR" "$PYBIN" - <<'PY'
import os, json, yaml
gd = os.environ["GOAL_DIR"]
s = json.load(open(os.path.join(gd, "state.json")))
g = yaml.safe_load(open(os.path.join(gd, "goal.yaml")))

terminal = s.get("terminal")
mode_label = {"done":"DONE","blocked":"BLOCKED","abandoned":"ABANDONED",None:"in-progress"}.get(terminal,"unknown")
last = s.get("last_action_result") or {}

print(f"Goal:        {g.get('short_goal','')}")
print(f"Slug:        {g.get('slug','')}")
print(f"Mode:        {g.get('autonomy','semi')}")
print(f"Status:      {mode_label}{' at ' + (s.get('current_action') or '(intake-complete)') if not terminal else ''}")
b  = g.get('budgets') or {}
bc = s.get('budgets_consumed') or {}
print(f"Iterations:  {s.get('iteration_count',0)} / {b.get('max_iterations','?')}")
print(f"Budget used: rebases {bc.get('rebases',0)}/{b.get('max_rebases','?')}, "
      f"ci-reruns {bc.get('ci_reruns',0)}/{b.get('max_ci_reruns','?')}, "
      f"tokens ~{bc.get('token_pct',0)}%")
if last:
    print(f"Last action: {last.get('action','?')} → "
          f"{'verifier_pass' if last.get('verifier_pass') else 'verifier_fail'} "
          f"({last.get('verifier_evidence','')[:80]})")
    print(f"Last journal: {last.get('journal_entry','')}")
if s.get('terminal_reason'):
    print(f"Terminal reason: {s.get('terminal_reason')}")
PY

# Exit code per terminal state.
T="$("$PYBIN" -c "import json; print(json.load(open('${GOAL_DIR}/state.json')).get('terminal') or 'null')")"
case "$T" in
  done)      exit 0 ;;
  blocked)   exit 1 ;;
  abandoned) exit 2 ;;
  null)      exit 3 ;;
  *)         exit 5 ;;
esac
