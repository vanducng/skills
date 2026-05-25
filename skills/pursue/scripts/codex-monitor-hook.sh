#!/usr/bin/env bash
# codex-monitor-hook.sh — PostToolUse hook handler for Codex Monitor-style
# waits. Polls a user-specified condition and injects status into the model's
# next turn via `hookSpecificOutput.additionalContext`.
#
# This is pursue's workaround for the absence of a Monitor-tool analog on
# Codex. Spec'd in references/codex-gap-workarounds.md.
#
# Triggered by Codex's PostToolUse hook event. Reads the JSON payload from
# stdin, looks up the corresponding monitor.spec.json in the goal-dir's
# iterations/ directory, runs the poll command, and writes a result file +
# emits hookSpecificOutput JSON to stdout for Codex to consume.
#
# Stdin (from Codex): JSON payload with session_id, tool_use_id, etc.
# Stdout: JSON {hookSpecificOutput: {additionalContext: "<status>"}} (or empty
#         when no monitor is active for this tool_use_id).
# Exit: 0 always (hook errors must not break the agent turn).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYBIN="${HOME}/.claude/skills/.venv/bin/python3"
[ -x "$PYBIN" ] || PYBIN="$(command -v python3)"

# Read the hook payload via codex-bridge.sh — emits `export HOOK_*` lines.
# If parsing fails, exit silently (don't break the turn).
PAYLOAD_EXPORTS="$(cat | bash "${SCRIPT_DIR}/codex-bridge.sh" hook-read 2>/dev/null)" || {
  echo '{}'  # empty hookSpecificOutput
  exit 0
}
eval "$PAYLOAD_EXPORTS"

# Find an active monitor spec matching this tool_use_id.
# Spec file convention: {goal-dir}/iterations/{NNN}-{action}-monitor.spec.json
# Contains: {tool_use_id, poll_cmd, timeout_seconds, started_at}
SPEC_FILE=""
if [ -n "${HOOK_TOOL_USE_ID:-}" ]; then
  SPEC_FILE="$(find . -path '*/iterations/*-monitor.spec.json' -type f 2>/dev/null \
    | while read -r f; do
        # Whitespace-tolerant JSON field match (covers both `: "id"` and `:"id"`).
        if grep -qE "\"tool_use_id\"[[:space:]]*:[[:space:]]*\"${HOOK_TOOL_USE_ID}\"" "$f" 2>/dev/null; then
          echo "$f"; break
        fi
      done)"
fi

# No matching spec → no-op (this PostToolUse hook fires for ALL tool calls;
# we only act when our spec is present).
if [ -z "$SPEC_FILE" ]; then
  echo '{}'
  exit 0
fi

# Read poll_cmd from the spec, run it, capture exit + output.
SPEC_FILE="$SPEC_FILE" "$PYBIN" - <<'PY'
import os, json, subprocess, time, sys

spec_path = os.environ["SPEC_FILE"]
result_path = spec_path.replace(".spec.json", ".result.json")
log_path    = spec_path.replace(".spec.json", ".log")

try:
    spec = json.load(open(spec_path))
except Exception as e:
    print(json.dumps({"hookSpecificOutput": {"additionalContext": f"[pursue-monitor] spec parse failed: {e}"}}))
    sys.exit(0)

poll_cmd = spec.get("poll_cmd", "")
if not poll_cmd:
    print(json.dumps({}))
    sys.exit(0)

# Check timeout — pursue spec sets timeout_seconds; if exceeded, write a
# timeout result and inject status.
started_at = spec.get("started_at_epoch", time.time())
timeout = int(spec.get("timeout_seconds", 600))
if time.time() - started_at > timeout:
    json.dump({"status": "timeout", "exit_code": 124, "evidence": f"poll exceeded {timeout}s"},
              open(result_path, "w"))
    print(json.dumps({"hookSpecificOutput": {"additionalContext": f"[pursue-monitor] {spec.get('action','?')} TIMEOUT after {timeout}s"}}))
    sys.exit(0)

# Run the poll command.
proc = subprocess.run(poll_cmd, shell=True, capture_output=True, text=True, timeout=60)
output = (proc.stdout or "") + (proc.stderr or "")
# Append to log for forensics.
with open(log_path, "a") as logf:
    logf.write(f"\n--- poll at {time.time():.0f} (exit {proc.returncode}) ---\n{output}\n")

# Decide: is this a terminal poll result?
# Convention: spec.terminal_when = "exit_zero" | "exit_nonzero" | "exit_any"
terminal_when = spec.get("terminal_when", "exit_zero")
terminal = False
if terminal_when == "exit_zero"    and proc.returncode == 0:  terminal = True
if terminal_when == "exit_nonzero" and proc.returncode != 0:  terminal = True
if terminal_when == "exit_any":                               terminal = True

if terminal:
    json.dump({"status": "done", "exit_code": proc.returncode,
               "evidence": output[-300:]},
              open(result_path, "w"))
    short_status = "PASS" if proc.returncode == 0 else f"FAIL (exit {proc.returncode})"
    print(json.dumps({"hookSpecificOutput": {
        "additionalContext": f"[pursue-monitor] {spec.get('action','?')}: {short_status} — see {result_path}"
    }}))
else:
    # Non-terminal: inject latest status line so the model knows we're still waiting.
    last_line = next((l for l in reversed(output.strip().split("\n")) if l.strip()), "(no output)")
    # Cap at 200 chars to avoid context burn.
    last_line = last_line[:200]
    print(json.dumps({"hookSpecificOutput": {
        "additionalContext": f"[pursue-monitor] {spec.get('action','?')}: still waiting — last: {last_line}"
    }}))
PY
