#!/usr/bin/env bash
# intake-complete.sh — shared default-answer gate for #60 (codex-exec / CI).
# Validates the PURSUE_* intake env vars; lets both runtimes decide whether to
# skip the interactive AskUserQuestion intake.
#
# Stdout: "ready"               when all required answers present + valid
#         "missing: <list>"     when required answers absent
#         "invalid: <details>"  when a present value fails enum validation
# Exit:   0 ready · 2 missing · 3 invalid
#
# Required (local/pr-only): PURSUE_TARGET_KIND, PURSUE_ACTION_SHAPE, PURSUE_AUTONOMY.
# Optional: PURSUE_BRANCH (derives from slug), PURSUE_REUSE_WORKTREE (default 0).
set -uo pipefail

missing=()
[ -n "${PURSUE_TARGET_KIND:-}" ]  || missing+=("--target-kind")
[ -n "${PURSUE_ACTION_SHAPE:-}" ] || missing+=("--action-shape")
[ -n "${PURSUE_AUTONOMY:-}" ]     || missing+=("--autonomy")
if [ "${#missing[@]}" -gt 0 ]; then
  echo "missing: ${missing[*]}"; exit 2
fi

invalid=()
case "$PURSUE_TARGET_KIND" in local|pr-only|cluster) ;; *) invalid+=("target-kind=$PURSUE_TARGET_KIND (want local|pr-only|cluster)") ;; esac
case "$PURSUE_ACTION_SHAPE" in brainstorm-first|plan-only|fix-and-ship|refactor) ;; *) invalid+=("action-shape=$PURSUE_ACTION_SHAPE (want brainstorm-first|plan-only|fix-and-ship|refactor)") ;; esac
case "$PURSUE_AUTONOMY" in manual|semi|auto) ;; *) invalid+=("autonomy=$PURSUE_AUTONOMY (want manual|semi|auto)") ;; esac
if [ "${#invalid[@]}" -gt 0 ]; then
  echo "invalid: ${invalid[*]}"; exit 3
fi

echo "ready"
