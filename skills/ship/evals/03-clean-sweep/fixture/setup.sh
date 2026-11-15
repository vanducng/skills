#!/usr/bin/env bash
# Run by the prompt (`bash setup.sh`): builds a repo whose feat branch changes a behaviour, fixed dates so shas repeat. No remote.
set -eu
export GIT_AUTHOR_NAME=dev GIT_AUTHOR_EMAIL=dev@example.test GIT_COMMITTER_NAME=dev GIT_COMMITTER_EMAIL=dev@example.test
export GIT_AUTHOR_DATE=2026-01-01T00:00:00Z GIT_COMMITTER_DATE=2026-01-01T00:00:00Z
git init -q -b main .
printf 'setup.sh\n.feat-head\n' > .gitignore
mkdir -p src
cat > src/opts.js <<'X'
exports.parse = argv => ({ verbose: argv.includes("--verbose") });
X
cat > README.md <<'X'
# tool

`--verbose` prints each step.
X
git add -A && git commit -q -m "base"
git checkout -q -b feat
cat > src/opts.js <<'X'
exports.parse = argv => ({ verbose: argv.includes("--verbose") || argv.includes("-v") });
X
cat > README.md <<'X'
# tool

`--verbose` (or `-v`) prints each step.
X
git add -A && git commit -q -m "feat: -v as a short form of --verbose"
git rev-parse feat > .feat-head
echo "repo ready: change on feat (checked out)"
