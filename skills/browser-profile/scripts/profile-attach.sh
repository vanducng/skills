#!/usr/bin/env bash
# Attach the agent-browser daemon to <profile-name>'s already-running Chrome over CDP.
# Requires the agent-browser CLI (vd:agent-browser skill).

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "$SCRIPT_DIR/_lib.sh"

NAME="$(require_name "${1:-}")"
DIR="$(profile_dir "$NAME")"
PORT="$(port_for "$NAME")"

command -v agent-browser >/dev/null 2>&1 || die "'agent-browser' CLI not on PATH. Install: npm install -g agent-browser (then one-time: agent-browser install)"

if ! cdp_alive "$PORT"; then
  if [[ ! -d "$DIR" ]]; then
    die "profile '$NAME' does not exist. Create it with: profile-open.sh $NAME"
  fi
  die "no CDP endpoint on :$PORT. The profile isn't running - start it with: profile-open.sh $NAME"
fi

info "attaching agent-browser to '$NAME' on :$PORT"
# The daemon may hold a stale session from a prior invocation; reset before connect.
env -u AGENT_BROWSER_PROFILE agent-browser close --all >/dev/null 2>&1 || true
env -u AGENT_BROWSER_PROFILE agent-browser connect "$PORT"

UA="$(env -u AGENT_BROWSER_PROFILE agent-browser eval 'navigator.userAgent' 2>/dev/null || true)"
if [[ -z "$UA" || "$UA" == *HeadlessChrome* ]]; then
  die "attached to the wrong browser (UA: ${UA:-empty}). An exported AGENT_BROWSER_PROFILE env var makes agent-browser silently launch its own headless profile browser instead of connecting to :$PORT. Fix: unset AGENT_BROWSER_PROFILE in your shell, then rerun: profile-attach.sh $NAME"
fi
info "attached to '$NAME' ($UA)"
