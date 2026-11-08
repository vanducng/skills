// node --test skills/code-review/scripts/verdict.test.cjs
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const crypto = require("node:crypto");
const { spawnSync } = require("node:child_process");

const V = path.join(__dirname, "verdict.cjs");
const ENV = { PATH: process.env.PATH, HOME: os.tmpdir(), GIT_CONFIG_GLOBAL: "/dev/null", GIT_CONFIG_SYSTEM: "/dev/null",
  GIT_AUTHOR_NAME: "t", GIT_AUTHOR_EMAIL: "t@example.test", GIT_COMMITTER_NAME: "t", GIT_COMMITTER_EMAIL: "t@example.test" };
const sh = (cwd, cmd, args, input) => spawnSync(cmd, args, { cwd, env: ENV, encoding: "utf8", input });
const git = (cwd, ...a) => { const r = sh(cwd, "git", a); assert.equal(r.status, 0, r.stderr); return r.stdout.trim(); };
const run = (cwd, ...a) => { const r = sh(cwd, process.execPath, [V, ...a]); return { code: r.status, out: r.stdout, err: r.stderr, json: () => JSON.parse(r.stdout) }; };

function repo(files) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "verdict-"));
  git(dir, "init", "-q", "-b", "main");
  fs.writeFileSync(path.join(dir, "README.md"), "base\n");
  git(dir, "add", "-A"); git(dir, "commit", "-q", "-m", "base");
  git(dir, "checkout", "-q", "-b", "feat");
  for (const [f, body] of Object.entries(files)) { fs.mkdirSync(path.dirname(path.join(dir, f)), { recursive: true }); fs.writeFileSync(path.join(dir, f), body); }
  git(dir, "add", "-A"); git(dir, "commit", "-q", "--allow-empty", "-m", "change");
  return dir;
}

test("tier: docs are Quick, a migration or CI change is Deep and needs the security axis", () => {
  assert.equal(run(repo({ "docs/a.md": "x\n" }), "tier", "--base", "main").json().tier, "Quick");
  const big = repo({ "src/a.js": "x\n".repeat(80) });
  assert.equal(run(big, "tier", "--base", "main").json().tier, "Standard");
  for (const f of ["db/migrations/1.sql", ".github/workflows/ci.yml", "src/auth/login.js", "infra/main.tf"]) {
    const t = run(repo({ [f]: "x\n" }), "tier", "--base", "main").json();
    assert.equal(t.tier, "Deep", f);
    assert.deepEqual(t.axes, ["spec", "standards", "security"], f);
  }
});

test("write binds the verdict to the same patch-id and digest a checker recomputes", () => {
  const dir = repo({ "src/a.js": "const a = 1;\n" });
  const r = run(dir, "write", "--base", "main", "--out", "proof/v.md", "--spec", "pass", "--standards", "pass", "--seat", "dev.review", "--family", "gpt");
  assert.equal(r.code, 0, r.err);
  assert.equal(r.json().verdict, "PASS");
  const text = fs.readFileSync(path.join(dir, "proof/v.md"), "utf8");
  const mb = git(dir, "merge-base", "main", "HEAD");
  const patch = sh(dir, "git", ["patch-id", "--stable"], git(dir, "diff", `${mb}..HEAD`) + "\n").stdout.split(" ")[0];
  const digest = crypto.createHash("sha256").update(spawnSync("git", ["diff", "--binary", `${mb}..HEAD`], { cwd: dir, env: ENV }).stdout).digest("hex");
  assert.match(text, new RegExp(`^patch_id: ${patch}$`, "m"));
  assert.match(text, new RegExp(`^diff_digest: "sha256:${digest}"$`, "m"));
  assert.match(text, /^axes: \{spec: pass, standards: pass\}$/m);
  assert.equal(run(dir, "check", "proof/v.md", "--base", "main").code, 0);
});

test("check catches a whitespace-only change that patch-id alone would miss", () => {
  const dir = repo({ "a.yml": "k:\n  v: 1\n" });
  run(dir, "write", "--base", "main", "--out", "v.md", "--spec", "pass", "--standards", "pass");
  fs.writeFileSync(path.join(dir, "a.yml"), "k:\n    v: 1\n");
  git(dir, "commit", "-q", "-am", "indent");
  const r = run(dir, "check", "v.md", "--base", "main");
  assert.equal(r.code, 1);
  assert.ok(r.json().stale.includes("diff_digest"));
});

