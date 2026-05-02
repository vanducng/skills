#!/usr/bin/env bash
# new-skill.sh — scaffold a new skill folder under skills/<name>/ with a SKILL.md template.
# Usage: scripts/new-skill.sh <skill-name>
set -euo pipefail

name="${1:-}"
[[ -n "$name" ]] || { echo "usage: $0 <skill-name>" >&2; exit 1; }

if [[ ! "$name" =~ ^[a-z][a-z0-9-]*$ ]]; then
  echo "error: name must be kebab-case (lowercase letters, digits, hyphens; starts with a letter)" >&2
  exit 1
fi

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dir="${REPO}/skills/${name}"

[[ -e "$dir" ]] && { echo "error: $dir already exists" >&2; exit 1; }

mkdir -p "$dir"
cat > "${dir}/SKILL.md" <<EOF
---
name: ${name}
description: TODO — one sentence describing what this skill does AND the exact phrase the user might type to trigger it. Be specific; vague descriptions never route.
license: MIT
---

# ${name}

TODO: instructions Claude follows when this skill is invoked.
EOF

echo "scaffolded ${dir}/SKILL.md"
echo "next: edit description, then run scripts/install.sh && scripts/validate.sh"
