#!/usr/bin/env bash
# status-reader.sh - READ-ONLY snapshot of the active loop. Never writes any file.
#
# Usage: status-reader.sh <workspace>
# Stdout: human-readable 1-screen summary
# Exit code: 0 if pursuing/achieved; 1 if blocked/budget-limited/cancelled; 2 if no loop.

set -uo pipefail

ws="${1:?workspace required}"
cd "$ws"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_state-dir.sh"
state_file="$state_dir/goal-state.json"
heartbeat="$state_dir/heartbeat.json"
gate_log="$state_dir/gate-history.jsonl"
restart_log="$state_dir/restart-history.jsonl"

if [[ ! -f "$state_file" ]]; then
  echo "no active vd:auto-loop in this workspace ($ws)"
  exit 2
fi

iter=$(jq -r '.iteration // 0' "$state_file")
status=$(jq -r '.status // "pursuing"' "$state_file")
na=$(jq -r '.next_action // ""' "$state_file")
vr=$(jq -r '.verifier_result // "not-run"' "$state_file")
av=$(jq -r '.audit_vote // "not-run"' "$state_file")
started=$(jq -r '.started_at // ""' "$state_file")
restart_count=$(jq -r '.restart_count // 0' "$state_file")

goal=""
max_iter=40
max_wallclock="4h"
pid=""
pid_alive="dead"
if [[ -f "$heartbeat" ]]; then
  goal=$(jq -r '.goal_text // ""' "$heartbeat")
  max_iter=$(jq -r '.max_iterations // 40' "$heartbeat")
  max_wallclock=$(jq -r '.max_wallclock // "4h"' "$heartbeat")
  pid=$(jq -r '.pid // empty' "$heartbeat")
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    pid_alive="alive"
  fi
fi

now_epoch=$(date -u +"%s")
elapsed_h="?"
if [[ -n "$started" ]]; then
  s_epoch=$(date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$started" "+%s" 2>/dev/null || \
            date -u -d "$started" "+%s" 2>/dev/null || echo "$now_epoch")
  el=$((now_epoch - s_epoch))
  elapsed_h=$(printf '%dh%dm' $((el/3600)) $(((el%3600)/60)))
fi

probe=$(bash "$SCRIPT_DIR/probe-token-usage.sh" "$iter" "$ws" 2>/dev/null || echo '{"tokens_used":0,"source":"unknown","fidelity":"fallback"}')
tokens_used=$(printf '%s' "$probe" | jq -r '.tokens_used // 0')
src=$(printf '%s' "$probe" | jq -r '.source // "unknown"')

cat <<EOF
vd:auto-loop status - workspace: $ws
─────────────────────────────────────────────────────────────────────
Goal: $goal
Status: $status
Iteration: $iter / $max_iter
Wallclock: $elapsed_h / $max_wallclock
Tokens: $tokens_used (source: $src)
Verifier: $vr
Audit: $av
Restarts: $restart_count
PID: ${pid:-unknown} ($pid_alive)
Last action: $na
EOF

if [[ -f "$gate_log" ]]; then
  echo
  echo "Recent gate decisions (last 5):"
  tail -n 5 "$gate_log" | sed 's/^/  /'
fi

if [[ -f "$restart_log" ]]; then
  echo
  echo "Recent restarts (last 3):"
  tail -n 3 "$restart_log" | sed 's/^/  /'
fi

case "$status" in
  pursuing|achieved) exit 0 ;;
  *)                 exit 1 ;;
esac
