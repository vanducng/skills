#!/usr/bin/env bash
# state-rw.sh - atomic read/write helpers for .auto-loop/goal-state.json.
# Validates against state-schema.json before any write. Atomic via tmpfile + mv (POSIX
# rename atomicity on the same filesystem).
#
# Source this file or invoke directly:
#   state-rw.sh read  <path>             → emits validated JSON to stdout
#   state-rw.sh write <path> <json>      → atomic write after schema validation
#   state-rw.sh seed  <path>             → write a fresh `pursuing` state at iter 0

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
SCHEMA="$SKILL_DIR/state-schema.json"
PYTHON_BIN="${PYTHON_BIN:-$HOME/.claude/skills/.venv/bin/python3}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi

_have_python_jsonschema() {
  [[ -x "$PYTHON_BIN" ]] && "$PYTHON_BIN" -c "import jsonschema" >/dev/null 2>&1
}

_validate_json() {
  # _validate_json <json-string> - exit 0 if valid, non-zero with stderr message otherwise.
  local payload="$1"

  # Cheap structural check via jq first
  if ! printf '%s' "$payload" | jq empty >/dev/null 2>&1; then
    echo "state-rw: payload is not valid JSON" >&2
    return 1
  fi

  # Required-field + enum checks via jq (works without python).
  local missing
  missing=$(printf '%s' "$payload" | jq -r '
    [
      "schema_version","iteration","status","evidence","blockers",
      "next_action","tokens_used","started_at","last_update","last_diff_signature"
    ] - keys | .[]
  ')
  if [[ -n "$missing" ]]; then
    echo "state-rw: missing required fields:" >&2
    echo "$missing" | sed "s/^/ - /" >&2
    return 1
  fi

  local status
  status=$(printf '%s' "$payload" | jq -r '.status')
  case "$status" in
    pursuing|achieved|unmet|blocked|budget-limited|cancelled) ;;
    *)
      echo "state-rw: invalid status '$status'" >&2
      return 1
      ;;
  esac

  local schema_version
  schema_version=$(printf '%s' "$payload" | jq -r '.schema_version')
  if [[ "$schema_version" != "1" ]]; then
    echo "state-rw: unsupported schema_version '$schema_version' (expected 1)" >&2
    return 1
  fi

  # Full schema check if python+jsonschema available. Payload arrives via stdin.
  if _have_python_jsonschema; then
    if ! printf '%s' "$payload" | "$PYTHON_BIN" -c '
import json, sys, jsonschema
schema_path = sys.argv[1]
with open(schema_path) as f:
    schema = json.load(f)
payload = json.loads(sys.stdin.read())
try:
    jsonschema.validate(payload, schema)
except jsonschema.ValidationError as e:
    sys.stderr.write("state-rw: schema validation failed: " + e.message + "\n")
    sys.exit(1)
' "$SCHEMA"; then
      return 1
    fi
  fi

  return 0
}

state_read() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "state-rw: file not found: $path" >&2
    return 2
  fi
  local payload
  payload=$(cat "$path")
  if ! _validate_json "$payload"; then
    return 1
  fi
  printf '%s' "$payload"
}

state_write() {
  local path="$1"
  local payload="$2"

  if ! _validate_json "$payload"; then
    return 1
  fi

  mkdir -p "$(dirname "$path")"
  local tmp
  tmp=$(mktemp "${path}.XXXXXX.tmp")
  # Pretty-print for human inspection; jq normalizes ordering.
  printf '%s' "$payload" | jq '.' > "$tmp"
  mv -f "$tmp" "$path"
}

state_seed() {
  local path="$1"
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local payload
  payload=$(jq -n --arg now "$now" '{
    schema_version: 1,
    iteration: 0,
    status: "pursuing",
    evidence: [],
    blockers: [],
    next_action: "begin",
    tokens_used: 0,
    started_at: $now,
    last_update: $now,
    last_diff_signature: "",
    verifier_result: "not-run",
    audit_vote: "not-run",
    restart_count: 0,
    session_id: ""
  }')
  state_write "$path" "$payload"
}

# CLI entrypoint
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  cmd="${1:-}"
  case "$cmd" in
    read)
      state_read "${2:?path required}"
      ;;
    write)
      state_write "${2:?path required}" "${3:?json payload required}"
      ;;
    seed)
      state_seed "${2:?path required}"
      ;;
    *)
      echo "usage: state-rw.sh {read|write|seed} <path> [json]" >&2
      exit 2
      ;;
  esac
fi
