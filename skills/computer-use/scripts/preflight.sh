#!/usr/bin/env bash
# Read-only: report which desktop driver works in this shell and what is missing.
set -euo pipefail

say() { printf '%-26s %s\n' "$1" "$2"; }
has() { command -v "$1" >/dev/null 2>&1; }

os=$(uname -s)
say os "$os"

if has agent-desktop; then
  say agent-desktop "$(agent-desktop version 2>/dev/null | sed -n 's/.*"version":"\([0-9][^"]*\)".*/\1/p' | tail -1)"
else
  say agent-desktop "missing - install: brew install agent-desktop  (or npm install -g agent-desktop)"
fi

case "$os" in
  Darwin)
    say macos "$(sw_vers -productVersion)"
    say launcher "${TERM_PROGRAM:-unknown}${__CFBundleIdentifier:+ ($__CFBundleIdentifier)}"
    [[ -n "${SSH_CONNECTION:-}" ]] && say ssh "yes - Accessibility is granted to sshd-keygen-wrapper, not your terminal"
    [[ -n "${TMUX:-}" ]] && say tmux "yes - trust 'agent-desktop permissions', not the terminal name"
    fallbacks="cliclick screencapture osascript shortcuts peekaboo"
    ;;
  Linux)
    uid=$(id -u)
    run="/run/user/$uid"
    for v in XDG_SESSION_TYPE WAYLAND_DISPLAY DISPLAY XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS; do
      say "$v" "${!v:-unset}"
    done
    if [[ -z "${DBUS_SESSION_BUS_ADDRESS:-}" || ( -z "${WAYLAND_DISPLAY:-}" && -z "${DISPLAY:-}" ) ]]; then
      if [[ -S "$run/bus" ]]; then
        echo "# not in the graphical session (SSH or cron?). Join the logged-in session:"
        echo "export XDG_RUNTIME_DIR=$run"
        echo "export DBUS_SESSION_BUS_ADDRESS=unix:path=$run/bus"
        way=$(find "$run" -maxdepth 1 -name 'wayland-[0-9]*' -type s 2>/dev/null | head -1)
        x11=$(find /tmp/.X11-unix -maxdepth 1 -name 'X[0-9]*' 2>/dev/null | head -1)
        [[ -n "$way" ]] && echo "export WAYLAND_DISPLAY=${way##*/}"
        [[ -n "$x11" ]] && echo "export DISPLAY=:${x11##*/X}"
      else
        echo "# no session bus at $run/bus: $(id -un) has no graphical login on this machine - log in on the screen first"
      fi
    fi
    fallbacks="xdotool ydotool grim gnome-screenshot wl-copy xclip"
    ;;
  *) fallbacks="" ;;
esac

if has agent-desktop; then
  STATUS=$(agent-desktop status 2>/dev/null || true) python3 - <<'PY' || say status "unreadable"
import json, os
d = json.loads(os.environ["STATUS"])
row = lambda k, v: print(f"{k:26} {v}")
if not d.get("ok"):
    e = d.get("error") or {}
    row("status", f"error {e.get('code')}: {e.get('message')}")
else:
    for k, v in (d["data"].get("permissions") or {}).items():
        row(k, v.get("state"))
    s = d["data"].get("supported_surfaces") or []
    row("supported_surfaces", f"{len(s)}" + ("  <- empty: accessibility bus unreachable" if not s else ""))
PY
fi

found=""
for t in $fallbacks; do has "$t" && found+="$t "; done
say fallback-tools "${found:-none}"
