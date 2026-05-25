#!/usr/bin/env bash
# codex-bridge.sh — Codex-side helpers for vd:pursue.
#
# Functions provided (sourced or invoked as subcommand):
#   codex_exec_resume_last <skill> <prompt>   — invoke another vd:* skill via
#                                                `codex exec resume --last`,
#                                                relying on auto-match against
#                                                skill description.
#   codex_hook_payload_read                   — read PostToolUse JSON from stdin
#                                                and export HOOK_TOOL_NAME /
#                                                HOOK_TOOL_INPUT / HOOK_TOOL_RESPONSE
#                                                env vars for the caller.
#   codex_exec_json_parse <jsonl-path>        — parse a Codex `--json` event
#                                                stream and emit a single JSON
#                                                with token totals + counts.
#
# Recursion guard: refuses if `VD_PURSUE_DEPTH > 0` — prevents nested
# pursue-spawns-pursue when invoked from a recursive subagent context.
#
# Phase 2 ships: `codex_exec_resume_last` minimal impl + `codex_hook_payload_read`
# Phase 3 hardens: adds `--session-id` fallback for non-determinism, error retry
# Phase 4 ships: `codex_exec_json_parse` (token telemetry)

set -uo pipefail

PYBIN="${HOME}/.claude/skills/.venv/bin/python3"
[ -x "$PYBIN" ] || PYBIN="$(command -v python3)"

# ── codex_exec_resume_last ────────────────────────────────────────────────────
# Resumes the most recent Codex session with an instruction to use the named
# skill on the given prompt. Returns the agent's final stdout for the journal.
#
# Stdout: tail of agent output (last ~2KB).
# Stderr: any setup/teardown noise.
# Exit:   0 if `codex exec resume` exits 0; non-zero otherwise.
#
# Usage: codex_exec_resume_last <skill-name> <prompt>
codex_exec_resume_last() {
  local skill="${1:?codex_exec_resume_last: <skill-name> required}"
  local prompt="${2:?codex_exec_resume_last: <prompt> required}"

  # Recursion guard.
  if [ "${VD_PURSUE_DEPTH:-0}" -gt 0 ]; then
    echo "codex_exec_resume_last: VD_PURSUE_DEPTH=$VD_PURSUE_DEPTH > 0 — refusing recursive pursue" >&2
    return 4
  fi

  # Precondition: codex must be on PATH.
  if ! command -v codex >/dev/null 2>&1; then
    echo "codex_exec_resume_last: codex CLI not found on PATH. Install via 'brew install vanducng/tap/vd' or upstream Codex docs." >&2
    return 3
  fi

  # Capture pre-call session-id from ~/.codex/sessions/ so we can fall back to
  # an explicit --session-id if --last races with parallel sessions (Phase 3
  # hardens this; Phase 2 ships the simpler --last variant).
  local pre_session_id=""
  if [ -d "$HOME/.codex/sessions" ]; then
    pre_session_id="$(find "$HOME/.codex/sessions" -maxdepth 2 -name '*.jsonl' -mmin -60 2>/dev/null \
      | xargs -I{} stat -f '%m {}' {} 2>/dev/null \
      | sort -rn | head -1 | awk '{print $2}')"
  fi

  # Compose the resume prompt — explicit "use the X skill" wording so Codex
  # auto-match picks the named skill reliably (non-deterministic; Phase 5
  # dogfood measures false-match rate + adjusts wording if needed).
  local resume_prompt="use the ${skill} skill to: ${prompt}"

  # Tee the agent output to stderr (for forensics) and stdout (tail for caller).
  local tmpout
  tmpout="$(mktemp -t pursue-codex-resume.XXXXXX)"
  trap "rm -f '$tmpout'" RETURN

  if codex exec resume --last "$resume_prompt" --json >"$tmpout" 2>&1; then
    # Parse the JSONL stream for the final agent message; emit tail for journal.
    "$PYBIN" - "$tmpout" <<'PY' 2>/dev/null || tail -c 2000 "$tmpout"
import json, sys
seen_final = False
for line in open(sys.argv[1]):
    line = line.strip()
    if not line: continue
    try:
        ev = json.loads(line)
    except Exception:
        continue
    # Codex --json emits item.* events; we want the final agent message text.
    if ev.get("type", "").startswith("item.") and ev.get("kind") == "agent_message":
        msg = ev.get("text") or ev.get("content") or ""
        if msg: print(msg[-2000:])
        seen_final = True
if not seen_final:
    # Fallback: tail.
    with open(sys.argv[1]) as f:
        print(f.read()[-2000:])
PY
    return 0
  else
    local rc=$?
    echo "codex_exec_resume_last: codex exec exited $rc. See log: $tmpout (will be removed on return)." >&2
    cat "$tmpout" >&2
    return $rc
  fi
}

