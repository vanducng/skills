#!/usr/bin/env bash
# check-budget-caps.sh - enforce iter / token / wallclock caps.
#
# Sets goal-state.status=budget-limited if any cap is breached. Wallclock cap is
# the floor cap (always enforced). Token cap is advisory unless probe fidelity is
# `exact` or `approximate`.
#
# Usage: check-budget-caps.sh <workspace>
# Exit code:
#   0 = no cap breached
#   1 = cap breached (state updated, drain prompt should be next)
#
# Stdout (when breached): JSON `{"reason": "iterations|tokens|wallclock", "drain": true}`

set -uo pipefail

ws="${1:?workspace required}"
cd "$ws"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_state-dir.sh"
state_file="$state_dir/goal-state.json"
heartbeat="$state_dir/heartbeat.json"

[[ -f "$heartbeat" && -f "$state_file" ]] || exit 0

iter=$(jq -r '.iteration // 0' "$state_file")
# Wallclock anchor is the loop-start heartbeat, not the state file (state's
# started_at can be reset by seed; heartbeat is set once at dispatch).
started_at=$(jq -r '.started_at // empty' "$heartbeat")

max_iter=$(jq -r '.max_iterations // 40' "$heartbeat")
max_tokens=$(jq -r '.max_tokens // 2000000' "$heartbeat")
max_wallclock=$(jq -r '.max_wallclock // "4h"' "$heartbeat")

# Parse wallclock duration → seconds. Accepts: 30m, 2h, 4h30m, 90s.
parse_duration() {
  local s="$1" total=0 num="" unit=""
  while [[ -n "$s" ]]; do
    if [[ "$s" =~ ^([0-9]+)([smhd])(.*)$ ]]; then
      num="${BASH_REMATCH[1]}"
      unit="${BASH_REMATCH[2]}"
      s="${BASH_REMATCH[3]}"
      case "$unit" in
        s) total=$((total + num)) ;;
        m) total=$((total + num*60)) ;;
        h) total=$((total + num*3600)) ;;
        d) total=$((total + num*86400)) ;;
      esac
    else
      break
    fi
  done
  echo "$total"
}

max_wall_sec=$(parse_duration "$max_wallclock")
[[ "$max_wall_sec" -le 0 ]] && max_wall_sec=14400  # default 4h floor

now_epoch=$(date -u +"%s")
if [[ -n "$started_at" ]]; then
  s_epoch=$(date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$started_at" "+%s" 2>/dev/null || \
            date -u -d "$started_at" "+%s" 2>/dev/null || echo "$now_epoch")
else
  s_epoch="$now_epoch"
fi
elapsed=$((now_epoch - s_epoch))

# --- Iteration cap ---
if [[ "$iter" -ge "$max_iter" ]]; then
  reason="iterations"
  fire=1
fi

# --- Wallclock cap (FLOOR) ---
if [[ -z "${fire:-}" && "$elapsed" -ge "$max_wall_sec" ]]; then
  reason="wallclock"
  fire=1
fi

# --- Token cap (only if probe is reliable) ---
if [[ -z "${fire:-}" ]]; then
  probe=$(bash "$SCRIPT_DIR/probe-token-usage.sh" "$iter" "$ws" 2>/dev/null || true)
  fidelity=$(printf '%s' "$probe" | jq -r '.fidelity // "fallback"' 2>/dev/null || echo "fallback")
  tokens_used=$(printf '%s' "$probe" | jq -r '.tokens_used // 0' 2>/dev/null || echo 0)
  if [[ "$fidelity" != "fallback" && "$tokens_used" -ge "$max_tokens" ]]; then
    reason="tokens"
    fire=1
  fi
fi

if [[ -z "${fire:-}" ]]; then
  exit 0
fi

# Mark state budget-limited.
now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
new_state=$(jq --arg s "budget-limited" \
               --arg n "cap reached: $reason" \
               --arg lu "$now" \
               '.status = $s | .next_action = $n | .last_update = $lu' \
               "$state_file")
bash "$SCRIPT_DIR/state-rw.sh" write "$state_file" "$new_state"

jq -nc --arg r "$reason" '{reason: $r, drain: true}'
exit 1
