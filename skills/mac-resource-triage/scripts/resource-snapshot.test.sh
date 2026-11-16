#!/usr/bin/env bash
# footprint_by_app ranks by top's footprint, not RSS: a daemon whose pages sit in swap still comes first.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=resource-snapshot.sh
source "$here/resource-snapshot.sh"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
printf '%s\n' '109 39G 36G' '200 512M+ 10M' '201 1536M 1G-' '300 900K 0B' >"$tmp/top"
printf '%s\n' '109 /usr/sbin/fseventsd' '200 /Applications/Aside.app/Contents/MacOS/Aside' \
  '201 /Applications/Aside.app/Contents/Frameworks/Aside Helper (Renderer).app/Contents/MacOS/Aside Helper (Renderer)' \
  '300 /bin/zsh' >"$tmp/ps"
out="$(footprint_by_app "$tmp/top" "$tmp/ps" | sort -k1 -rn)"
first="$(head -1 <<<"$out")"
[[ "$first" == *"39936 MB   36864 MB     1  fseventsd" ]] || { echo "FAIL first row: $first"; exit 1; }
grep -q "2048 MB    1034 MB     2  Aside.app" <<<"$out" || { echo "FAIL Aside grouping:"; echo "$out"; exit 1; }
grep -q "     1 MB       0 MB     1  zsh" <<<"$out" || { echo "FAIL zsh row:"; echo "$out"; exit 1; }
echo "ok"
