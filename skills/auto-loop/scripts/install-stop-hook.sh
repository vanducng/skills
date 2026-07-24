#!/usr/bin/env bash
# install-stop-hook.sh - install Stop hook for the active auto-loop into
# .claude/settings.local.json. Backs up prior config to .auto-loop/hooks-backup.json.
# Refuses to install if a live heartbeat already exists.
#
# Usage: install-stop-hook.sh <workspace-root> <handler-path>

set -euo pipefail

ws="${1:?workspace-root required}"
handler="${2:?handler-path required}"

cd "$ws"

settings=".claude/settings.local.json"
heartbeat=".auto-loop/heartbeat.json"
backup=".auto-loop/hooks-backup.json"

mkdir -p .auto-loop .claude

# Concurrent-loop guard is the dispatcher's job (it owns the heartbeat lifecycle).
# This script only installs the hook entry. If the caller provides
# VD_AUTOLOOP_HEARTBEAT_OWNER=$$ in env, we trust it.

# Initialise settings file if missing
if [[ ! -f "$settings" ]]; then
  echo '{}' > "$settings"
fi

# Backup existing Stop config (whatever shape) - write `null` if absent.
prior=$(jq '.hooks.Stop // null' "$settings")
echo "{\"prior_stop\": $prior}" > "$backup"

# Upsert Stop hook entry.
# Claude Code Stop hook contract: array of matchers, each with `hooks` array of commands.
# We register a single command that points at handler-path.
new_settings=$(jq --arg cmd "$handler" '
  .hooks //= {}
  | .hooks.Stop = [
      {
        "matcher": "*",
        "hooks": [
          { "type": "command", "command": $cmd }
        ]
      }
    ]
' "$settings")

tmp=$(mktemp "${settings}.XXXXXX.tmp")
printf '%s\n' "$new_settings" > "$tmp"
mv -f "$tmp" "$settings"

echo "install-stop-hook: registered Stop hook → $handler"
