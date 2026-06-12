#!/usr/bin/env bash
# List all browser profiles with status (open/closed), deterministic port, and disk size.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "$SCRIPT_DIR/_lib.sh"

if [[ ! -d "$PROFILES_ROOT" ]]; then
  info "no profiles yet · root=$PROFILES_ROOT"
  exit 0
fi

printf "%-25s  %-7s  %-5s  %-8s  %s\n" "NAME" "STATUS" "PORT" "SIZE" "DIR"
printf "%-25s  %-7s  %-5s  %-8s  %s\n" "----" "------" "----" "----" "---"

shopt -s nullglob
for d in "$PROFILES_ROOT"/*/; do
  name="$(basename "$d")"
  port="$(port_for "$name")"
  status="closed"
  if is_open "$d"; then
    status="open"
    cdp_alive "$port" || status="no-cdp"
  elif lock_present "$d"; then
    status="stale"
  fi
  size="$(du -sh "$d" 2>/dev/null | awk '{print $1}')"
  printf "%-25s  %-7s  %-5s  %-8s  %s\n" "$name" "$status" "$port" "$size" "$d"
done
