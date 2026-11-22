#!/usr/bin/env bash
. "$(dirname "$0")/../bot-checks.sh"

reply_ok; headline_first; tables_narrow
[ -s card.json ] || { echo "no question card (card.json)"; exit 1; }
python3 - <<'PY2' || exit 1
import json, sys
c = json.load(open("card.json"))
pages = c.get("pages") if isinstance(c, dict) else None
if not isinstance(pages, list) or len(pages) != 3: sys.exit(f"want one card with 3 pages, got {len(pages) if isinstance(pages, list) else c!r}")
for p in pages:
    if len(p.get("options") or []) < 2 or not p.get("recommended"): sys.exit(f"page without options or a recommendation: {p.get('question')!r}")
PY2
n=$(grep -Ec '^\*\*Decision [0-9]|^- \*\*[A-C]\*\* ' reply.md); [ "$n" = 0 ] || { echo "decisions repeated as text cards next to the question card"; exit 1; }
echo ok
