# Sourced by checks.sh. The chart and report must come from the statechart command (a TLC run), not a hand-drawn diagram.
set -u
report=$(grep -rlE '^TLC reached [0-9]+ states' --include=report.md model 2>/dev/null | head -1)
[ -n "$report" ] || { echo "no report.md from a TLC run under ./model"; exit 1; }
chart="$(dirname "$report")/chart.mmd"
[ -f "$chart" ] && grep -q '^stateDiagram-v2' "$chart" || { echo "no chart.mmd beside $report"; exit 1; }
grep -q '```mermaid' "$EVAL_OUTPUT" || { echo "the reply does not show the chart as a mermaid block"; exit 1; }
