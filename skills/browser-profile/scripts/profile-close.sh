#!/usr/bin/env bash
# Close the Chrome instance for <profile-name> and clear stale lock files.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "$SCRIPT_DIR/_lib.sh"

NAME="$(require_name "${1:-}")"
DIR="$(profile_dir "$NAME")"
[[ -d "$DIR" ]] || die "profile '$NAME' does not exist"

PIDFILE="$(pid_file "$NAME")"
if [[ -f "$PIDFILE" ]]; then
  PID="$(cat "$PIDFILE")"
  if kill -0 "$PID" 2>/dev/null; then
    info "stopping Chrome pid=$PID"
    kill -TERM "$PID" || true
    # wait up to 5s for graceful exit
    for i in 1 2 3 4 5 6 7 8 9 10; do
      kill -0 "$PID" 2>/dev/null || break
      sleep 0.5
    done
    kill -0 "$PID" 2>/dev/null && { warn "Chrome did not exit; sending SIGKILL"; kill -KILL "$PID" || true; }
  fi
  rm -f "$PIDFILE"
fi

# Clean stale singleton lock if Chrome left it behind.
for f in SingletonLock SingletonCookie SingletonSocket; do
  [[ -e "$DIR/$f" ]] && rm -f "$DIR/$f"
done

info "profile '$NAME' closed"
