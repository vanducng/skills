#!/usr/bin/env bash
# uninstall-stop-hook.sh — restore prior Stop hook config from hooks-backup.json
# and remove heartbeat. Leaves goal-state.json + logs intact for forensics.
#
# Usage: uninstall-stop-hook.sh <workspace-root>

set -euo pipefail

ws="${1:?workspace-root required}"
cd "$ws"

settings=".claude/settings.local.json"
heartbeat=".auto-loop/heartbeat.json"
backup=".auto-loop/hooks-backup.json"

if [[ ! -f "$settings" ]]; then
  rm -f "$heartbeat"
  echo "uninstall-stop-hook: no settings.local.json; heartbeat purged."
  exit 0
fi

if [[ -f "$backup" ]]; then
  prior=$(jq '.prior_stop' "$backup")
  if [[ "$prior" == "null" ]]; then
    new_settings=$(jq 'del(.hooks.Stop) | if (.hooks // {}) == {} then del(.hooks) else . end' "$settings")
  else
    new_settings=$(jq --argjson p "$prior" '.hooks.Stop = $p' "$settings")
  fi
  tmp=$(mktemp "${settings}.XXXXXX.tmp")
  printf '%s\n' "$new_settings" > "$tmp"
  mv -f "$tmp" "$settings"
fi

rm -f "$heartbeat"
echo "uninstall-stop-hook: restored prior Stop config; heartbeat purged."
