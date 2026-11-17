#!/usr/bin/env bash
# Print the JSON payload of a twg command. twg may print the JSON itself or a YAML summary
# whose output_files.stdout names a file holding it; this handles both.
#   twgj.sh <twg args...>        runs: twg <args> -o json
#   twgj.sh --from <saved-output>
set -euo pipefail

if [[ ${1:-} == --from ]]; then
  out=$(cat "${2:?usage: twgj.sh --from <file>}")
else
  out=$(twg "$@" -o json)
fi
case $out in
  \{* | \[*) printf '%s\n' "$out"; exit 0 ;;
esac
f=$(printf '%s\n' "$out" | sed -n 's/^[[:space:]]*stdout:[[:space:]]*"\{0,1\}\([^"]*\)"\{0,1\}[[:space:]]*$/\1/p' | head -n 1)
if [[ -z $f || ! -r $f ]]; then
  printf '%s\n' "$out" >&2
  echo "twgj.sh: no JSON payload in the twg output" >&2
  exit 1
fi
cat "$f"
