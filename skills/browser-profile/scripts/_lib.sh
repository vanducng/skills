#!/usr/bin/env bash
# Shared helpers for browser-profile scripts.
# Source-only; do not exec directly.

set -euo pipefail

PROFILES_ROOT="${BROWSER_PROFILE_ROOT:-$HOME/.claude/browser-profiles}"
CHROME_BIN="${BROWSER_PROFILE_CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
PORT_BASE=9300
PORT_RANGE=100

die() { echo "error: $*" >&2; exit 1; }
warn() { echo "warn: $*" >&2; }
info() { echo "$*" >&2; }

require_name() {
  local name="${1:-}"
  [[ -n "$name" ]] || die "usage: $(basename "$0") <profile-name>"
  [[ "$name" =~ ^[a-z][a-z0-9-]*$ ]] || die "name must be kebab-case (lowercase, digits, hyphens; starts with letter): $name"
  echo "$name"
}

profile_dir() {
  echo "$PROFILES_ROOT/$1"
}

# Deterministic port from profile name. Pure function of name + PORT_BASE.
port_for() {
  local name="$1"
  local sum
  sum=$(echo -n "$name" | cksum | awk '{print $1}')
  echo $((PORT_BASE + sum % PORT_RANGE))
}

is_open() {
  local dir="$1"
  [[ -f "$dir/SingletonLock" ]]
}

cdp_alive() {
  local port="$1"
  curl -s --max-time 1 "http://localhost:$port/json/version" >/dev/null 2>&1
}

pid_file() {
  echo "$(profile_dir "$1")/.browser-profile.pid"
}

require_chrome() {
  [[ -x "$CHROME_BIN" ]] || die "Chrome not found at: $CHROME_BIN (override with BROWSER_PROFILE_CHROME)"
}
