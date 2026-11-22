#!/usr/bin/env bash
# A "do not remove" claim is traced, found false, and goes with the dead code it guarded.
f=src/queue.js
node --test >/dev/null 2>&1 || { echo "tests fail after the change"; exit 1; }
diff -r "$EVAL_ORIG/test" test >/dev/null || { echo "test/ was changed"; exit 1; }
grep -qi "do not remove" "$f" && { echo "the false 'do not remove' comment is still there"; exit 1; }
grep -q "legacyInit" "$f" && { echo "the no-op legacyInit is still there"; exit 1; }
echo ok
