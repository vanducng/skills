#!/usr/bin/env bash
# cancel-loop.sh — terminate active loop, mark state cancelled, restore Stop hook.
# Idempotent: re-running with no live loop is a clean no-op.
#
# Usage: cancel-loop.sh <workspace>

set -uo pipefail

ws="${1:?workspace required}"
cd "$ws"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_state-dir.sh"
state_file="$state_dir/goal-state.json"
heartbeat="$state_dir/heartbeat.json"

if [[ ! -f "$state_file" && ! -f "$heartbeat" ]]; then
  echo "cancel-loop: no active loop in $ws"
  exit 0
fi

# 1. Mark state cancelled (best-effort; don't fail if state-rw rejects).
if [[ -f "$state_file" ]]; then
  iter=$(jq -r '.iteration // 0' "$state_file")
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  current=$(cat "$state_file")
  cancelled=$(printf '%s' "$current" | jq \
    --arg s "cancelled" \
    --arg n "cancelled by user at iter $iter" \
    --arg lu "$now" \
    '.status = $s | .next_action = $n | .last_update = $lu')
  bash "$SCRIPT_DIR/state-rw.sh" write "$state_file" "$cancelled" 2>/dev/null || \
    printf '%s\n' "$cancelled" > "$state_file"
fi

# 2. Send SIGTERM to the loop PID; escalate to SIGKILL after 5s.
if [[ -f "$heartbeat" ]]; then
  pid=$(jq -r '.pid // empty' "$heartbeat" 2>/dev/null || true)
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    kill -TERM "$pid" 2>/dev/null || true
    for _ in 1 2 3 4 5; do
      sleep 1
      if ! kill -0 "$pid" 2>/dev/null; then break; fi
    done
    if kill -0 "$pid" 2>/dev/null; then
      kill -KILL "$pid" 2>/dev/null || true
    fi
  fi
fi

# 3. Uninstall Stop hook (restores prior config).
bash "$SCRIPT_DIR/uninstall-stop-hook.sh" "$ws" >/dev/null 2>&1 || true

# 4. Print summary.
cat <<EOF
cancel-loop: loop cancelled in $ws

Working tree: untouched (any auto-loop commits remain — see git log for wip(auto-loop):).
Forensics preserved under .auto-loop/:
  goal-state.json     — final state
  gate-history.jsonl  — all gate decisions
  verifier-*.log      — per-iter verifier output
  audit-*.json        — per-iter audit votes

Re-run vd:auto-loop "<goal>" --verify "<cmd>" to start fresh.
EOF
