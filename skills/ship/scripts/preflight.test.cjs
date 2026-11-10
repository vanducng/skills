// node --test skills/ship/scripts/preflight.test.cjs
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const P = path.join(__dirname, "preflight.cjs");
const ENV = { HOME: os.tmpdir(), GIT_CONFIG_GLOBAL: "/dev/null", GIT_CONFIG_SYSTEM: "/dev/null",
  GIT_AUTHOR_NAME: "t", GIT_AUTHOR_EMAIL: "t@example.test", GIT_COMMITTER_NAME: "t", GIT_COMMITTER_EMAIL: "t@example.test" };
const git = (cwd, ...a) => { const r = spawnSync("git", a, { cwd, env: { ...ENV, PATH: process.env.PATH }, encoding: "utf8" }); assert.equal(r.status, 0, r.stderr); };
const write = (dir, files) => { for (const [f, body] of Object.entries(files)) { fs.mkdirSync(path.dirname(path.join(dir, f)), { recursive: true }); fs.writeFileSync(path.join(dir, f), body); } };

// A repo whose base has `base` files and whose branch `feat` adds `change`. A fake `gh` on PATH prints `prs` for `pr list`.
function repo(base, change, prs = []) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "preflight-")), bin = path.join(dir, ".bin");
  git(dir, "init", "-q", "-b", "main"); write(dir, { "README.md": "base\n", ...base });
  git(dir, "add", "-A"); git(dir, "commit", "-q", "-m", "base"); git(dir, "checkout", "-q", "-b", "feat");
  write(dir, change); git(dir, "add", "-A"); git(dir, "commit", "-q", "-m", "change");
  fs.appendFileSync(path.join(dir, ".git", "info", "exclude"), ".bin/\n");
  fs.mkdirSync(bin); fs.writeFileSync(path.join(bin, "gh"), `#!/bin/sh\ncat <<'EOF'\n${JSON.stringify(prs)}\nEOF\n`, { mode: 0o755 });
  return dir;
}
const run = (cwd, ...a) => { const r = spawnSync(process.execPath, [P, ...a], { cwd, env: { ...ENV, PATH: `${path.join(cwd, ".bin")}:${process.env.PATH}` }, encoding: "utf8" }); return { code: r.status, out: r.stdout, err: r.stderr }; };

test("overlap: names the other open PRs that touch the same files, skips this branch's own PR, never blocks", () => {
  const prs = [
    { number: 11, title: "Other change to the export", headRefName: "other", files: [{ path: "src/export.js" }, { path: "src/x.js" }] },
    { number: 12, title: "Unrelated", headRefName: "unrelated", files: [{ path: "docs/a.md" }] },
    { number: 13, title: "This branch", headRefName: "feat", files: [{ path: "src/export.js" }] },
  ];
  const r = run(repo({ "src/export.js": "a\n" }, { "src/export.js": "b\n" }, prs), "overlap", "--base", "main", "--repo", "o/r");
  assert.equal(r.code, 0, r.err);
  assert.match(r.out, /#11 Other change to the export: src\/export\.js/);
  assert.doesNotMatch(r.out, /#12|#13/);
  const none = run(repo({}, { "src/new.js": "x\n" }, prs), "overlap", "--base", "main", "--repo", "o/r");
  assert.equal(none.code, 0); assert.match(none.out, /no other open PR touches these files/);
});

test("tests: one line per touched package with its test command; a root-only repo gets one line", () => {
  const dir = repo({
    "package.json": JSON.stringify({ scripts: { test: "node --test" } }),
    "tools/pyproject.toml": "[tool.pytest.ini_options]\n",
    "svc/go.mod": "module svc\n",
  }, { "src/a.js": "x\n", "tools/src/b.py": "x\n", "svc/c.go": "x\n", "docs/d.md": "x\n" });
  const r = run(dir, "tests", "--base", "main");
  assert.equal(r.code, 0, r.err);
  assert.deepEqual(r.out.trim().split("\n"), ["- `npm test`", "- `cd svc && go test ./...`", "- `cd tools && pytest`"]);
  fs.writeFileSync(path.join(dir, "svc", "new.go"), "x\n"); fs.writeFileSync(path.join(dir, "README.md"), "edited\n");
  assert.equal(run(dir, "tests", "--base", "main").out, r.out, "uncommitted work counts too");
  const one = run(repo({ "package.json": JSON.stringify({ scripts: { test: "node --test" } }) }, { "a.js": "x\n" }), "tests", "--base", "main");
  assert.equal(one.out.trim(), "- `npm test`");
});

test("tests --run: runs each command and marks it pass or failed; a failure exits 1", () => {
  const dir = repo({ "Makefile": "test:\n\t@true\n", "bad/Makefile": "test:\n\t@false\n" }, { "x.js": "x\n", "bad/y.js": "y\n" });
  const r = run(dir, "tests", "--base", "main", "--run");
  assert.equal(r.code, 1);
  assert.match(r.out, /- `make test`: pass/);
  assert.match(r.out, /- `cd bad && make test`: failed \(exit 2\)/);
});

test("tests: a docs-only change needs no test command; an untested package is named", () => {
  assert.match(run(repo({}, { "docs/a.md": "x\n" }), "tests", "--base", "main").out, /docs only/);
  const r = run(repo({}, { "src/a.js": "x\n" }), "tests", "--base", "main");
  assert.equal(r.code, 0); assert.match(r.out, /no test command found for: src/);
});
