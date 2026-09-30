#!/usr/bin/env bash
# wait-for-merge-ready.sh - poll a PR until it can be merged or needs a human.
#
# Use when the user already authorized the merge and the PR is only waiting on
# CI, a required approval, or review bots. Run it with the harness's background
# mode so the session wakes when the state changes instead of idling for hours.
# It never merges and never bypasses review; the caller re-checks and merges.
#
# Usage:
#   wait-for-merge-ready.sh [PR] [--timeout SEC] [--interval SEC]
#
# Exit: 0 ready (open, approved or no review needed, CLEAN, 0 unresolved threads)
#       3 already merged or closed
#       4 needs attention (unresolved threads, changes requested, failing checks, conflict)
#       8 still waiting after timeout · 1 gh error · 2 usage
set -euo pipefail

TIMEOUT="${WAIT_FOR_MERGE_TIMEOUT:-86400}"
INTERVAL="${WAIT_FOR_MERGE_INTERVAL:-60}"
PR=""

usage() { echo "usage: wait-for-merge-ready.sh [PR] [--timeout SEC] [--interval SEC]" >&2; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 2 ;;
    --timeout) [[ $# -ge 2 ]] || { usage; exit 2; }; TIMEOUT="$2"; shift 2 ;;
    --timeout=*) TIMEOUT="${1#--timeout=}"; shift ;;
    --interval) [[ $# -ge 2 ]] || { usage; exit 2; }; INTERVAL="$2"; shift 2 ;;
    --interval=*) INTERVAL="${1#--interval=}"; shift ;;
    -*) echo "wait-for-merge-ready: unknown flag: $1" >&2; usage; exit 2 ;;
    *) [[ -z "$PR" ]] || { usage; exit 2; }; PR="$1"; shift ;;
  esac
done
[[ "$TIMEOUT" =~ ^[0-9]+$ && "$INTERVAL" =~ ^[0-9]+$ ]] || { usage; exit 2; }

view=(pr view --json number,state,reviewDecision,mergeStateStatus,url)
[[ -n "$PR" ]] && view+=("$PR")

deadline=$((SECONDS + TIMEOUT))
last=""
while true; do
  info=$(gh "${view[@]}" --jq '[.number, .state, (.reviewDecision // ""), .mergeStateStatus, .url] | map(tostring) | join("|")') || exit 1
  IFS='|' read -r number state review merge url <<<"$info"
  repo=$(sed -E 's#https://github.com/([^/]+)/([^/]+)/pull/.*#\1 \2#' <<<"$url")
  read -r owner name <<<"$repo"
  unresolved=$(gh api graphql -F owner="$owner" -F name="$name" -F number="$number" -f query='
    query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){pullRequest(number:$number){
      reviewThreads(first:100){nodes{isResolved}}}}}' \
    --jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved | not)] | length') || exit 1

  status="state=$state review=${review:-none} merge=$merge unresolved=$unresolved"
  [[ "$status" != "$last" ]] && echo "wait-for-merge-ready: #$number $status"
  last="$status"

  if [[ "$state" != "OPEN" ]]; then exit 3; fi
  if (( unresolved > 0 )) || [[ "$review" == "CHANGES_REQUESTED" || "$merge" =~ ^(DIRTY|UNSTABLE)$ ]]; then exit 4; fi
  if [[ "$merge" == "CLEAN" || "$merge" == "HAS_HOOKS" ]] && [[ "$review" != "REVIEW_REQUIRED" ]]; then exit 0; fi
  if (( SECONDS >= deadline )); then echo "wait-for-merge-ready: still waiting after ${TIMEOUT}s" >&2; exit 8; fi
  sleep "$INTERVAL"
done
