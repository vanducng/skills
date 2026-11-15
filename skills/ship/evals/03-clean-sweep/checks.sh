#!/usr/bin/env bash
# The change already updated its docs: no new commit and no edit.
[ "$(git rev-parse feat)" = "$(cat .feat-head)" ] || { echo "feat moved on a clean change: $(git log --oneline "$(cat .feat-head)..feat" | head -3)"; exit 1; }
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "tracked files were edited"; exit 1; }
echo ok
