#!/usr/bin/env bash
# Shared helpers for browser-profile scripts.
# Source-only; do not exec directly.

set -euo pipefail

PROFILES_ROOT="${BROWSER_PROFILE_ROOT:-$HOME/.claude/browser-profiles}"
PROFILES_ROOT="${PROFILES_ROOT%/}"
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

# SingletonLock is a dangling symlink to "<hostname>-<pid>"; -f/-e follow it and see nothing.
lock_present() {
  local dir="${1%/}"
  [[ -L "$dir/SingletonLock" || -e "$dir/SingletonLock" ]]
}

lock_pid() {
  local dir="${1%/}" target
  target="$(readlink "$dir/SingletonLock" 2>/dev/null || true)"
  [[ -n "$target" ]] && echo "${target##*-}"
}

chrome_owns_dir() {
  local pid="$1" dir="${2%/}" cmd
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  cmd="$(ps -p "$pid" -o command= 2>/dev/null)" || return 1
  # Exact-arg match: a substring test would let /x/app claim /x/app-2's Chrome.
  [[ "$cmd" == *"--user-data-dir=$dir "* || "$cmd" == *"--user-data-dir=$dir" ]]
}

is_open() {
  local dir="${1%/}"
  lock_present "$dir" || return 1
  chrome_owns_dir "$(lock_pid "$dir" || true)" "$dir"
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
