#!/usr/bin/env bash
# delegate-to-codex.sh — hand off goal-pursuit to native Codex `/goal`.
# Refuses if codex < 0.128.0 or auth missing. Defaults to --sandbox workspace-write.
#
# Usage: delegate-to-codex.sh <workspace> <goal-file-or-text> [verify-cmd]

set -uo pipefail

ws="${1:?workspace required}"
goal_arg="${2:?goal required}"
verify_cmd="${3:-}"

cd "$ws"

if ! command -v codex >/dev/null 2>&1; then
  echo "delegate-to-codex: codex CLI not installed (https://developers.openai.com/codex)" >&2
  exit 2
fi

ver_raw=$(codex --version 2>/dev/null | head -n1 || echo "")
ver=$(printf '%s' "$ver_raw" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1)

if [[ -z "$ver" ]]; then
  echo "delegate-to-codex: cannot parse codex version from: $ver_raw" >&2
  exit 2
fi

# semver compare against 0.128.0
ver_ge_128() {
  local v="$1"
  IFS=. read -r maj min pat <<< "$v"
  if [[ "$maj" -gt 0 ]]; then return 0; fi
  if [[ "$min" -gt 128 ]]; then return 0; fi
  if [[ "$min" -eq 128 && "$pat" -ge 0 ]]; then return 0; fi
  return 1
}

if ! ver_ge_128 "$ver"; then
  echo "delegate-to-codex: codex /goal requires 0.128.0+; you have $ver" >&2
  exit 2
fi

# Resolve goal text
if [[ -f "$goal_arg" ]]; then
  goal_text=$(awk '/^# Goal/{flag=1; next} /^# /{flag=0} flag' "$goal_arg" | sed '/^$/d' | head -c 4000)
else
  goal_text="$goal_arg"
fi

# Concurrent-loop guard
state_dir=".auto-loop"
heartbeat="$state_dir/heartbeat.json"
if [[ -f "$heartbeat" ]]; then
  pid=$(jq -r '.pid // empty' "$heartbeat" 2>/dev/null || true)
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "delegate-to-codex: another vd:auto-loop is live (pid=$pid). --cancel first." >&2
    exit 3
  fi
fi

cat <<EOF
delegate-to-codex: handing off to codex $ver

  goal:    $goal_text
  verify:  ${verify_cmd:-(none — set verify in goal.md)}
  sandbox: workspace-write

Launching codex... type:
  /goal $goal_text
inside the TUI to start. Use /goal status, /goal pause, /goal resume from there.

(See references/codex-delegation.md for limits and the danger-full-access opt-in.)
EOF

exec codex --sandbox workspace-write
