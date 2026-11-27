#!/bin/sh
# 360 views point at the people of the story, not at the empty path or the trees: every shot from a range where the
# notes place people looks within 45 degrees of them (a fixed view or a track), Ben's face excepted, and a shot of a
# range with nobody names its landmark.
. "$(dirname "$0")/../common.sh"
lists=$(edit_lists)
[ -n "$lists" ] || { echo "no edit list"; exit 1; }
for f in $lists; do
  python3 - "$f" <<'PY' || exit 1
import json, sys
f = sys.argv[1]; d = json.load(open(f))
# clip -> [(from, to, yaw at from, yaw at to)] where people are (Ben's face excluded)
people = {"410": [(0, 30, 150, 150), (30, 90, 120, 60), (150, 220, -100, -100)],
          "411": [(0, 80, 30, 30), (160, 240, -60, -60)]}
empty = {"410": [(90, 150)], "411": [(80, 160)]}
def gap(a, b): return abs((a - b + 180) % 360 - 180)
def views(s):
    v = s.get("view") or {}
    tr = v.get("track")
    if tr: return [(float(s["in"]) + float(k[0]), float(k[1])) for k in tr]
    y0, y1 = float(v.get("yaw", 0)), float(v.get("yaw_end", v.get("yaw", 0)))
    return [(float(s["in"]), y0), (float(s["out"]), y1)]
checked = 0
for s in d["shots"]:
    if "src" not in s: continue
    clip = next((k for k in people if f"_{k}." in s["src"]), None)
    if not clip: continue
    a, b = float(s["in"]), float(s["out"])
    for p0, p1, y0, y1 in people[clip]:
        if a < p1 and b > p0:
            for t, yaw in views(s):
                t = min(max(t, p0), p1)
                want = y0 + (y1 - y0) * (t - p0) / max(p1 - p0, 1)
                if gap(yaw, want) > 45:
                    sys.exit(f"{f}: clip {clip} {a:.0f}-{b:.0f} looks at yaw {yaw:.0f} at {t:.0f} s; the people are at {want:.0f}")
            checked += 1
    for e0, e1 in empty[clip]:
        if a < e1 and b > e0 and (min(b, e1) - max(a, e0)) > 3 and not s.get("landmark"):
            sys.exit(f"{f}: clip {clip} {a:.0f}-{b:.0f} shows nobody and names no landmark")
if checked < 2: sys.exit(f"{f}: fewer than two shots of the people")
PY
done
echo ok
