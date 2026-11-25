# Sourced by checks.sh. The stub aside logs every call to .aside-log.jsonl in the run dir.
set -u
LOG=.aside-log.jsonl
CHANNEL=UCq3Kp9VxL2mT8wR4nB6yZ1a
fail() { echo "$*"; exit 1; }
calls() { [ -f "$LOG" ] && jq -c "select(.script == \"$1\")" "$LOG" || true; }
