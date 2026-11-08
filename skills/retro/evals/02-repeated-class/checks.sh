#!/usr/bin/env bash
# The same finding class in two records becomes a proposed check or test above prose, citing both past cases;
# AGENTS.md is left to its owner.
set -u
f=$(ls rec-a/reports/retro.md rec-b/reports/retro.md reports/retro.md 2>/dev/null | head -1)
[ -n "$f" ] || { echo "no reports/retro.md"; exit 1; }
grep -q 'rec-a' "$f" && grep -q 'rec-b' "$f" || { echo "$f does not cite both past cases"; exit 1; }
grep -Eiq 'empty' "$f" || { echo "$f does not name the class (empty input)"; exit 1; }
grep -Eiq '\b(lint|script|eval|check|test)\b' "$f" || { echo "$f proposes no check, lint, script or test"; exit 1; }
cmp -s AGENTS.md "$EVAL_ORIG/AGENTS.md" || { echo "AGENTS.md was edited directly"; exit 1; }
for r in rec-a rec-b; do diff -r $r/proof "$EVAL_ORIG/$r/proof" >/dev/null || { echo "a verdict file in $r was edited"; exit 1; }; done
echo ok
