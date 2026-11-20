#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
export DISPLAYS_JSON="$here/../evals/2-window-shot-coordinates/fixture/displays.json"
s="$here/shot-xy.sh"

[[ $("$s" 0 0 0) == "0,0" ]]
[[ $("$s" 0 5119 2879) == "2559,1439" ]]
[[ $("$s" 1 1000 600) == "1095,1740" ]]
! "$s" 1 3024 10 2>/dev/null
! "$s" 2 1 1 2>/dev/null
echo "shot-xy: ok"
