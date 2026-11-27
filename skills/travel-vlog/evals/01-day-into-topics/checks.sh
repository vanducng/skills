#!/bin/sh
# A day becomes 2+ topic videos, each named <series>-d<dd>-<nn>-<slug>, titled '<Series> · Day <d> · <Topic>', 3-6 min, a title or hook on shot 1, which is held at least 4 s
# (the establishing shot).
. "$(dirname "$0")/../common.sh"
lists=$(edit_lists)
n=$(printf '%s\n' "$lists" | grep -c . || true)
[ "$n" -ge 2 ] || { echo "expected two or more edit lists, found $n"; exit 1; }
for f in $lists; do
  python3 - "$f" <<'PY' || exit 1
import json, re, sys, pathlib
f = sys.argv[1]; d = json.load(open(f))
stem = pathlib.Path(f).stem
if not re.fullmatch(r"jp27-d03-\d{2}-[a-z0-9]+(-[a-z0-9]+)*", stem): sys.exit(f"{f}: file name is not jp27-d03-<nn>-<slug>")
if d.get("stem") != stem: sys.exit(f"{f}: stem field {d.get('stem')!r} differs from the file name")
if not re.fullmatch(r"Jp27 · Day 3 · .+|JP27 · Day 3 · .+|Japan 2027 · Day 3 · .+", d.get("title", "")): sys.exit(f"{f}: title {d.get('title')!r} is not '<Series> · Day 3 · <Topic>'")
total = sum((float(s["dur"]) if (s.get("still") or s.get("kind") == "still") and "dur" in s else (float(s["out"]) - float(s["in"])) / float(s.get("speed", 1))) for s in d["shots"])
if not 180 <= total <= 360: sys.exit(f"{f}: {total:.0f} s is outside 3-6 min")
first = d["shots"][0]
if not (first.get("hook") or first.get("title")): sys.exit(f"{f}: shot 1 has no hook or title")
if (float(first["out"]) - float(first["in"])) / float(first.get("speed", 1)) < 4: sys.exit(f"{f}: shot 1 is under 4 s; open on a held establishing shot")
PY
done
echo ok
