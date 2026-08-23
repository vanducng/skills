# lib.sh - shared helpers for ultracook state scripts.
# Source from a script that has already set -euo pipefail.
# Expects SCRIPT_DIR to be the scripts/ directory.

_uc_python() {
  if [ -n "${UC_PYTHON:-}" ] && [ -x "${UC_PYTHON}" ]; then
    printf '%s' "${UC_PYTHON}"
    return
  fi
  local venv="${HOME}/.claude/skills/.venv/bin/python3"
  if [ -x "$venv" ]; then
    printf '%s' "$venv"
    return
  fi
  command -v python3
}

_uc_hash12() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 | awk '{print substr($1, 1, 12)}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum | awk '{print substr($1, 1, 12)}'
  else
    cksum | awk '{print $1}'
  fi
}

_uc_state_repo_id() {
  local root="$1"
  local source name hash
  source="$(git -C "$root" remote get-url origin 2>/dev/null || printf '%s' "$root")"
  name="$(printf '%s' "$source" | sed -E 's#\\#/#g; s#^.*[:/]##; s#[.]git$##')"
  if [ -z "$name" ]; then
    name="$(basename "$root")"
  fi
  name="$(printf '%s' "$name" \
    | tr '[:upper:]' '[:lower:]' \
    | LC_ALL=C sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//')"
  if [ -z "$name" ]; then
    name="repo"
  fi
  hash="$(printf '%s' "$source" | _uc_hash12)"
  echo "${name}-${hash}"
}

# Print newline-separated globs that may contain state.json files.
# $VD_STATE_PATH is exclusive when set; otherwise workbench / XDG / legacy.
_uc_state_globs() {
  if [ -n "${VD_STATE_PATH:-}" ]; then
    echo "${VD_STATE_PATH}/*/state.json"
    return
  fi
  local repo_root
  repo_root="$(git rev-parse --show-toplevel 2>/dev/null || echo '')"
  if [ -n "$repo_root" ] && [ -d "${repo_root}/.workbench" ]; then
    echo "${repo_root}/.workbench/state/*/state.json"
  elif [ -n "$repo_root" ] && [ -d "${repo_root}/.work" ]; then
    echo "${repo_root}/.work/state/*/state.json"
  fi
  if [ -n "$repo_root" ]; then
    echo "${XDG_STATE_HOME:-${HOME}/.local/state}/vd/ultracook/$(_uc_state_repo_id "$repo_root")/goals/*/state.json"
    echo "${repo_root}/plans/goals/*/state.json"
  else
    echo "plans/goals/*/state.json"
  fi
}

# Resolve where a NEW goal should be written. Never writes into plans/goals.
_uc_new_state_base() {
  if [ -n "${VD_STATE_PATH:-}" ]; then
    printf '%s' "${VD_STATE_PATH}"
    return
  fi
  local repo_root
  repo_root="$(git rev-parse --show-toplevel 2>/dev/null || echo '')"
  if [ -n "$repo_root" ] && [ -d "${repo_root}/.workbench" ]; then
    printf '%s' "${repo_root}/.workbench/state"
    return
  fi
  if [ -n "$repo_root" ]; then
    printf '%s' "${XDG_STATE_HOME:-${HOME}/.local/state}/vd/ultracook/$(_uc_state_repo_id "$repo_root")/goals"
    return
  fi
  printf '%s' "${XDG_STATE_HOME:-${HOME}/.local/state}/vd/ultracook/local/goals"
}