test("write refuses a blended or impossible verdict", () => {
  const deep = repo({ "migrations/1.sql": "x\n" });
  assert.match(run(deep, "write", "--base", "main", "--out", "v.md", "--spec", "pass", "--standards", "pass").err, /Deep.*--security is required/);
  const dir = repo({ "a.js": "x\n" });
  assert.match(run(dir, "write", "--base", "main", "--out", "v.md", "--spec", "pass").err, /--standards is required/);
  assert.match(run(dir, "write", "--base", "main", "--out", "v.md", "--spec", "pass", "--standards", "pass", "--finding", "F1|spec|Important|open|x").err, /cannot pass with an open Important/);
  assert.match(run(dir, "write", "--base", "main", "--out", "v.md", "--spec", "pass", "--standards", "pass", "--finding", "F1|spec|Blocker|open|x").err, /tag/);
  const ok = run(dir, "write", "--base", "main", "--out", "v.md", "--spec", "fail", "--standards", "pass", "--finding", "F1|spec|Important|open|missing case");
  assert.equal(ok.json().verdict, "BLOCKING");
  assert.match(fs.readFileSync(path.join(dir, "v.md"), "utf8"), /- \{id: "F1", axis: spec, tag: Important, status: open, text: "missing case"\}/);
  assert.equal(run(dir, "write", "--base", "main", "--out", "v.md", "--spec", "inconclusive", "--standards", "pass").json().verdict, "NOT-CLEAR");
});

test("round counts prior verdicts and stops past round 3", () => {
  const dir = repo({ "a.js": "x\n" });
  assert.equal(run(dir, "round", "proof").json().round, 1);
  for (const n of [1, 2, 3]) run(dir, "write", "--base", "main", "--out", `proof/r${n}.md`, "--spec", "fail", "--standards", "pass", "--finding", "F1|spec|Important|open|x");
  fs.writeFileSync(path.join(dir, "proof", "notes.md"), "not a verdict\n");
  const r = run(dir, "round", "proof");
  assert.equal(r.code, 3);
  assert.match(r.out, /round cap/);
});

test("round counts only files whose leading block is a verdict, as the workspace check reads them", () => {
  const dir = repo({ "a.js": "x\n" });
  run(dir, "write", "--base", "main", "--out", "proof/r1.md", "--spec", "fail", "--standards", "pass", "--finding", "F1|spec|Important|open|x");
  fs.writeFileSync(path.join(dir, "proof", "example.md"), "# How to write one\n\naxes: {spec: pass, standards: pass}\n");
  fs.writeFileSync(path.join(dir, "proof", "c1.md"), "---\nslice: s\nverdict: PASS\n---\n---\naxes: {spec: pass, standards: pass}\n---\nbody\n");
  assert.equal(run(dir, "round", "proof").json().round, 3);
});

test("the security axis is Deep only, and an empty diff has nothing to judge", () => {
  const dir = repo({ "a.js": "x\n" });
  assert.match(run(dir, "write", "--base", "main", "--out", "v.md", "--spec", "pass", "--standards", "pass", "--security", "fail").err, /Deep axis and this change is Quick/);
  const empty = repo({});
  assert.match(run(empty, "tier", "--base", "main").err, /changes nothing/);
  assert.equal(run(empty, "write", "--base", "main", "--out", "v.md", "--spec", "pass", "--standards", "pass").code, 2);
});
test("round filters by seat, so another seat's verdict is not this seat's round", () => {
  const dir = repo({ "a.js": "x\n" });
  run(dir, "write", "--base", "main", "--out", "proof/other.md", "--spec", "fail", "--standards", "pass", "--seat", "other.review");
  const mine = run(dir, "round", "proof", "--seat", "me.review").json();
  assert.equal(mine.round, 1);
  assert.equal(mine.artifact_type, "rev1-r1");
  run(dir, "write", "--base", "main", "--out", "proof/mine.md", "--spec", "pass", "--standards", "pass", "--seat", "me.review");
  assert.equal(run(dir, "round", "proof", "--seat", "me.review").json().round, 2);
});

test("round 2 and later map to rev1-r2, the last type rig proof accepts, with the round in the file name", () => {
  const dir = repo({ "a.js": "x\n" });
  const slice = path.join(dir, "07-thing");
  fs.mkdirSync(path.join(slice, "proof"), { recursive: true });
  const proof = path.join("07-thing", "proof");
  for (const n of [1, 2, 3]) {
    const r = run(dir, "round", proof).json();
    assert.equal(r.round, n);
    assert.equal(r.artifact_type, n === 1 ? "rev1-r1" : "rev1-r2");
    assert.equal(r.proof_name, `07-thing-rev1-round${n}.md`);
    run(dir, "write", "--base", "main", "--out", path.join(proof, r.proof_name), "--spec", "fail", "--standards", "pass", "--finding", "F1|spec|Important|open|x");
  }
});

