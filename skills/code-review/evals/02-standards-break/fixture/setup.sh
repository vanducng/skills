#!/usr/bin/env bash
# Sourced by each fixture's setup.sh: a repo with main (the base) and feat (the change), fixed dates so shas repeat.
set -eu
export GIT_AUTHOR_NAME=dev GIT_AUTHOR_EMAIL=dev@example.test GIT_COMMITTER_NAME=dev GIT_COMMITTER_EMAIL=dev@example.test
export GIT_AUTHOR_DATE=2026-01-01T00:00:00Z GIT_COMMITTER_DATE=2026-01-01T00:00:00Z
git init -q -b main .
printf 'record/\nbin/\ncalls.log\n.feat-head\nsetup.sh\n' > .gitignore
mkdir -p src
cat > src/log.js <<'J'
module.exports = { info: msg => process.stderr.write(`[info] ${msg}\n`) };
J
cat > src/greet.js <<'J'
module.exports = function greet(name) {
  return "Hi " + name;
};
J
cat > REVIEW.md <<'J'
# Review rules
1. No `console.log` in `src/`: use `src/log.js`.
2. Every exported function has a test in `test/`.
J
git add -A && git commit -q -m "base"
git checkout -q -b feat
mkdir -p record
cat > record/SPEC.md <<'J'
---
id: demo.greet
intent: "Greet a person by name, and greet a stranger when no name is given."
---
# Greeting

## Mini-requirements

1. `greet("Ada")` returns `"Hello, Ada!"`.
2. `greet("")` returns `"Hello, there!"`.

## Proof contract

- [ ] `test/greet.test.js` covers every mini-requirement and `node --test` passes.
J
cat > src/greet.js <<'J'
module.exports = function greet(name) {
  console.log("greet called with", name);
  return name ? `Hello, ${name}!` : "Hello, there!";
};
J
mkdir -p test
cat > test/greet.test.js <<'J'
const test = require("node:test"), assert = require("node:assert"), greet = require("../src/greet");
test("names", () => assert.equal(greet("Ada"), "Hello, Ada!"));
test("stranger", () => assert.equal(greet(""), "Hello, there!"));
J
git add -A && git commit -q -m "change"
git rev-parse feat > .feat-head
echo "repo ready: base main, change on feat (checked out)"
