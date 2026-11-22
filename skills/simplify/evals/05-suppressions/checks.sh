#!/usr/bin/env bash
# Lint suppressions hiding real code smells go with the code fixed; a style-only prettier-ignore stays.
f=src/stats.js
node --test >/dev/null 2>&1 || { echo "tests fail after the change"; exit 1; }
diff -r "$EVAL_ORIG/test" test >/dev/null || { echo "test/ was changed"; exit 1; }
grep -q "eslint-disable" "$f" && { echo "an eslint-disable suppression is still there"; exit 1; }
grep -q "started" "$f" && { echo "the unused variable behind the suppression is still there"; exit 1; }
grep -qE 'x !== x|x != x' "$f" && { echo "the self-compare is still there; use Number.isNaN"; exit 1; }
grep -q "prettier-ignore" "$f" || { echo "the style-only prettier-ignore was removed"; exit 1; }
echo ok
