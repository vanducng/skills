#!/usr/bin/env bash
# check-install-conflicts.sh — detect a skill installed BOTH as a vd symlink and
# as a Claude Code plugin-marketplace copy (#64). Warn-only by default.
#
# Sources scanned per skill name:
#   ~/.claude/skills/<name>            (vd symlink install)
#   ~/.agents/skills/<name>            (vd symlink install, Codex)
#   ~/.claude/plugins/cache/*/skills/<name>   (marketplace plugin cache)
#
# A conflict = the name resolves to a vd symlink AND a marketplace copy. When
# both exist, skill discovery may pick either depending on load order, and edits
# to one won't appear in the other.
#
# Usage: check-install-conflicts.sh [--strict]
# Exit: 0 no conflict (or warn-only) · 3 conflict found with --strict · 2 bad args
set -uo pipefail

STRICT=0
case "${1:-}" in
  --strict) STRICT=1 ;;
  "" ) ;;
  -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *) echo "check-install-conflicts.sh: unknown arg: $1" >&2; exit 2 ;;
esac

CLAUDE_SKILLS="${HOME}/.claude/skills"
AGENTS_SKILLS="${HOME}/.agents/skills"
CACHE_GLOB="${HOME}/.claude/plugins/cache"

conflicts=0
# Gather marketplace skill names (basename) → presence set.
declare -A market=()
if [ -d "$CACHE_GLOB" ]; then
  # Marketplace layout: cache/<marketplace>/<plugin>/<version>/skills/<name>.
  # Match only the immediate children of any skills/ dir (any nesting depth).
  while IFS= read -r d; do
    [ -n "$d" ] || continue
    market["$(basename "$d")"]="$d"
  done < <(find "$CACHE_GLOB" -type d -path '*/skills/*' ! -path '*/skills/*/*' 2>/dev/null)
fi

check_dir() {
  local dir="$1"
  [ -d "$dir" ] || return 0
  for entry in "$dir"/*; do
    [ -L "$entry" ] || continue        # only vd installs are symlinks
    local name; name="$(basename "$entry")"
    if [ -n "${market[$name]:-}" ]; then
      echo "CONFLICT  $name — vd symlink ($entry → $(readlink "$entry")) AND marketplace copy (${market[$name]})" >&2
      conflicts=$((conflicts + 1))
    fi
  done
}
check_dir "$CLAUDE_SKILLS"
check_dir "$AGENTS_SKILLS"

if [ "$conflicts" -eq 0 ]; then
  echo "no vd-symlink ↔ marketplace duplicate skills detected"
  exit 0
fi
echo "" >&2
echo "$conflicts duplicate(s). Precedence: a marketplace plugin and a dev symlink of the same skill" >&2
echo "shadow each other unpredictably. Keep ONE: either \`/plugin uninstall\` the marketplace copy" >&2
echo "or remove the symlink (scripts/uninstall.sh)." >&2
[ "$STRICT" -eq 1 ] && exit 3
exit 0
