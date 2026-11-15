#!/usr/bin/env bash
# --dry became --dry-run: the README and the src comment now say --dry-run, committed on feat; the changelog keeps history.
git rev-parse --verify -q feat >/dev/null || { echo "no feat branch"; exit 1; }
[ "$(git rev-list --count "$(cat .feat-head)..feat")" -ge 1 ] || { echo "no commit on feat after the change"; exit 1; }
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "fixes left uncommitted"; exit 1; }
hits=$(git grep -n -E -e '--dry([^-]|$)' feat -- . ':!CHANGELOG.md' || true)
[ -z "$hits" ] || { echo "old flag still named: $hits"; exit 1; }
git grep -q -e '--dry-run' feat -- README.md || { echo "README does not name --dry-run"; exit 1; }
git diff --quiet "$(cat .feat-head)" feat -- CHANGELOG.md || { echo "the 1.0.0 changelog entry (history) was rewritten"; exit 1; }
[ "$(git show feat:src/opts.js | grep -c 'argv.includes("--dry-run")')" = 1 ] || { echo "the code itself changed"; exit 1; }
echo ok
