#!/usr/bin/env bash
# install.sh — symlink each skills/<name>/ into ~/.claude/skills/<name>.
# Idempotent. Never overwrites existing non-symlink files.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_DIR="${HOME}/.claude/skills"

mkdir -p "$DEST_DIR"

linked=0; skipped=0; conflicts=0

for src in "$REPO"/skills/*/; do
  [[ -d "$src" ]] || continue
  name="$(basename "$src")"
  src_abs="${src%/}"
  target="${DEST_DIR}/${name}"

  if [[ ! -e "$target" && ! -L "$target" ]]; then
    ln -s "$src_abs" "$target"
    echo "linked   $name"
    linked=$((linked + 1))
  elif [[ -L "$target" ]]; then
    current="$(readlink "$target")"
    if [[ "$current" == "$src_abs" ]]; then
      echo "ok       $name (already linked)"
      skipped=$((skipped + 1))
    else
      echo "conflict $name (symlink points elsewhere: $current) — leaving as-is" >&2
      conflicts=$((conflicts + 1))
    fi
  else
    echo "conflict $name (non-symlink at $target) — leaving as-is" >&2
    conflicts=$((conflicts + 1))
  fi
done

AGENTS_DEST="${HOME}/.claude/agents"
mkdir -p "$AGENTS_DEST"

for src in "$REPO"/agents/*.md; do
  [[ -f "$src" ]] || continue
  name="$(basename "$src")"
  [[ "$name" == "README.md" ]] && continue
  target="${AGENTS_DEST}/${name}"

  if [[ ! -e "$target" && ! -L "$target" ]]; then
    ln -s "$src" "$target"
    echo "linked   agents/$name"
    linked=$((linked + 1))
  elif [[ -L "$target" ]]; then
    current="$(readlink "$target")"
    if [[ "$current" == "$src" ]]; then
      echo "ok       agents/$name (already linked)"
      skipped=$((skipped + 1))
    elif [[ ! -e "$target" ]]; then
      rm "$target" && ln -s "$src" "$target"
      echo "relinked agents/$name (dangling symlink repaired)"
      linked=$((linked + 1))
    else
      echo "conflict agents/$name (symlink points elsewhere: $current) — leaving as-is" >&2
      conflicts=$((conflicts + 1))
    fi
  else
    # pre-tracking deployed copy: adopt it only if content matches, else leave for manual review
    if cmp -s "$src" "$target"; then
      rm "$target" && ln -s "$src" "$target"
      echo "adopted  agents/$name (identical copy replaced with symlink)"
      linked=$((linked + 1))
    else
      echo "conflict agents/$name (differing non-symlink at $target) — leaving as-is" >&2
      conflicts=$((conflicts + 1))
    fi
  fi
done

echo
echo "summary: linked=$linked skipped=$skipped conflicts=$conflicts"
[[ $conflicts -eq 0 ]]
