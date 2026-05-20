#!/usr/bin/env bash
# DESTRUCTIVE: wipe the profile dir for <profile-name>. Asks for confirmation.
# Usage: profile-reset.sh <name> [--force]

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "$SCRIPT_DIR/_lib.sh"

NAME="$(require_name "${1:-}")"
FORCE="${2:-}"
DIR="$(profile_dir "$NAME")"

[[ -d "$DIR" ]] || die "profile '$NAME' does not exist at $DIR"

if is_open "$DIR"; then
  die "profile '$NAME' is currently open. Close it first: profile-close.sh $NAME"
fi

if [[ "$FORCE" != "--force" ]]; then
  read -r -p "WIPE everything in $DIR? (type the profile name to confirm) > " ans
  [[ "$ans" == "$NAME" ]] || die "aborted"
fi

rm -rf "$DIR"
info "wiped profile '$NAME'"
