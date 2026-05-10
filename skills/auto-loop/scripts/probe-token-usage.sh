#!/usr/bin/env bash
# probe-token-usage.sh — feature-detect token-usage source.
#
# Sources, in priority order:
#   1. ccusage CLI if installed (exact)
#   2. statusline payload via stdin if hook provides one (exact)
#   3. Fallback estimate: iteration count × per-iter constant (fallback)
#
# Usage: probe-token-usage.sh <iter> <workspace>
# Stdout: JSON `{"tokens_used": <int>, "source": "ccusage|statusline|fallback", "fidelity": "exact|approximate|fallback"}`

set -uo pipefail

iter="${1:?iter required}"
ws="${2:?workspace required}"

if command -v ccusage >/dev/null 2>&1; then
  raw=$(ccusage --json 2>/dev/null || true)
  if [[ -n "$raw" ]]; then
    tokens=$(printf '%s' "$raw" | jq -r '.session.tokens // .total_tokens // 0' 2>/dev/null || echo 0)
    if [[ "$tokens" -gt 0 ]]; then
      jq -nc --argjson t "$tokens" '{tokens_used: $t, source: "ccusage", fidelity: "exact"}'
      exit 0
    fi
  fi
fi

# Fallback: rough estimate.
# Empirical: ~25K tokens per loop iteration for moderately verbose code work.
PER_ITER_EST="${VD_AUTOLOOP_TOKENS_PER_ITER:-25000}"
est=$(( iter * PER_ITER_EST ))
jq -nc --argjson t "$est" '{tokens_used: $t, source: "fallback", fidelity: "fallback"}'
exit 0
