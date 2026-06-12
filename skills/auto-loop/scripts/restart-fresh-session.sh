#!/usr/bin/env bash
# restart-fresh-session.sh — invoked by the outer wrapper when stop-hook signals
# `restart needed`. Kills the current claude PID (per heartbeat), increments
# restart_count in goal-state.json, then re-launches `claude -p` with the
# compaction summary as the seed prompt. Anti-thrash: refuses to restart if
# restart_count >= max_restarts.
#
# Usage: restart-fresh-session.sh <workspace>

set -uo pipefail

ws="${1:?workspace required}"
cd "$ws"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_state-dir.sh"
state_file="$state_dir/goal-state.json"
heartbeat="$state_dir/heartbeat.json"

[[ -f "$state_file" && -f "$heartbeat" ]] || { echo "restart: no state/heartbeat" >&2; exit 1; }

restart_count=$(jq -r '.restart_count // 0' "$state_file")
max_restarts=$(jq -r '.max_restarts // 5' "$heartbeat")

if [[ "$restart_count" -ge "$max_restarts" ]]; then
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  new_state=$(jq --arg lu "$now" \
                 '.status = "budget-limited"
                  | .next_action = "excessive-restarts cap reached"
                  | .last_update = $lu' "$state_file")
  bash "$SCRIPT_DIR/state-rw.sh" write "$state_file" "$new_state"
  echo "restart: max_restarts ($max_restarts) reached; halting" >&2
  exit 2
fi

# Render compaction summary
summary_path=$(bash "$SCRIPT_DIR/write-compaction-summary.sh" "$ws")

# Increment restart counter
new_state=$(jq --argjson c "$((restart_count + 1))" '.restart_count = $c' "$state_file")
bash "$SCRIPT_DIR/state-rw.sh" write "$state_file" "$new_state"

# Mark prior PID as superseded; the outer wrapper does the actual respawn
old_pid=$(jq -r '.pid // empty' "$heartbeat")
if [[ -n "$old_pid" ]]; then
  jq --arg op "$old_pid" '.superseded_pid = $op | del(.pid)' "$heartbeat" > "${heartbeat}.tmp" \
    && mv -f "${heartbeat}.tmp" "$heartbeat"
fi

# Emit a marker for the outer wrapper to consume
jq -nc --arg p "$summary_path" \
       --arg ws "$ws" \
       '{action:"restart-needed", summary_path:$p, workspace:$ws}'
