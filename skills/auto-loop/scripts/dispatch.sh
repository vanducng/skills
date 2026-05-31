#!/usr/bin/env bash
# dispatch.sh — argument parser + flag router for vd:auto-loop.
#
# Recognised invocations:
#   vd:auto-loop                                   → print help, exit 0
#   vd:auto-loop <goal> --verify <cmd> [opts]      → start in-house loop
#   vd:auto-loop --goal-file <path> [opts]         → start from goal.md
#   vd:auto-loop --status                          → status-reader
#   vd:auto-loop --cancel                          → cancel-loop
#   vd:auto-loop --codex <goal> [--verify <cmd>]   → delegate to codex /goal
#
# Options:
#   --max-iterations N     (default 40)
#   --max-tokens T         (default 2000000)
#   --max-wallclock D      (default 4h)
#   --restart-pct N        (default 70)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
WS="${VD_AUTOLOOP_WORKSPACE:-$(pwd)}"

usage() {
  cat "$SKILL_DIR/references/usage.md"
}

if [[ $# -eq 0 ]]; then
  usage
  exit 0
fi

# --- Flag parse ---
goal=""
goal_file=""
verify=""
max_iter=40
max_tokens=2000000
max_wallclock="4h"
restart_pct=70
mode="run"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --status)        mode="status"; shift ;;
    --cancel)        mode="cancel"; shift ;;
    --codex)         mode="codex";  shift ;;
    --verify)        verify="${2:-}"; shift 2 ;;
    --goal-file)     goal_file="${2:-}"; shift 2 ;;
    --max-iterations) max_iter="${2:-40}"; shift 2 ;;
    --max-tokens)    max_tokens="${2:-2000000}"; shift 2 ;;
    --max-wallclock) max_wallclock="${2:-4h}"; shift 2 ;;
    --restart-pct)   restart_pct="${2:-70}"; shift 2 ;;
    -h|--help)       usage; exit 0 ;;
    --*)             echo "dispatch: unknown flag: $1" >&2; exit 2 ;;
    *)
      if [[ -z "$goal" ]]; then goal="$1"
      else                      goal="$goal $1"
      fi
      shift
      ;;
  esac
done

# --- Mutually exclusive flag check ---
case "$mode" in
  status) bash "$SCRIPT_DIR/status-reader.sh" "$WS"; exit $? ;;
  cancel) bash "$SCRIPT_DIR/cancel-loop.sh"   "$WS"; exit $? ;;
  codex)
    if [[ -n "$goal_file" ]]; then
      bash "$SCRIPT_DIR/delegate-to-codex.sh" "$WS" "$goal_file" "$verify"
    else
      bash "$SCRIPT_DIR/delegate-to-codex.sh" "$WS" "$goal" "$verify"
    fi
    exit $?
    ;;
esac

# --- run mode ---
if [[ -n "$goal_file" ]]; then
  if [[ ! -f "$goal_file" ]]; then
    echo "dispatch: goal-file not found: $goal_file" >&2
    exit 2
  fi
  # Source parsed defaults
  eval "$(bash "$SCRIPT_DIR/parse-goal-spec.sh" "$goal_file")"
  goal="$GOAL"
  [[ -z "$verify" ]] && verify="$VERIFY"
  max_iter="${MAX_ITERATIONS:-$max_iter}"
  max_tokens="${MAX_TOKENS:-$max_tokens}"
  max_wallclock="${MAX_WALLCLOCK:-$max_wallclock}"
  restart_pct="${RESTART_AT_CONTEXT_PCT:-$restart_pct}"
  allow="${ALLOW:-}"
  deny="${DENY:-}"
  max_restarts="${MAX_RESTARTS:-5}"
else
  allow=""
  deny=""
  max_restarts=5
fi

if [[ -z "$goal" || -z "$verify" ]]; then
  echo "dispatch: <goal> and --verify <cmd> are required (or use --goal-file)." >&2
  usage
  exit 2
fi

# --- Recursion guard ---
if [[ "${VD_AUTOLOOP_DEPTH:-0}" -gt 0 ]]; then
  echo "dispatch: refusing to start nested vd:auto-loop (VD_AUTOLOOP_DEPTH=${VD_AUTOLOOP_DEPTH})" >&2
  exit 4
fi

# --- Bootstrap state and heartbeat ---
state_dir="$WS/.auto-loop"
mkdir -p "$state_dir"

heartbeat="$state_dir/heartbeat.json"
state_file="$state_dir/goal-state.json"
now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
session_id="${CLAUDE_SESSION_ID:-${SHLVL}-$$}"
start_ref=$(git -C "$WS" rev-parse HEAD 2>/dev/null || echo "HEAD")

# Refuse if loop already live
if [[ -f "$heartbeat" ]]; then
  pid=$(jq -r '.pid // empty' "$heartbeat" 2>/dev/null || true)
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "dispatch: another vd:auto-loop is live (pid=$pid). --cancel first." >&2
    exit 3
  fi
  rm -f "$heartbeat"
fi

jq -n \
  --argjson pid "$$" \
  --arg sa "$now" \
  --arg sid "$session_id" \
  --arg gt "$goal" \
  --arg vf "$verify" \
  --argjson mi "$max_iter" \
  --argjson mt "$max_tokens" \
  --arg mw "$max_wallclock" \
  --argjson rp "$restart_pct" \
  --argjson mr "$max_restarts" \
  --arg al "$allow" \
  --arg dn "$deny" \
  --arg sr "$start_ref" \
  '{
    pid: $pid, started_at: $sa, session_id: $sid,
    goal_text: $gt, verify: $vf,
    max_iterations: $mi, max_tokens: $mt, max_wallclock: $mw,
    restart_at_context_pct: $rp, max_restarts: $mr,
    allow: $al, deny: $dn, start_ref: $sr
  }' > "$heartbeat"

# Seed state file (only if absent — preserve resume case)
if [[ ! -f "$state_file" ]]; then
  bash "$SCRIPT_DIR/state-rw.sh" seed "$state_file"
  # Stamp started_at + session_id
  current=$(cat "$state_file")
  stamped=$(printf '%s' "$current" | jq --arg sa "$now" --arg sid "$session_id" \
    '.started_at = $sa | .last_update = $sa | .session_id = $sid')
  bash "$SCRIPT_DIR/state-rw.sh" write "$state_file" "$stamped"
fi

# Install Stop hook
bash "$SCRIPT_DIR/install-stop-hook.sh" "$WS" "$SCRIPT_DIR/stop-hook-handler.sh"

cat <<EOF
vd:auto-loop started in $WS

  goal:     $goal
  verify:   $verify
  caps:     iter=$max_iter, tokens=$max_tokens, wallclock=$max_wallclock
  restart:  at $restart_pct% context, max $max_restarts restarts
  pid:      $$  session_id: $session_id

The Stop hook will re-feed each iteration's prompt until:
  - the two-vote completion gate opens (verifier + audit both vote achieved), OR
  - any hard cap fires (graceful drain), OR
  - --cancel is invoked.

Inspect: vd:auto-loop --status
Stop:    vd:auto-loop --cancel
EOF
