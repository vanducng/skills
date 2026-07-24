#!/usr/bin/env bash
# parse-goal-spec.sh - read a goal.md spec; emit KEY=VALUE env-style lines for sourcing.
# Exits non-zero if `# Goal` block or `verify:` field is missing.
#
# Usage: parse-goal-spec.sh <path-to-goal.md>
# Stdout: KEY=VALUE lines (GOAL, VERIFY, ALLOW, DENY, MAX_ITERATIONS, MAX_TOKENS,
#         MAX_WALLCLOCK, RESTART_AT_CONTEXT_PCT, MAX_RESTARTS)
# Stderr: human-readable parse errors.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: parse-goal-spec.sh <path-to-goal.md>" >&2
  exit 2
fi

spec="$1"

if [[ ! -f "$spec" ]]; then
  echo "parse-goal-spec: file not found: $spec" >&2
  exit 2
fi

# Defaults
GOAL=""
VERIFY=""
ALLOW=""
DENY=""
MAX_ITERATIONS=40
MAX_TOKENS=2000000
MAX_WALLCLOCK="4h"
RESTART_AT_CONTEXT_PCT=70
MAX_RESTARTS=5

# Two-pass parser:
#   1) Walk the file collecting `# Goal` block content (until next `#` heading).
#   2) Then scan for `key: value` lines anywhere in the file.

in_goal_block=0
goal_lines=()

while IFS= read -r line || [[ -n "$line" ]]; do
  # Detect headings
  if [[ "$line" =~ ^#[[:space:]]*[Gg]oal[[:space:]]*$ ]]; then
    in_goal_block=1
    continue
  fi
  if [[ "$line" =~ ^#[[:space:]] ]]; then
    in_goal_block=0
    continue
  fi
  if [[ "$in_goal_block" -eq 1 ]]; then
    goal_lines+=("$line")
  fi
done < "$spec"

# Trim leading/trailing blank lines from goal_lines
GOAL=$(printf '%s\n' "${goal_lines[@]}" | sed -e '/./,$!d' | sed -e :a -e '/^\n*$/{$d;N;ba' -e '}')

if [[ -z "${GOAL// }" ]]; then
  echo "parse-goal-spec: missing or empty '# Goal' block in $spec" >&2
  exit 1
fi

# Pass 2: key/value lines (anywhere in file)
strip_comment() {
  # Drop trailing ' # comment' but preserve content inside backticks.
  local s="$1"
  if [[ "$s" == *'`'* ]]; then
    printf '%s' "$s"
  else
    printf '%s' "${s%%#*}"
  fi
}

normalize_num() {
  # 2_000_000 → 2000000
  printf '%s' "${1//_/}"
}

while IFS= read -r raw || [[ -n "$raw" ]]; do
  line=$(strip_comment "$raw")
  # Skip non key:value lines
  if ! [[ "$line" =~ ^[[:space:]]*([A-Za-z_]+)[[:space:]]*:[[:space:]]*(.*)$ ]]; then
    continue
  fi
  key="${BASH_REMATCH[1]}"
  val="${BASH_REMATCH[2]}"
  # Trim whitespace
  val="${val#"${val%%[![:space:]]*}"}"
  val="${val%"${val##*[![:space:]]}"}"
  # Strip surrounding backticks
  if [[ "$val" =~ ^\`(.*)\`$ ]]; then
    val="${BASH_REMATCH[1]}"
  fi

  case "$key" in
    verify)                 VERIFY="$val" ;;
    allow)                  ALLOW="$val" ;;
    deny)                   DENY="$val" ;;
    max_iterations)         MAX_ITERATIONS=$(normalize_num "$val") ;;
    max_tokens)             MAX_TOKENS=$(normalize_num "$val") ;;
    max_wallclock)          MAX_WALLCLOCK="$val" ;;
    restart_at_context_pct) RESTART_AT_CONTEXT_PCT=$(normalize_num "$val") ;;
    max_restarts)           MAX_RESTARTS=$(normalize_num "$val") ;;
    *) ;;  # forward-compat: silently ignore unknown keys
  esac
done < "$spec"

if [[ -z "${VERIFY// }" ]]; then
  echo "parse-goal-spec: missing 'verify:' field in $spec" >&2
  exit 1
fi

# Emit. Quote VERIFY/GOAL because they may contain spaces & special chars.
escape() {
  # POSIX-shell single-quote escape: ' → '\''
  local s="$1"
  printf "'%s'" "${s//\'/\'\\\'\'}"
}

printf 'GOAL=%s\n'                   "$(escape "$GOAL")"
printf 'VERIFY=%s\n'                 "$(escape "$VERIFY")"
printf 'ALLOW=%s\n'                  "$(escape "$ALLOW")"
printf 'DENY=%s\n'                   "$(escape "$DENY")"
printf 'MAX_ITERATIONS=%s\n'         "$MAX_ITERATIONS"
printf 'MAX_TOKENS=%s\n'             "$MAX_TOKENS"
printf 'MAX_WALLCLOCK=%s\n'          "$(escape "$MAX_WALLCLOCK")"
printf 'RESTART_AT_CONTEXT_PCT=%s\n' "$RESTART_AT_CONTEXT_PCT"
printf 'MAX_RESTARTS=%s\n'           "$MAX_RESTARTS"
