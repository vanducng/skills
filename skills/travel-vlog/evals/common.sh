# Sourced by checks.sh. new_files: files the run created (paths relative to the run dir), compared with $EVAL_ORIG.
set -u
new_files() {
  find . -type f | sed 's#^\./##' | while read -r f; do [ -e "$EVAL_ORIG/$f" ] || echo "$f"; done
}
# Edit lists the run wrote: new JSON files that have a "shots" list.
edit_lists() {
  new_files | grep -E '\.json$' | while read -r f; do
    python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if isinstance(d,dict) and isinstance(d.get("shots"),list) else 1)' "$f" 2>/dev/null && echo "$f"
  done
}
