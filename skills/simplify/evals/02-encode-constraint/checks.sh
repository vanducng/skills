#!/usr/bin/env bash
# The "DO NOT REORDER" comment becomes a test that fails when the order is swapped, then the comment goes.
node --test >/dev/null 2>&1 || { echo "tests fail after the change"; exit 1; }
grep -qi "do not reorder" src/pipeline.js && { echo "the DO NOT REORDER comment is still there (not encoded and deleted)"; exit 1; }
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
cp -R . "$t/"
# Swap the two steps wherever the list is written, then the tests must fail.
perl -0pi -e 's/\[\s*validate\s*,\s*save\s*\]/[save, validate]/g' "$t/src/pipeline.js"
grep -q "\[save, validate\]" "$t/src/pipeline.js" || { echo "cannot find the step list to swap: [validate, save]"; exit 1; }
(cd "$t" && node --test >/dev/null 2>&1) && { echo "swapping the steps passes every test: the rule is not encoded"; exit 1; }
echo ok
