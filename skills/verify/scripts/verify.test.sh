#!/usr/bin/env bash
# Tests for both.sh, new-verify-app.cjs and stale.cjs on a throwaway repo.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
fail() { echo "FAIL: $*"; exit 1; }
cd "$t"
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@example.test GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@example.test
git init -q -b main
printf 'module.exports = (a, b) => a - b;\n' > add.js
printf '{"name":"demo","scripts":{"start":"node add.js","test":"node test/t.js"}}\n' > package.json
git add -A && git commit -qm base
git checkout -qb feat
printf 'module.exports = (a, b) => a + b;\n' > add.js
mkdir test && printf 'require("assert").equal(require("../add")(2, 2), 4);\n' > test/t.js
git add -A && git commit -qm fix
j() { node -e 'const d=require(process.argv[1]); console.log(process.argv[2].split(".").reduce((o,k)=>o[k],d))' "$t/$1" "$2"; }

bash "$here/both.sh" --base main --out m1.json --from-head test/t.js -- node test/t.js >/dev/null
[ "$(j m1.json outcome)" = fixed ] || fail "--from-head: want fixed"
[ "$(j m1.json parent.sha)" = "$(git rev-parse main)" ] || fail "parent sha is not the merge-base"
grep -q AssertionError "$(dirname m1.json)/$(j m1.json parent.log)" || fail "parent did not fail on the assertion"
echo "ok both.sh --from-head runs the new check on the old code"

bash "$here/both.sh" --base main --out m2.json -- node test/t.js >/dev/null
grep -q "Cannot find module" "$(j m2.json parent.log)" || fail "without --from-head the parent should miss the file"
echo "ok both.sh without --from-head records the missing file"

[ "$(git worktree list | wc -l | tr -d ' ')" = 1 ] || fail "temporary worktrees left behind"
echo "ok both.sh removes its worktrees"

node "$here/new-verify-app.cjs" demo --repo . --out skills >/dev/null
grep -q '`npm test`' skills/verify-demo/SKILL.md || fail "new: npm test missing"
node "$here/stale.cjs" skills/verify-demo --repo . >/dev/null || fail "fresh skill reported stale"
printf '{"name":"demo","scripts":{"start":"node add.js"}}\n' > package.json
if node "$here/stale.cjs" skills/verify-demo --repo . >/dev/null; then fail "a removed script was not reported"; fi
echo "ok new-verify-app writes the table and stale.cjs catches a removed command"
