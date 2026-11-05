#!/usr/bin/env bash
# Serve the boards root on the tailnet at /boards (tailnet only, never Funnel). Idempotent.
#   OPENRIG_BOARDS_ROOT  default ~/.share/openrig/boards
#   OPENRIG_BOARDS_PORT  loopback port of the static server, default 47320
# The macOS Tailscale app cannot serve a directory, so a loopback python server holds the files and
# `tailscale serve` proxies /boards to it. The tailnet URL does not load from the serving machine
# itself; check there with http://127.0.0.1:$PORT/<org>/<project>/<slug>/ instead.
set -euo pipefail

root="${OPENRIG_BOARDS_ROOT:-$HOME/.share/openrig/boards}"
port="${OPENRIG_BOARDS_PORT:-47320}"
ts="$(command -v tailscale || echo /Applications/Tailscale.app/Contents/MacOS/Tailscale)"
mkdir -p "$root"

if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "serve: port $port already listening (expected: python http.server on $root)"
else
  nohup python3 -m http.server "$port" --bind 127.0.0.1 --directory "$root" >"${TMPDIR:-/tmp}/openrig-boards.log" 2>&1 &
  sleep 1
  echo "serve: started http.server on 127.0.0.1:$port for $root"
fi

"$ts" serve --bg --set-path=/boards "http://127.0.0.1:$port" >/dev/null
host="$("$ts" status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
echo "https://$host/boards/"
