#!/bin/sh
# Clean case: a rename is a title-only update. The body stays untouched and is not re-sent.
cmp -s body.html "$EVAL_ORIG/body.html" || { echo "body.html changed"; exit 1; }
[ -f rename.sh ] || { echo "no rename.sh"; exit 1; }
grep -Eq 'confluence +content +update' rename.sh || { echo "rename.sh does not update the page"; exit 1; }
grep -q -- '--title' rename.sh && grep -qF 'Sprint 42 report (final)' rename.sh || { echo "no --title with the new name"; exit 1; }
grep -q -- '--snapshot-token' rename.sh || { echo "no --snapshot-token"; exit 1; }
grep -Eq -- '--body(-file)?[ =]' rename.sh && { echo "rename re-sends the body"; exit 1; }
new_html=$(find . -name '*.html' | sed 's#^\./##' | while read -r f; do [ -e "$EVAL_ORIG/$f" ] || echo "$f"; done)
[ -z "$new_html" ] || { echo "wrote a new body: $new_html"; exit 1; }
echo ok
