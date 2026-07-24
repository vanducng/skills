#!/usr/bin/env bash
# lookup-profile.sh - resolve the per-project profile for the current repo.
#
# Reads `git remote get-url origin`, matches against `remote_matches` arrays
# in skills/ultracook/projects/*.toml (excluding _default.toml), returns the
# matched profile path on stdout.
#
# Falls back to _default.toml if no specific profile matches.
# Exits non-zero with a diagnostic if multiple profiles match the same remote
# (ambiguous - author error).
#
# Usage: lookup-profile.sh [--remote-url <url>]   # url override for testing

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECTS_DIR="$(dirname "$SCRIPT_DIR")/projects"

# ── Arg parsing ───────────────────────────────────────────────────────────────

REMOTE_URL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --remote-url)
      REMOTE_URL="${2:-}"; shift 2 ;;
    --help|-h)
      echo "usage: lookup-profile.sh [--remote-url <url>]"; exit 0 ;;
    *)
      echo "lookup-profile.sh: unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$REMOTE_URL" ]; then
  if ! REMOTE_URL="$(git remote get-url origin 2>/dev/null)"; then
    echo "lookup-profile.sh: no origin remote and no --remote-url override" >&2
    echo "falling back to _default.toml"  >&2
    echo "${PROJECTS_DIR}/_default.toml"
    exit 0
  fi
fi

# ── Scan profiles, match against remote_matches arrays ────────────────────────
# TOML parsing without a library: grep-and-eyeball for the `remote_matches`
# array contents. Each profile lists its matches as quoted strings on
# subsequent lines until the closing `]`. We just substring-match.

matched=()
for profile in "$PROJECTS_DIR"/*.toml; do
  base="$(basename "$profile")"
  [ "$base" = "_default.toml" ] && continue

  # Extract the remote_matches array body (handle multi-line arrays).
  # We grab everything between `remote_matches = [` and the matching `]`.
  matches_block="$(awk '
    /^remote_matches[[:space:]]*=[[:space:]]*\[/ { capture=1; next }
    capture && /\]/                              { capture=0 }
    capture                                       { print }
  ' "$profile")"

  # For each quoted entry in the block, substring-test against REMOTE_URL.
  while IFS= read -r line; do
    # Strip leading/trailing whitespace + comma + comment.
    pattern="$(printf '%s' "$line" | sed -E 's/^[[:space:]]*"//; s/"[[:space:]]*,?[[:space:]]*(#.*)?$//' )"
    [ -z "$pattern" ] && continue
    if printf '%s' "$REMOTE_URL" | grep -qF -- "$pattern"; then
      matched+=("$profile")
      break   # one match per profile is enough
    fi
  done <<< "$matches_block"
done

# ── Resolve ───────────────────────────────────────────────────────────────────

case ${#matched[@]} in
  0)
    echo "${PROJECTS_DIR}/_default.toml"
    ;;
  1)
    echo "${matched[0]}"
    ;;
  *)
    echo "lookup-profile.sh: AMBIGUOUS - multiple profiles match remote '$REMOTE_URL':" >&2
    printf '  %s\n' "${matched[@]}" >&2
    echo "tighten remote_matches in one of them." >&2
    exit 3
    ;;
esac
