#!/usr/bin/env bash
# Run by the prompt (`bash setup.sh`): builds a repo whose feat branch changes a behaviour, fixed dates so shas repeat. No remote.
set -eu
export GIT_AUTHOR_NAME=dev GIT_AUTHOR_EMAIL=dev@example.test GIT_COMMITTER_NAME=dev GIT_COMMITTER_EMAIL=dev@example.test
export GIT_AUTHOR_DATE=2026-01-01T00:00:00Z GIT_COMMITTER_DATE=2026-01-01T00:00:00Z
git init -q -b main .
printf 'setup.sh\n.feat-head\n' > .gitignore
mkdir -p src docs
cat > src/fetch.js <<'X'
/** Fetches a URL. Gives up after the default timeout of 30 seconds. */
exports.fetchUrl = (url, { timeoutMs = 30000 } = {}) => ({ url, timeoutMs });
X
cat > docs/config.md <<'X'
# Config

`timeoutMs` defaults to 30000 (30 seconds).
X
git add -A && git commit -q -m "base"
git checkout -q -b feat
cat > src/fetch.js <<'X'
/** Fetches a URL. Gives up after the default timeout of 30 seconds. */
exports.fetchUrl = (url, { timeoutMs = 60000 } = {}) => ({ url, timeoutMs });
X
git add -A && git commit -q -m "fix: raise the fetch timeout default to 60 s"
git rev-parse feat > .feat-head
echo "repo ready: change on feat (checked out)"
