#!/usr/bin/env bash
# _state-dir.sh — resolve the canonical .auto-loop state dir (source me; sets $state_dir).
#
# .auto-loop is a per-checkout CACHE (live loop state + forensics), intentionally
# OUTSIDE the .work artifact umbrella. It stays worktree-LOCAL by design: two loops
# running in two worktrees must not share state. So anchor to the working-tree root
# (the worktree itself when inside one) — NOT the invoking CWD, which may be a subdir.
# Honors VD_AUTOLOOP_WORKSPACE when set.
_autoloop_workspace() {
  if [[ -n "${VD_AUTOLOOP_WORKSPACE:-}" ]]; then
    printf '%s' "$VD_AUTOLOOP_WORKSPACE"
  else
    git rev-parse --show-toplevel 2>/dev/null || pwd
  fi
}
state_dir="$(_autoloop_workspace)/.auto-loop"
