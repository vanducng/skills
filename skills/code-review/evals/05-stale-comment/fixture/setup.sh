#!/usr/bin/env bash
# Sourced by each fixture's setup.sh: a repo with main (the base) and feat (the change), fixed dates so shas repeat.
set -eu
export GIT_AUTHOR_NAME=dev GIT_AUTHOR_EMAIL=dev@example.test GIT_COMMITTER_NAME=dev GIT_COMMITTER_EMAIL=dev@example.test
export GIT_AUTHOR_DATE=2026-01-01T00:00:00Z GIT_COMMITTER_DATE=2026-01-01T00:00:00Z
git init -q -b main .
printf 'record/\nbin/\ncalls.log\n.feat-head\nsetup.sh\n' > .gitignore
mkdir -p src test
cat > src/retry.js <<'J2'
// Retries a failing call up to 3 times, waiting 100 ms between tries.
module.exports = async function retry(call) {
  for (let i = 0; ; i++) {
    try { return await call(); } catch (e) { if (i >= 2) throw e; }
    await new Promise(r => setTimeout(r, 100));
  }
};
J2
cat > test/retry.test.js <<'J2'
const test = require("node:test"), assert = require("node:assert"), retry = require("../src/retry");
test("gives up", async () => { let n = 0; await assert.rejects(retry(async () => { n++; throw new Error("x"); })); assert.ok(n >= 3); });
J2
cat > REVIEW.md <<'J2'
# Review rules
1. Every exported function has a test in `test/`.
J2
git add -A && git commit -q -m "base"
git checkout -q -b feat
mkdir -p record
cat > record/SPEC.md <<'J2'
---
id: demo.retry
intent: "Retry a failing call 5 times with a doubling wait, so a slow start-up does not fail the job."
---
# Retry with backoff

## Mini-requirements

1. `retry` tries a failing call 5 times in all, then throws the last error.
2. The waits between tries double: 100, 200, 400, 800 ms.

## Proof contract

- [ ] `test/retry.test.js` checks the try count and `node --test` passes.
J2
cat > src/retry.js <<'J2'
// Retries a failing call up to 3 times, waiting 100 ms between tries.
module.exports = async function retry(call) {
  for (let i = 0; ; i++) {
    try { return await call(); } catch (e) { if (i >= 4) throw e; }
    // wait
    await new Promise(r => setTimeout(r, 100 * 2 ** i));
  }
};
J2
cat > test/retry.test.js <<'J2'
const test = require("node:test"), assert = require("node:assert"), retry = require("../src/retry");
test("tries 5 times", async () => { let n = 0; await assert.rejects(retry(async () => { n++; throw new Error("x"); })); assert.equal(n, 5); });
J2
git add -A && git commit -q -m "change"
git rev-parse feat > .feat-head
echo "repo ready: base main, change on feat (checked out)"
