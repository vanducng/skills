#!/usr/bin/env bash
# Convert a pixel in `agent-desktop screenshot --screen N` output to the global point `mouse-click --xy` takes.
# Usage: shot-xy.sh <screen-index> <px> <py>   (DISPLAYS_JSON=<file> reads saved list-displays output)
set -euo pipefail
[[ $# -eq 3 ]] || { echo "usage: $0 <screen-index> <px> <py>" >&2; exit 2; }

if [[ -n "${DISPLAYS_JSON:-}" ]]; then json=$(cat "$DISPLAYS_JSON"); else json=$(agent-desktop list-displays); fi

DISPLAYS="$json" python3 - "$1" "$2" "$3" <<'PY'
import json, math, os, sys
i, px, py = int(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
d = json.loads(os.environ["DISPLAYS"])
if not d.get("ok"):
    sys.exit(f"list-displays failed: {d.get('error')}")
displays = d["data"]
if not 0 <= i < len(displays):
    sys.exit(f"screen index {i} out of range 0..{len(displays) - 1}")
b, s = displays[i]["bounds"], displays[i].get("scale") or 1.0
if not (0 <= px < b["width"] * s and 0 <= py < b["height"] * s):
    sys.exit(f"pixel {px:g},{py:g} is outside screen {i} ({b['width'] * s:g}x{b['height'] * s:g} px)")
print(f"{math.floor(b['x'] + px / s)},{math.floor(b['y'] + py / s)}")
PY
