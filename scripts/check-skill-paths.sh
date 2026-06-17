#!/usr/bin/env bash
# check-skill-paths.sh — guard producer skills against hardcoding umbrella paths
# instead of writing to the hook-injected Reports:/Visuals:/Journals: paths.
#
# Default: REPORT-ONLY (prints findings, exits 0). Pass --enforce to exit 1 on any
# violation. validate.sh runs it with --enforce (producer skills are one-lined to the
# injected paths). Consumers/layout-docs that legitimately reference the umbrella are
# allowlisted below.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_ROOT="${REPO}/skills"
ENFORCE=0
[[ "${1:-}" == "--enforce" ]] && ENFORCE=1

[[ -d "$SKILLS_ROOT" ]] || { echo "no skills/ dir"; exit 0; }

# Hardcoded artifact paths + the retired interim mechanism (feature-folder.json).
FORBIDDEN='(\.workbench/|plans/(reports|visuals|journals)|feature-folder\.json)'
# Allowed to reference umbrella paths: migrator + lifecycle owner + skill-authoring docs,
# plus consumers that READ the layout (devlog) and skills that DOCUMENT it (worktree, ultracook).
ALLOWLIST_RE='^(cktovd|workbench|skill-creator|template-skill|worktree|ultracook|devlog)$'

violations=0
flagged_files=0

while IFS= read -r f; do
  rel="${f#"$SKILLS_ROOT"/}"
  skill="${rel%%/*}"
  [[ "$skill" =~ $ALLOWLIST_RE ]] && continue
  hits="$(grep -nE "$FORBIDDEN" "$f" || true)"
  [[ -z "$hits" ]] && continue
  flagged_files=$((flagged_files + 1))
  echo "  ${rel}:"
  while IFS= read -r line; do echo "    ${line}"; done <<< "$hits"
  violations=$((violations + $(printf '%s\n' "$hits" | wc -l | tr -d ' ')))
done < <(find "$SKILLS_ROOT" -type f \( -name 'SKILL.md' -o -path '*/references/*.md' \) | sort)

echo
if [[ $violations -eq 0 ]]; then
  echo "check-skill-paths: OK (0 hardcoded-path violations)"
  exit 0
fi

if [[ $ENFORCE -eq 1 ]]; then
  echo "check-skill-paths: FAIL — ${violations} violation(s) in ${flagged_files} file(s). Use the injected Reports:/Visuals:/Journals: path."
  exit 1
fi
echo "check-skill-paths: ${violations} finding(s) in ${flagged_files} file(s) [report-only; --enforce flips on in Phase 6]"
exit 0
