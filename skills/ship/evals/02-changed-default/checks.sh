#!/usr/bin/env bash
# The default went from 30 s to 60 s: the docstring and docs/config.md now say 60, committed on feat.
[ "$(git rev-list --count "$(cat .feat-head)..feat")" -ge 1 ] || { echo "no commit on feat after the change"; exit 1; }
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "fixes left uncommitted"; exit 1; }
hits=$(git grep -n -E '30 ?seconds|30000|30 ?s\b' feat -- . || true)
[ -z "$hits" ] || { echo "old default still named: $hits"; exit 1; }
git grep -q -E '60' feat -- docs/config.md || { echo "docs/config.md does not give the new default"; exit 1; }
git show feat:src/fetch.js | grep -q 'timeoutMs = 60000' || { echo "the code itself changed"; exit 1; }
echo ok
