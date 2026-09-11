#!/usr/bin/env bash
# Launch headed Chrome for <profile-name>. Creates the user-data-dir on first run.
# Refuses to open if a live Chrome already owns the profile (use `attach` instead).
# Stale locks from crashed/dead sessions are cleared automatically.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "$SCRIPT_DIR/_lib.sh"

NAME="$(require_name "${1:-}")"
DIR="$(profile_dir "$NAME")"
PORT="$(port_for "$NAME")"

require_chrome

if is_open "$DIR"; then
  die "profile '$NAME' is already open (pid $(lock_pid "$DIR")). Use profile-attach.sh, or profile-close.sh first."
fi

if lock_present "$DIR"; then
  warn "clearing stale SingletonLock left by dead Chrome (pid $(lock_pid "$DIR" || echo '?'))"
  rm -f "$DIR/SingletonLock" "$DIR/SingletonCookie" "$DIR/SingletonSocket"
fi

# Ports are hash-derived, so another profile can already own this port. Chrome
# silently keeps running without CDP when the port is taken, and a live check
# would answer from the OTHER profile's Chrome - so refuse before launching.
if cdp_alive "$PORT"; then
  die "port :$PORT is already serving CDP - another profile (hash collision) or process owns it. Rename this profile (e.g., add a '-2' suffix)."
fi

if [[ ! -d "$DIR" ]]; then
  info "creating new profile dir: $DIR"
  mkdir -p "$DIR"
  chmod 700 "$DIR"
fi

# Launch detached so the script returns immediately.
# --no-first-run: skip the "set as default browser" prompts.
# --no-default-browser-check: same.
# --disable-features=ChromeWhatsNewUI: skip the new-tab nag.
"$CHROME_BIN" \
  --user-data-dir="$DIR" \
  --remote-debugging-port="$PORT" \
  --no-first-run \
  --no-default-browser-check \
  --disable-features=ChromeWhatsNewUI \
  >/dev/null 2>&1 &
PID=$!
echo "$PID" > "$(pid_file "$NAME")"

# Wait for Chrome to bind the debug port (max 10s - cold starts are slow).
for _ in $(seq 1 20); do
  if cdp_alive "$PORT"; then
    info "profile '$NAME' open · port=$PORT · pid=$PID · dir=$DIR"
    exit 0
  fi
  sleep 0.5
done

die "profile launched (pid $PID) but the CDP endpoint on :$PORT never came up - Chrome may have failed to start or dropped the debug flag. Check the window, then retry or use profile-reset.sh."

