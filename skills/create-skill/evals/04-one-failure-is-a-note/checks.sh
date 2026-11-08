#!/usr/bin/env bash
# Clean case: one failure changes nothing in the skill, and the answer says it is one failure.
diff -r "$EVAL_ORIG/skills" skills >/dev/null || { echo "the skill changed after a single failure"; exit 1; }
grep -qiE "once|one (failure|row|time|evidence)|single|twice|two (failure|row|evidence)|second" "$EVAL_OUTPUT" || { echo "the answer does not mention the evidence count"; exit 1; }
