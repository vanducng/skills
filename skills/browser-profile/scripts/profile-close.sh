#!/usr/bin/env bash
# Close the Chrome instance for <profile-name> and clear stale lock files.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "$SCRIPT_DIR/_lib.sh"

NAME="$(require_name "${1:-}")"
DIR="$(profile_dir "$NAME")"
[[ -d "$DIR" ]] || die "profile '$NAME' does not exist"

# Resolve the owning PID: pidfile when it still owns the dir, else the SingletonLock target
# (covers Chromes that took over the singleton and orphaned our pidfile).
# Capture both candidates ONCE - the lock can vanish mid-script and set -e would abort.
PIDFILE="$(pid_file "$NAME")"
PIDFILE_PID=""
[[ -f "$PIDFILE" ]] && PIDFILE_PID="$(cat "$PIDFILE" 2>/dev/null || true)"
LOCK_PID="$(lock_pid "$DIR" || true)"
PID=""
if [[ -n "$PIDFILE_PID" ]] && chrome_owns_dir "$PIDFILE_PID" "$DIR"; then
  PID="$PIDFILE_PID"
elif [[ -n "$LOCK_PID" ]] && chrome_owns_dir "$LOCK_PID" "$DIR"; then
  PID="$LOCK_PID"
fi

if [[ -n "$PID" ]]; then
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

# Clean singleton locks (dangling symlinks; rm -f handles both present and absent).
rm -f "$DIR/SingletonLock" "$DIR/SingletonCookie" "$DIR/SingletonSocket"

info "profile '$NAME' closed"
