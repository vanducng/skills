#!/usr/bin/env bash
# append-journal.sh — write plans/goals/{slug}/iterations/NNN-{action}.md.
#
# Usage:
#   append-journal.sh --goal-dir <dir> --action <name> --exit-code <int>
#                     [--evidence-file <path>] [--verifier-pass <true|false>]
#                     [--verifier-evidence <text>]
#
# Computes NNN = 1 + count of existing iterations/NNN-*.md files (zero-padded
# to 3 digits). Returns the iteration N on stdout.
#
# Idempotent on the file level — refuses to overwrite an existing iteration.
# Caller is expected to use the returned N for any subsequent reads.

set -euo pipefail

GOAL_DIR=""
ACTION=""
EXIT_CODE=""
EVIDENCE_FILE=""
VERIFIER_PASS=""
VERIFIER_EVIDENCE=""
CODEX_JSONL=""

while [ $# -gt 0 ]; do
  case "$1" in
    --goal-dir)          GOAL_DIR="${2:?}"; shift 2 ;;
    --action)            ACTION="${2:?}"; shift 2 ;;
    --exit-code)         EXIT_CODE="${2:?}"; shift 2 ;;
    --evidence-file)     EVIDENCE_FILE="${2:-}"; shift 2 ;;
    --verifier-pass)     VERIFIER_PASS="${2:-}"; shift 2 ;;
    --verifier-evidence) VERIFIER_EVIDENCE="${2:-}"; shift 2 ;;
    --codex-jsonl)       CODEX_JSONL="${2:-}"; shift 2 ;;
    --help|-h)
      echo "usage: append-journal.sh --goal-dir <dir> --action <name> --exit-code <int> [--evidence-file <p>] [--verifier-pass <t|f>] [--verifier-evidence <s>] [--codex-jsonl <path>]"
      exit 0 ;;
    *) echo "append-journal.sh: unknown arg: $1" >&2; exit 2 ;;
  esac
done

[ -z "$GOAL_DIR" ]  && { echo "--goal-dir required" >&2; exit 2; }
[ -z "$ACTION" ]    && { echo "--action required" >&2; exit 2; }
[ -z "$EXIT_CODE" ] && { echo "--exit-code required" >&2; exit 2; }

ITER_DIR="${GOAL_DIR}/iterations"
mkdir -p "$ITER_DIR"

# Next iteration number = 1 + count of existing NNN-*.md
N=$(( $(find "$ITER_DIR" -maxdepth 1 -name '[0-9][0-9][0-9]-*.md' -type f 2>/dev/null | wc -l | tr -d ' ') + 1 ))
NNN="$(printf '%03d' "$N")"
TARGET="${ITER_DIR}/${NNN}-${ACTION}.md"

# Refuse to overwrite — should never happen given the count-based naming,
# but guard against concurrent writers.
[ -e "$TARGET" ] && { echo "append-journal.sh: $TARGET exists; refusing to overwrite" >&2; exit 4; }

NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Build evidence body — read evidence-file if provided, else use a short note.
EVIDENCE_BODY=""
if [ -n "$EVIDENCE_FILE" ] && [ -f "$EVIDENCE_FILE" ]; then
  EVIDENCE_BODY="$(head -c 4000 "$EVIDENCE_FILE")"
fi

# Codex session metrics — parse Codex --json stream if path provided
# (Phase 4 enrichment). Embedded into frontmatter for observability.
CODEX_METRICS_LINE=""
if [ -n "$CODEX_JSONL" ] && [ -f "$CODEX_JSONL" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  METRICS_JSON="$(bash "${SCRIPT_DIR}/codex-bridge.sh" json-parse "$CODEX_JSONL" 2>/dev/null || echo '{}')"
  CODEX_METRICS_LINE="codex_session_metrics: ${METRICS_JSON}"
fi

# Frontmatter + body
cat > "$TARGET" <<MD
---
iteration: ${N}
action: ${ACTION}
finished_at: ${NOW}
exit_code: ${EXIT_CODE}
verifier_pass: ${VERIFIER_PASS:-null}
${CODEX_METRICS_LINE}
---

# Iteration ${N} — ${ACTION}

**Exit code:** ${EXIT_CODE}
**Verifier:** ${VERIFIER_PASS:-(n/a)} — ${VERIFIER_EVIDENCE:-(no evidence)}

## Evidence

${EVIDENCE_BODY:-(no captured output)}
MD

echo "$N"
