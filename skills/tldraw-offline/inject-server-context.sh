#!/bin/sh
# <!-- installed-by:tldraw-desktop-agent-skills -->
# Injects the running tldraw desktop canvas server context for agents.
event="${1:-SubagentStart}"
server_json=${TLDRAW_STATE_FILE:-"$HOME/Library/Application Support/tldraw/server.json"}

command -v jq >/dev/null 2>&1 || exit 0
[ -f "$server_json" ] || exit 0

port=$(jq -r '.port // empty' "$server_json" 2>/dev/null) || exit 0
token=$(jq -r '.token // empty' "$server_json" 2>/dev/null) || exit 0
[ -n "$port" ] && [ -n "$token" ] || exit 0
case "$port" in *[!0-9]*) exit 0 ;; esac
[ "$port" -ge 1 ] && [ "$port" -le 65535 ] || exit 0

context="The tldraw desktop canvas server is running at http://localhost:$port. Use the installed tq helper for authenticated requests; it reads the per-launch token without exposing it in agent context."

# Snapshot the open documents so the agent starts knowing what canvases exist.
# Best-effort: a dead server, missing curl, or a slow response must not delay
# or fail the subagent launch.
docs=""
if command -v curl >/dev/null 2>&1; then
  docs=$(printf 'authorization: Bearer %s\n' "$token" | curl -s --max-time 2 -X POST "http://localhost:$port/api/search" \
    -H 'content-type: text/plain' \
    -H @- \
    --data-binary 'return await api.getDocs()' 2>/dev/null | jq -c '.result // empty' 2>/dev/null)
fi

if [ -n "$docs" ] && [ "$docs" != "[]" ]; then
  context="$context

The user's currently open tldraw offline canvases (most-recently-active first): $docs"
fi

jq -n --arg event "$event" --arg context "$context" \
  '{hookSpecificOutput: {hookEventName: $event, additionalContext: $context}}'
