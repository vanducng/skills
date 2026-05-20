#!/usr/bin/env bash
# Point the `browse` daemon at <profile-name>'s already-running Chrome.
# Requires the `browse` CLI from the vd:browser skill.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "$SCRIPT_DIR/_lib.sh"

NAME="$(require_name "${1:-}")"
DIR="$(profile_dir "$NAME")"
PORT="$(port_for "$NAME")"

command -v browse >/dev/null 2>&1 || die "'browse' CLI not on PATH. Install: npm i -g @browserbasehq/browse-cli"

if ! cdp_alive "$PORT"; then
  if [[ ! -d "$DIR" ]]; then
    die "profile '$NAME' does not exist. Create it with: profile-open.sh $NAME"
  fi
  die "no CDP endpoint on :$PORT. The profile isn't running — start it with: profile-open.sh $NAME"
fi

info "attaching browse to '$NAME' on :$PORT"
exec browse env local "$PORT"
