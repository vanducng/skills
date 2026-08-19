#!/usr/bin/env bash
# check-slop.sh - deterministic floor for the vd:unslop skill.
# Flags em/en dashes and curly quotes in catalog prose. The catalog was swept
# clean once; this keeps it that way.
#
# Default: REPORT-ONLY (prints findings, exits 0). Pass --enforce to exit 1 on
# any violation. validate.sh runs it with --enforce.
# Scope: every .md under skills/ (minus vendored skills), docs/content/*.md|mdx, README.md.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENFORCE=0
[[ "${1:-}" == "--enforce" ]] && ENFORCE=1

# Vendored skills are upstream-owned; do not fail CI on their prose.
VENDORED_RE='^(browser|browser-trace|ego-browser)$'

# em dash U+2014, en dash U+2013, curly doubles U+201C/201D, curly singles U+2018/2019
PATTERN=$'\u2014|\u2013|\u201c|\u201d|\u2018|\u2019'

violations=0

scan() {
  local f="$1"
  local hits
  hits="$(grep -nE "$PATTERN" "$f" 2>/dev/null || true)"
  [[ -z "$hits" ]] && return 0
  echo "  ${f#"$REPO"/}:"
  while IFS= read -r line; do echo "    ${line}"; done <<< "$hits"
  violations=$((violations + $(printf '%s\n' "$hits" | wc -l | tr -d ' ')))
}

while IFS= read -r f; do
  skill="${f#"$REPO"/skills/}"; skill="${skill%%/*}"
  [[ "$skill" =~ $VENDORED_RE ]] && continue
  scan "$f"
done < <(find "$REPO/skills" -name '*.md' -type f 2>/dev/null | sort)

for f in "$REPO"/docs/content/*.md "$REPO"/docs/content/*.mdx "$REPO"/README.md; do
  [[ -f "$f" ]] && scan "$f"
done

echo
if [[ $violations -eq 0 ]]; then
  echo "check-slop: OK (0 violations)"
  exit 0
fi

echo "check-slop: ${violations} violation(s) - em/en dashes or curly quotes in catalog prose. Fix per vd:unslop (plain '-' and straight quotes)."
[[ $ENFORCE -eq 1 ]] && exit 1
exit 0
