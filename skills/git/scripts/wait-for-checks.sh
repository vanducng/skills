#!/usr/bin/env bash
# wait-for-checks.sh — poll `gh pr checks` until the result is terminal.
#
# `gh pr checks` exits 8 while any check is still pending. Treat 8 as retry,
# never as failure. Do not write `gh pr checks N && gh pr merge N` — the merge
# never runs while CI is queued.
#
# This script does not merge. hooks/pr-merge-guard.py still blocks
# `gh pr merge` while review threads are unresolved. To queue a merge until
# GitHub is satisfied, use `gh pr merge --auto` instead of waiting here.
# Full-pipeline CI watch lives in vd:ship Step 15 — do not duplicate it.
#
# Only exit 8 is retried. Auth errors, usage errors, and upstream HTTP
# failures (including 503) are terminal — surface them, do not back off.
#
# Usage:
#   wait-for-checks.sh [PR] [--timeout SEC] [--interval SEC] [--required]
#   PR may be a number, URL, or branch. Omit to use the current branch's PR.
#
# Exit: 0 all pass · 1 fail / gh error · 8 still pending after timeout · 2 usage
set -euo pipefail

TIMEOUT="${WAIT_FOR_CHECKS_TIMEOUT:-900}"
INTERVAL="${WAIT_FOR_CHECKS_INTERVAL:-10}"
REQUIRED=0
PR=""

usage() {
  cat <<'EOF' >&2
usage: wait-for-checks.sh [PR] [--timeout SEC] [--interval SEC] [--required]
  PR          number, URL, or branch (default: current branch)
  --timeout   seconds to keep polling pending checks (default 900, or WAIT_FOR_CHECKS_TIMEOUT)
  --interval  seconds between polls (default 10, or WAIT_FOR_CHECKS_INTERVAL)
  --required  pass --required through to `gh pr checks`
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 2
      ;;
    --timeout)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      TIMEOUT="$2"
      shift 2
      ;;
    --timeout=*)
      TIMEOUT="${1#--timeout=}"
      shift
      ;;
    --interval)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      INTERVAL="$2"
      shift 2
      ;;
    --interval=*)
      INTERVAL="${1#--interval=}"
      shift
      ;;
    --required)
      REQUIRED=1
      shift
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "wait-for-checks: unknown flag: $1" >&2
      usage
      exit 2
      ;;
    *)
      if [[ -n "$PR" ]]; then
        echo "wait-for-checks: unexpected extra argument: $1" >&2
        usage
        exit 2
      fi
      PR="$1"
      shift
      ;;
  esac
done

[[ "$TIMEOUT" =~ ^[0-9]+$ ]] || { echo "wait-for-checks: --timeout must be an integer" >&2; exit 2; }
[[ "$INTERVAL" =~ ^[0-9]+$ ]] || { echo "wait-for-checks: --interval must be an integer" >&2; exit 2; }

if ! command -v gh >/dev/null 2>&1; then
  echo "wait-for-checks: gh not on PATH" >&2
  exit 2
fi

gh_args=(pr checks)
if [[ "$REQUIRED" -eq 1 ]]; then
  gh_args+=(--required)
fi
if [[ -n "$PR" ]]; then
  gh_args+=("$PR")
fi

deadline=$((SECONDS + TIMEOUT))
while true; do
  set +e
  out=$(gh "${gh_args[@]}" 2>&1)
  rc=$?
  set -e
  printf '%s\n' "$out"
  case "$rc" in
    0)
      exit 0
      ;;
    8)
      if (( SECONDS >= deadline )); then
        echo "wait-for-checks: still pending after ${TIMEOUT}s (exit 8 is pending, not failure)" >&2
        exit 8
      fi
      sleep "$INTERVAL"
      ;;
    *)
      echo "wait-for-checks: gh pr checks exited $rc (not retrying; only exit 8 is pending)" >&2
      exit "$rc"
      ;;
  esac
done
