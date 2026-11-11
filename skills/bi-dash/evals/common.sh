# Sourced by checks.sh. new_files: files the run created (paths relative to the run dir), compared with $EVAL_ORIG.
set -u
T=$(mktemp -d "${TMPDIR:-/tmp}/bi-dash-check.XXXXXX") || { echo "no temp dir"; exit 1; }
trap 'rm -rf "$T"' EXIT
new_files() {
  find . -type f | sed 's#^\./##' | while read -r f; do [ -e "$EVAL_ORIG/$f" ] || echo "$f"; done
}
# The run's own words: its final text plus every new text file it wrote.
said() {
  cat "$EVAL_OUTPUT"
  new_files | grep -Ei '\.(md|txt|csv)$' | while read -r f; do cat "$f"; done
}
# True when one new markdown or CSV table row (a line with | or ,) matches every pattern given.
row_with() {
  new_files | grep -Ei '\.(md|csv)$' | while read -r f; do grep -E '\||,' "$f"; done > "$T/rows"
  for p in "$@"; do grep -Ei -- "$p" "$T/rows" > "$T/next"; mv "$T/next" "$T/rows"; done
  [ -s "$T/rows" ]
}
