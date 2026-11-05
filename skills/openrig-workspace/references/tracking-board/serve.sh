#!/usr/bin/env bash
# Serve every board on the tailnet at /boards (tailnet only, never Funnel). Idempotent.
#   OPENRIG_BOARDS_ROOT  default ~/.share/openrig/boards
#   OPENRIG_BOARDS_PORT  loopback port of the board server, default 47320
# server.cjs holds the files, the feedback endpoint and live events on loopback; `tailscale serve` proxies
# /boards to it (the macOS Tailscale app cannot serve a directory itself). The tailnet URL does not load from
# the serving machine; check there with http://127.0.0.1:$PORT/<org>/<project>/<slug>/.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="${OPENRIG_BOARDS_ROOT:-$HOME/.share/openrig/boards}"
port="${OPENRIG_BOARDS_PORT:-47320}"
ts="$(command -v tailscale || echo /Applications/Tailscale.app/Contents/MacOS/Tailscale)"
mkdir -p "$root"

pid="$(lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -1 || true)"
if [ -n "$pid" ] && ps -o command= -p "$pid" | grep -q "server.cjs"; then
  echo "serve: board server already on 127.0.0.1:$port"
else
  [ -n "$pid" ] && { echo "serve: port $port held by: $(ps -o command= -p "$pid")"; echo "serve: stop it, or set OPENRIG_BOARDS_PORT"; exit 1; }
  OPENRIG_BOARDS_ROOT="$root" OPENRIG_BOARDS_PORT="$port" nohup node "$here/server.cjs" >"${TMPDIR:-/tmp}/openrig-boards.log" 2>&1 &
  sleep 1
  echo "serve: started board server on 127.0.0.1:$port for $root"
fi

"$ts" serve --bg --set-path=/boards "http://127.0.0.1:$port" >/dev/null
host="$("$ts" status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
echo "https://$host/boards/"
