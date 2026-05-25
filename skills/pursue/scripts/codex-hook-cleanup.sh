#!/usr/bin/env bash
# codex-hook-cleanup.sh — SessionStart hook handler. Sweeps stale Monitor
# spec/log files from completed (or crashed) pursue runs.
#
# Triggered by Codex's SessionStart hook event. Reads payload from stdin
# (we only use it for forensic logging — the cleanup itself is filesystem-
# wide). Removes `iterations/*-monitor.spec.json` files older than 24h
# whose matching `.result.json` doesn't exist (i.e. pursue died mid-wait).
#
# Stdin: SessionStart hook JSON payload (ignored apart from logging).
# Stdout: optional {systemMessage: "..."} for the user; empty by default.
# Exit: 0 always (cleanup errors must not break the session).

set -uo pipefail

LOG="$HOME/.pursue/cleanup.log"
mkdir -p "$(dirname "$LOG")"

# Sweep spec files older than 24h that have NO matching .result.json.
# Find runs across the user's home + common worktree locations.
SEARCH_ROOTS=("$HOME/git" "$HOME/Projects" "$HOME/Code" "$PWD")
COUNT=0

for root in "${SEARCH_ROOTS[@]}"; do
  [ -d "$root" ] || continue
  while IFS= read -r spec; do
    [ -n "$spec" ] || continue
    result="${spec%.spec.json}.result.json"
    # Only sweep when no result.json exists (i.e. pursue died mid-wait).
    if [ ! -f "$result" ]; then
      echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) sweeping stale spec: $spec" >> "$LOG"
      rm -f "$spec" "${spec%.spec.json}.log"
      COUNT=$((COUNT + 1))
    fi
  done < <(find "$root" -path '*/iterations/*-monitor.spec.json' -type f -mtime +1 2>/dev/null)
done

if [ "$COUNT" -gt 0 ]; then
  # Optional: surface to user via systemMessage.
  printf '{"hookSpecificOutput":{"systemMessage":"vd:pursue cleanup: swept %d stale monitor spec(s) from prior runs"}}\n' "$COUNT"
else
  echo '{}'
fi
exit 0
