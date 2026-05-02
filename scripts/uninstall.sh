#!/usr/bin/env bash
# uninstall.sh — remove symlinks under ~/.claude/skills/ that resolve into this repo.
# Never touches files we don't own.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_ROOT="${REPO}/skills"
DEST_DIR="${HOME}/.claude/skills"

[[ -d "$DEST_DIR" ]] || { echo "$DEST_DIR does not exist — nothing to do"; exit 0; }

removed=0; kept=0

for entry in "$DEST_DIR"/*; do
  [[ -L "$entry" ]] || continue
  target="$(readlink "$entry")"
  # Resolve relative symlinks against ~/.claude/skills (shouldn't happen — install.sh writes absolute)
  case "$target" in
    /*) abs="$target" ;;
    *)  abs="${DEST_DIR}/${target}" ;;
  esac
  # Only remove if symlink target is under our repo's skills/ dir
  case "$abs" in
    "$SKILLS_ROOT"/*)
      rm -- "$entry"
      echo "removed  $(basename "$entry")"
      removed=$((removed + 1))
      ;;
    *)
      kept=$((kept + 1))
      ;;
  esac
done

echo
echo "summary: removed=$removed kept=$kept"
