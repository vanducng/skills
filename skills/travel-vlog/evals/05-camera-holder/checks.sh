#!/bin/sh
# The camera holder (Ben, yaw about 180 on the 360 clips) stays behind the camera: under 15 s of his face in all, no
# stretch over 6 s, and the thumbnail looks at the place or the moment, not at him.
. "$(dirname "$0")/../common.sh"
lists=$(edit_lists)
[ -n "$lists" ] || { echo "no edit list"; exit 1; }
for f in $lists; do
  python3 - "$f" <<'PY' || exit 1
import json, sys
def length(s):
    if s.get("still") or s.get("kind") == "still":
        return float(s["dur"]) if "dur" in s else (float(s.get("out", 4)) - float(s.get("in", 0))) / float(s.get("speed", 1))
    return (float(s["out"]) - float(s["in"])) / float(s.get("speed", 1))
f = sys.argv[1]; d = json.load(open(f))
def face(v):
    v = v or {}
    if "yaw" not in v: return False
    return abs(((float(v["yaw"]) - 180) + 180) % 360 - 180) < 60
total = run = 0.0
for s in d["shots"]:
    dur = length(s)
    on = face(s.get("view")) or s.get("holder")
    run = run + dur if on else 0.0
    total += dur if on else 0.0
    if run > 6: sys.exit(f"{f}: Ben's face runs {run:.0f} s in a row")
if total > 15: sys.exit(f"{f}: Ben's face is on screen {total:.0f} s")
th = d.get("thumbnail") or {}
if not th: sys.exit(f"{f}: no thumbnail block")
if face(th.get("view")) or th.get("holder"): sys.exit(f"{f}: the thumbnail looks at Ben")
PY
done
echo ok