test("round --pr counts only that PR's verdicts, across seat names, and names the proof by PR", () => {
  const dir = repo({ "a.js": "x\n" });
  const slice = path.join(dir, "02-long");
  fs.mkdirSync(path.join(slice, "proof"), { recursive: true });
  const proof = path.join("02-long", "proof");
  const w = (out, ...extra) => run(dir, "write", "--base", "main", "--out", path.join(proof, out), "--spec", "fail", "--standards", "pass", ...extra);
  w("other-1.md", "--pr", "1430", "--seat", "dev.review"); w("other-2.md", "--pr", "1430", "--seat", "dev.review");
  const first = run(dir, "round", proof, "--pr", "1429").json();
  assert.deepEqual([first.round, first.artifact_type, first.proof_name], [1, "rev1-r1", "02-long-pr1429-rev1-round1.md"]);
  assert.match(fs.readFileSync(path.join(slice, "proof", "other-1.md"), "utf8"), /^pr: 1430$/m);
  w("mine-1.md", "--pr", "#1429", "--seat", "dev.review");   // the seat was renamed after round 1
  w("mine-2.md", "--pr", "1429", "--seat", "review-r1");
  assert.equal(run(dir, "round", proof, "--pr", "1429").json().round, 3);
  assert.equal(run(dir, "round", proof).json().round, 5);     // without --pr: every verdict in the slice, as before
  assert.throws(() => run(dir, "round", proof, "--pr", "x").json(), SyntaxError);
});

test("tier: a new API route, API controller or OpenAPI spec is Deep", () => {
  for (const f of ["routes/api.php", "app/Http/Controllers/Api/TransferController.php", "src/api/v1/routes.ts",
    "services/api/handlers/user_handler.go", "openapi.yaml", "docs/api/swagger.json"]) {
    assert.equal(run(repo({ [f]: "x\n" }), "tier", "--base", "main").json().tier, "Deep", f);
  }
  for (const f of ["src/apiary/hive.js", "src/api/client.ts", "docs/api/guide.md"])
    assert.notEqual(run(repo({ [f]: "x\n".repeat(80) }), "tier", "--base", "main").json().tier, "Deep", f);
});

test("--security below Deep is allowed only when the repo's REVIEW.md asks for the security axis", () => {
  const plain = repo({ "src/a.js": "x\n" });
  assert.match(run(plain, "write", "--base", "main", "--out", "v.md", "--spec", "pass", "--standards", "pass", "--security", "pass").err, /Deep axis/);
  const asks = repo({ "src/a.js": "x\n", "REVIEW.md": "# Review\n\n- Security axis: always (every change touches customer data)\n" });
  const r = run(asks, "write", "--base", "main", "--out", "v.md", "--spec", "pass", "--standards", "pass", "--security", "pass");
  assert.equal(r.code, 0, r.err);
  assert.match(fs.readFileSync(path.join(asks, "v.md"), "utf8"), /^axes: \{spec: pass, standards: pass, security: pass\}$/m);
  assert.match(run(asks, "tier", "--base", "main").json().why, /REVIEW\.md asks for the security axis/);
});

test("a PR that deletes 'Security axis: always' from REVIEW.md still needs the security axis", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "verdict-"));
  git(dir, "init", "-q", "-b", "main");
  fs.writeFileSync(path.join(dir, "REVIEW.md"), "- Security axis: always\n");
  git(dir, "add", "-A"); git(dir, "commit", "-q", "-m", "base");
  git(dir, "checkout", "-q", "-b", "feat");
  fs.writeFileSync(path.join(dir, "REVIEW.md"), "# Review\n");
  fs.writeFileSync(path.join(dir, "a.js"), "x\n");
  git(dir, "add", "-A"); git(dir, "commit", "-q", "-m", "drop the rule");
  assert.deepEqual(run(dir, "tier", "--base", "main").json().axes, ["spec", "standards", "security"]);
  assert.match(run(dir, "write", "--base", "main", "--out", "v.md", "--spec", "pass", "--standards", "pass").err, /--security is required/);
});
