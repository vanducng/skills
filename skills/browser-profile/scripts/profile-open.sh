#!/usr/bin/env bash
# Launch headed Chrome for <profile-name>. Creates the user-data-dir on first run.
# Refuses to open if a SingletonLock already exists (use `attach` instead).

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "$SCRIPT_DIR/_lib.sh"

NAME="$(require_name "${1:-}")"
DIR="$(profile_dir "$NAME")"
PORT="$(port_for "$NAME")"

require_chrome

if is_open "$DIR"; then
  die "profile '$NAME' is already open (SingletonLock present). Use profile-attach.sh, or profile-close.sh first."
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

# Wait briefly for Chrome to bind the debug port (max 5s).
for i in 1 2 3 4 5 6 7 8 9 10; do
  if cdp_alive "$PORT"; then
    info "profile '$NAME' open · port=$PORT · pid=$PID · dir=$DIR"
    exit 0
  fi
  sleep 0.5
done

warn "profile launched but CDP endpoint on :$PORT not responding yet — check that Chrome opened correctly"
exit 0
