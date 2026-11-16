#!/usr/bin/env bash
set -u
o=$(cat "$EVAL_OUTPUT")
grep -qE '(rpass\.py|\$S) share' <<<"$o" || { echo "no share command"; exit 1; }
for s in "--name shop-keys" "--access manage" "--access view" "Platform Team" "Jane Doe" "--account u1"; do
  grep -qF -- "$s" <<<"$o" || { echo "missing: $s"; exit 1; }
done
