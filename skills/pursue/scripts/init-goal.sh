#!/usr/bin/env bash
# init-goal.sh — Phase 1 intake helper.
# Reads env vars (PURSUE_*) populated by SKILL.md after AskUserQuestion calls.
# Writes plans/goals/{date}-{slug}/goal.yaml + state.json. Optionally creates a worktree.
# Stdout: the absolute path to the goal-dir (so SKILL.md can chain).
# Exit: 0 on success, non-zero with diagnostic on stderr.

set -euo pipefail

# ── Required env vars (set by SKILL.md from AskUserQuestion answers) ──────────

: "${PURSUE_TARGET_KIND:?PURSUE_TARGET_KIND not set (local | pr-only | cluster)}"
: "${PURSUE_ACTION_SHAPE:?PURSUE_ACTION_SHAPE not set (brainstorm-first | plan-only | fix-and-ship | refactor)}"
: "${PURSUE_AUTONOMY:?PURSUE_AUTONOMY not set (manual | semi | auto)}"

PURSUE_REUSE_WORKTREE="${PURSUE_REUSE_WORKTREE:-0}"   # 0 (default) = create, 1 = skip
PURSUE_BRANCH="${PURSUE_BRANCH:-}"                     # required unless --reuse

# ── Positional arg: the short goal ────────────────────────────────────────────

if [ $# -lt 1 ] || [ -z "${1:-}" ]; then
  echo "usage: init-goal.sh <short_goal>" >&2
  exit 2
fi
# Strip ASCII control chars (newlines, tabs, etc.) — they corrupt YAML body and filesystem paths.
SHORT_GOAL="$(printf '%s' "$1" | LC_ALL=C tr -d '\000-\037')"
if [ -z "$SHORT_GOAL" ]; then
  echo "init-goal.sh: short_goal is empty after stripping control chars" >&2
  exit 2
fi

# ── Validate enums ────────────────────────────────────────────────────────────

case "$PURSUE_TARGET_KIND" in local|pr-only|cluster) ;; *)
  echo "PURSUE_TARGET_KIND must be local|pr-only|cluster (got: $PURSUE_TARGET_KIND)" >&2; exit 2 ;;
esac
case "$PURSUE_ACTION_SHAPE" in brainstorm-first|plan-only|fix-and-ship|refactor) ;; *)
  echo "PURSUE_ACTION_SHAPE invalid (got: $PURSUE_ACTION_SHAPE)" >&2; exit 2 ;;
esac
case "$PURSUE_AUTONOMY" in manual|semi|auto) ;; *)
  echo "PURSUE_AUTONOMY must be manual|semi|auto (got: $PURSUE_AUTONOMY)" >&2; exit 2 ;;
esac

# ── Pre-flight: must be inside a git repo ─────────────────────────────────────

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "init-goal.sh: not inside a git work tree. /vd:pursue requires git context for branch + worktree handling." >&2
  exit 3
fi
REPO_ROOT="$(git rev-parse --show-toplevel)"
REPO_NAME="$(basename "$REPO_ROOT")"
REMOTE_URL="$(git remote get-url origin 2>/dev/null || echo '')"

# ── Slug derivation: kebab-case, ASCII-only, max 40 chars ─────────────────────

# Lowercase, replace non-alphanumeric with '-', collapse runs, strip leading/trailing '-'.
slugify() {
  printf '%s' "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | LC_ALL=C sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//' \
    | cut -c1-40 \
    | sed -E 's/-+$//'
}
SLUG="$(slugify "$SHORT_GOAL")"
if [ -z "$SLUG" ]; then
  SLUG="goal-$(date +%y%m%d-%H%M)"
fi

# ── Compute goal-dir path: plans/goals/{YYMMDD-HHMM}-{slug}/ ──────────────────

DATE_STAMP="$(date +%y%m%d-%H%M)"
GOAL_DIR_NAME="${DATE_STAMP}-${SLUG}"

# ── Decide branch name + worktree path ────────────────────────────────────────

if [ "$PURSUE_REUSE_WORKTREE" = "1" ]; then
  # --reuse: write into the current repo, capture current branch
  PURSUE_BRANCH="${PURSUE_BRANCH:-$(git rev-parse --abbrev-ref HEAD)}"
  WORKTREE_PATH=""
  GOAL_DIR="${REPO_ROOT}/plans/goals/${GOAL_DIR_NAME}"