# ── codex_hook_payload_read ───────────────────────────────────────────────────
# Reads PostToolUse JSON payload from stdin and exports parsed fields as env
# vars for the calling script. Designed to be `eval`'d in the hook handler.
#
# Exports: HOOK_TOOL_NAME, HOOK_TOOL_INPUT, HOOK_TOOL_RESPONSE, HOOK_SESSION_ID,
#          HOOK_TOOL_USE_ID, HOOK_EVENT_NAME, HOOK_CWD
#
# Stdout: a sequence of `export KEY=value` lines suitable for `eval`.
# Exit:   0 on success, 2 on invalid JSON.
codex_hook_payload_read() {
  # Read JSON payload from caller's stdin into a var, then pass via env var
  # — heredoc occupies python's stdin so the payload can't reach json.load directly.
  local payload
  payload="$(cat)"
  PURSUE_HOOK_PAYLOAD="$payload" "$PYBIN" - <<'PY'
import os, json, shlex
try:
    payload = json.loads(os.environ.get("PURSUE_HOOK_PAYLOAD", ""))
except Exception as e:
    print(f"# codex_hook_payload_read: invalid JSON — {e}", file=__import__("sys").stderr)
    raise SystemExit(2)
def emit(key, val):
    if val is None: val = ""
    print(f"export {key}={shlex.quote(str(val))}")
emit("HOOK_TOOL_NAME",    payload.get("tool_name"))
emit("HOOK_TOOL_INPUT",   json.dumps(payload.get("tool_input") or {}))
emit("HOOK_TOOL_RESPONSE",json.dumps(payload.get("tool_response") or {}))
emit("HOOK_SESSION_ID",   payload.get("session_id"))
emit("HOOK_TOOL_USE_ID",  payload.get("tool_use_id"))
emit("HOOK_EVENT_NAME",   payload.get("hook_event_name"))
emit("HOOK_CWD",          payload.get("cwd"))
PY
}

# ── codex_exec_json_parse ─────────────────────────────────────────────────────
# Parses a Codex `--json` JSONL file and emits a single JSON with token totals,
# error count, and timing. Phase 4 wires this into append-journal.sh for token
# telemetry per action.
#
# Stdout: JSON object {tokens_total, tokens_cached, errors_count, item_count,
#                       started_at, ended_at}
# Exit:   0 always (malformed lines skipped with defensive parsing).
codex_exec_json_parse() {
  local jsonl="${1:?codex_exec_json_parse: <jsonl-path> required}"
  "$PYBIN" - "$jsonl" <<'PY'
import sys, json
totals = {"tokens_total":0,"tokens_cached":0,"errors_count":0,"item_count":0,
          "started_at":None,"ended_at":None}
for line in open(sys.argv[1], errors="ignore"):
    line = line.strip()
    if not line: continue
    try:
        ev = json.loads(line)
    except Exception:
        continue
    t = ev.get("type","")
    ts = ev.get("timestamp") or ev.get("created_at")
    if t == "thread.started" and ts: totals["started_at"] = ts
    if t == "turn.completed":
        usage = ev.get("usage") or {}
        totals["tokens_total"]  += int(usage.get("input_tokens",0) or 0) + int(usage.get("output_tokens",0) or 0)
        totals["tokens_cached"] += int(usage.get("cached_input_tokens",0) or 0)
        if ts: totals["ended_at"] = ts
    if t == "error": totals["errors_count"] += 1
    if t.startswith("item."): totals["item_count"] += 1
print(json.dumps(totals))
PY
}

# ── CLI dispatch (when invoked as subcommand, not sourced) ────────────────────
# Usage when called directly:
#   bash codex-bridge.sh resume-last <skill> <prompt>
#   bash codex-bridge.sh hook-read < payload.json
#   bash codex-bridge.sh json-parse <path>
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  case "${1:-}" in
    resume-last) shift; codex_exec_resume_last "$@" ;;
    hook-read)   codex_hook_payload_read ;;
    json-parse)  shift; codex_exec_json_parse "$@" ;;
    "")
      echo "usage: codex-bridge.sh {resume-last <skill> <prompt> | hook-read | json-parse <jsonl>}" >&2
      exit 2
      ;;
    *)
      echo "codex-bridge.sh: unknown subcommand: $1" >&2
      exit 2
      ;;
  esac
fi
