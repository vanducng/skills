#!/usr/bin/env bash
# Run by the prompt (`bash setup.sh`): builds a repo whose feat branch changes a behaviour, fixed dates so shas repeat. No remote.
set -eu
export GIT_AUTHOR_NAME=dev GIT_AUTHOR_EMAIL=dev@example.test GIT_COMMITTER_NAME=dev GIT_COMMITTER_EMAIL=dev@example.test
export GIT_AUTHOR_DATE=2026-01-01T00:00:00Z GIT_COMMITTER_DATE=2026-01-01T00:00:00Z
git init -q -b main .
printf 'setup.sh\n.feat-head\n' > .gitignore
mkdir -p bin src
cat > bin/tool.js <<'X'
const { parse } = require("../src/opts");
const o = parse(process.argv.slice(2));
console.log(o.dryRun ? "would write" : "wrote");
X
cat > src/opts.js <<'X'
// `--dry` skips the write and prints what would happen.
exports.parse = argv => ({ dryRun: argv.includes("--dry") });
X
cat > README.md <<'X'
# tool

Run `node bin/tool.js --dry` to see what it would write without writing.
X
cat > CHANGELOG.md <<'X'
# Changelog

## 1.0.0
- Added `--dry`.
X
git add -A && git commit -q -m "base"
git checkout -q -b feat
cat > src/opts.js <<'X'
// `--dry` skips the write and prints what would happen.
exports.parse = argv => ({ dryRun: argv.includes("--dry-run") });
X
git add -A && git commit -q -m "feat: rename --dry to --dry-run"
git rev-parse feat > .feat-head
echo "repo ready: change on feat (checked out)"