else
  if [ -z "$PURSUE_BRANCH" ]; then
    echo "PURSUE_BRANCH must be set when not using --reuse" >&2
    exit 2
  fi
  # Worktree convention: sibling dir next to current repo, named ${repo}-${slug}.
  PARENT_DIR="$(dirname "$REPO_ROOT")"
  WORKTREE_PATH="${PARENT_DIR}/${REPO_NAME}-${SLUG}"
  # Collision handling: suffix -2, -3, ... if path exists.
  i=2
  while [ -e "$WORKTREE_PATH" ]; do
    WORKTREE_PATH="${PARENT_DIR}/${REPO_NAME}-${SLUG}-${i}"
    i=$((i + 1))
    if [ "$i" -gt 10 ]; then
      echo "Refusing to create worktree: 10+ collisions for ${REPO_NAME}-${SLUG}" >&2
      exit 4
    fi
  done
  GOAL_DIR="${WORKTREE_PATH}/plans/goals/${GOAL_DIR_NAME}"
fi

# ── Create worktree (skip on --reuse) ─────────────────────────────────────────

if [ "$PURSUE_REUSE_WORKTREE" = "0" ]; then
  # If branch already exists locally, attach to it; else create.
  if git show-ref --verify --quiet "refs/heads/${PURSUE_BRANCH}"; then
    git worktree add "$WORKTREE_PATH" "$PURSUE_BRANCH" >/dev/null
  else
    # Default base = origin/main if reachable, else current HEAD.
    BASE_REF="HEAD"
    if git rev-parse --verify origin/main >/dev/null 2>&1; then
      BASE_REF="origin/main"
    fi
    git worktree add "$WORKTREE_PATH" -b "$PURSUE_BRANCH" "$BASE_REF" >/dev/null
  fi
fi

# ── Make goal-dir + iterations subdir ─────────────────────────────────────────

mkdir -p "${GOAL_DIR}/iterations"

# ── Determine first action from action-shape ──────────────────────────────────

case "$PURSUE_ACTION_SHAPE" in
  brainstorm-first) FIRST_ACTION="brainstorm" ;;
  plan-only)        FIRST_ACTION="plan" ;;
  fix-and-ship)     FIRST_ACTION="fix" ;;
  refactor)         FIRST_ACTION="plan" ;;   # Phase 2 will append --tdd flag
esac

# ── Write goal.yaml ───────────────────────────────────────────────────────────

CREATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# Escape backslash THEN double-quote for YAML double-quoted-string safety.
SHORT_GOAL_YAML="$(printf '%s' "$SHORT_GOAL" | sed -e 's/\\/\\\\/g; s/"/\\"/g')"

# Worktree path: render as null literal when empty (--reuse case), else quoted string.
if [ -n "${WORKTREE_PATH:-}" ]; then
  WORKTREE_YAML="\"${WORKTREE_PATH}\""
else
  WORKTREE_YAML="null"
fi

cat > "${GOAL_DIR}/goal.yaml" <<YAML
version: 1
slug: ${SLUG}
created: ${CREATED_AT}
short_goal: "${SHORT_GOAL_YAML}"

project:
  name: "${REPO_NAME}"
  remote_url: "${REMOTE_URL}"
  worktree_path: ${WORKTREE_YAML}
  branch: "${PURSUE_BRANCH}"

target:
  kind: ${PURSUE_TARGET_KIND}
  env: ""
  verifiers: []   # workflow-level verifiers; populated by resolve-workflow.sh (Phase 2) from project profile

actions:
  - ${FIRST_ACTION}   # rest of sequence merges from profile at resolve time

autonomy: ${PURSUE_AUTONOMY}

budgets:
  max_iterations: 30
  max_rebases: 3
  max_ci_reruns: 2
  token_pct_cap: 80
YAML

# ── Write state.json ──────────────────────────────────────────────────────────

cat > "${GOAL_DIR}/state.json" <<JSON
{
  "version": 1,
  "terminal": null,
  "terminal_reason": null,
  "current_phase": "intake-complete",
  "current_action": null,
  "iteration_count": 0,
  "budgets_consumed": { "rebases": 0, "ci_reruns": 0, "token_pct": 0 },
  "last_failure_signature": null,
  "last_failure_count": 0,
  "last_action_result": null,
  "journal_path": "iterations/",
  "pr_number": null,
  "updated_at": "${CREATED_AT}"
}
JSON

# ── Emit the goal-dir path on stdout (the chain-able output) ──────────────────

echo "$GOAL_DIR"
