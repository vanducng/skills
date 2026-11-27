#!/bin/sh
# Frame the whole subject: the pair on the lens join is stitched (view.stitch "flow") or not shown on the join; the
# menu is a sign, aimed at, framed whole and held long enough to read; the group of five fits (fov 90-95, centred
# on them); the barrel, already whole in a flat clip, is not cropped.
. "$(dirname "$0")/../common.sh"
lists=$(edit_lists)
[ -n "$lists" ] || { echo "no edit list"; exit 1; }
for f in $lists; do
  python3 - "$f" <<'PY' || exit 1
import json, sys
f = sys.argv[1]; d = json.load(open(f))
def gap(a, b): return abs((float(a) - float(b) + 180) % 360 - 180)
def clip(s, n): return f"_{n}." in str(s.get("src", ""))
def yaws(v):
    if v.get("track"): return [float(k[1]) for k in v["track"]]
    return [float(v.get("yaw", 0)), float(v.get("yaw_end", v.get("yaw", 0)))]
seen = set()
for s in d["shots"]:
    v = s.get("view") or {}
    a, b = float(s.get("in", 0)), float(s.get("out", 0))
    if clip(s, 520) and a < 70 and b > 10:
        if any(gap(y, -95) <= 45 for y in yaws(v)):
            seen.add("pair")
            if v.get("stitch") != "flow":
                sys.exit(f"{f}: the pair sits on the lens join (yaw -95) and the shot is not stitched (view.stitch)")
    if clip(s, 521) and a < 40 and b > 5 and any(gap(y, 20) <= 30 for y in yaws(v)):
        seen.add("menu")
        if s.get("subject") != "sign": sys.exit(f"{f}: the menu shot does not say subject sign")
        if b - a < 4.7: sys.exit(f"{f}: the menu (9 words) is held {b - a:.1f} s; it needs 4.7 s")
        if not all(gap(y, 20) <= 10 for y in yaws(v)): sys.exit(f"{f}: the menu is not centred")
        if not 58 <= float(v.get("fov", 85)) <= 95: sys.exit(f"{f}: fov {v.get('fov')} does not hold the 50 deg menu whole")
    if clip(s, 522) and a < 50 and b > 0 and any(gap(y, -170) <= 45 for y in yaws(v)):
        seen.add("group")
        if not 90 <= float(v.get("fov", 85)) <= 95: sys.exit(f"{f}: fov {v.get('fov')} cannot hold the five (80 deg) with a margin")
        if not all(gap(y, -170) <= 10 for y in yaws(v)): sys.exit(f"{f}: the group is not centred (yaw -170)")
    if clip(s, 523) and a < 20 and b > 5:
        seen.add("barrel")
        if any(k in v for k in ("zoom", "scale", "w", "h")) or v.get("fit") == "crop":
            sys.exit(f"{f}: the barrel is whole in the source; the shot crops it")
missing = {"pair", "menu", "group", "barrel"} - seen
if missing: sys.exit(f"{f}: no shot of {', '.join(sorted(missing))}")
PY
done
echo ok
