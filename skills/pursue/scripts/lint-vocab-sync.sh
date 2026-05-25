#!/usr/bin/env bash
# lint-vocab-sync.sh — verify references/action-vocab.md ↔ .yaml and
# references/verifier-vocab.md ↔ .yaml are in sync (same action / verifier
# names). Run during Phase 2's smoke test; can be wired into CI later.
#
# Exit: 0 if synced, non-zero with diff report if drifted.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REF_DIR="$(dirname "$SCRIPT_DIR")/references"

PYBIN="${HOME}/.claude/skills/.venv/bin/python3"
if [ ! -x "$PYBIN" ]; then PYBIN="$(command -v python3)"; fi

rc=0

# ── Check action-vocab.md ↔ action-vocab.yaml ─────────────────────────────────

# Extract action names from the markdown table: rows starting with `| \``
md_actions="$(awk -F'|' '
  /^\| `[a-z_]+`/ {
    name = $2
    gsub(/[ \`]/, "", name)
    print name
  }
' "${REF_DIR}/action-vocab.md" | sort -u)"

yaml_actions="$("$PYBIN" - <<PY | sort -u
import yaml
d = yaml.safe_load(open("${REF_DIR}/action-vocab.yaml"))
for k in (d.get('actions') or {}).keys():
    print(k)
PY
)"

if ! diff -q <(echo "$md_actions") <(echo "$yaml_actions") >/dev/null 2>&1; then
  echo "DRIFT: action-vocab.md ↔ action-vocab.yaml" >&2
  echo "--- in .md but not .yaml:" >&2
  comm -23 <(echo "$md_actions") <(echo "$yaml_actions") | sed 's/^/  /' >&2
  echo "--- in .yaml but not .md:" >&2
  comm -13 <(echo "$md_actions") <(echo "$yaml_actions") | sed 's/^/  /' >&2
  rc=1
else
  echo "OK: action-vocab synced ($(echo "$md_actions" | wc -l | tr -d ' ') actions)"
fi

# ── Check verifier-vocab.md ↔ verifier-vocab.yaml ─────────────────────────────

# Verifier names appear as ### Headers in .md AND as top-level keys under
# `verifiers:` in .yaml.
md_verifiers="$(awk '
  /^\| `[a-z_]+`/ {
    # Same table-row pattern as action-vocab — first column is the type name.
    # But verifier-vocab.md has a single table; pull all backtick-wrapped
    # identifiers from the type column.
    n = split($0, fields, "|")
    name = fields[2]
    gsub(/[ \`]/, "", name)
    if (name != "") print name
  }
' "${REF_DIR}/verifier-vocab.md" | sort -u)"

yaml_verifiers="$("$PYBIN" - <<PY | sort -u
import yaml
d = yaml.safe_load(open("${REF_DIR}/verifier-vocab.yaml"))
for k in (d.get('verifiers') or {}).keys():
    print(k)
PY
)"

if ! diff -q <(echo "$md_verifiers") <(echo "$yaml_verifiers") >/dev/null 2>&1; then
  echo "DRIFT: verifier-vocab.md ↔ verifier-vocab.yaml" >&2
  echo "--- in .md but not .yaml:" >&2
  comm -23 <(echo "$md_verifiers") <(echo "$yaml_verifiers") | sed 's/^/  /' >&2
  echo "--- in .yaml but not .md:" >&2
  comm -13 <(echo "$md_verifiers") <(echo "$yaml_verifiers") | sed 's/^/  /' >&2
  rc=1
else
  echo "OK: verifier-vocab synced ($(echo "$md_verifiers" | wc -l | tr -d ' ') types)"
fi

exit $rc
