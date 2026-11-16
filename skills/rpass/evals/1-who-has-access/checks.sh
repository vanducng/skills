#!/usr/bin/env bash
set -u
grep -qE '(rpass\.py|\$S) access' "$EVAL_OUTPUT" || { echo "no access command"; exit 1; }
for s in "--account u1" "--name api-keys"; do grep -qF -- "$s" "$EVAL_OUTPUT" || { echo "missing: $s"; exit 1; }; done
