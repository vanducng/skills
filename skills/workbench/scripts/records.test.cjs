// Tests for records.cjs. Run: node --test skills/workbench/scripts/records.test.cjs
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const RECORDS = path.join(__dirname, "records.cjs");
const tmps = [];
const tmp = () => { const d = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), "records-test-"))); tmps.push(d); return d; };
test.after(() => { for (const d of tmps) fs.rmSync(d, { recursive: true, force: true }); });

const CLEAN_ENV = { PATH: process.env.PATH, HOME: process.env.HOME, GIT_CONFIG_GLOBAL: "/dev/null", GIT_CONFIG_SYSTEM: "/dev/null" };
function run(args, { cwd, env = {} } = {}) {
  const r = spawnSync(process.execPath, [RECORDS, ...args], { cwd: cwd || process.cwd(), encoding: "utf8", env: { ...CLEAN_ENV, ...env } });
  return { code: r.status, out: r.stdout, err: r.stderr, json: () => JSON.parse(r.stdout) };
}
const git = (cwd, ...a) => { const r = spawnSync("git", ["-c", "user.email=t@example.test", "-c", "user.name=t", "-c", "init.defaultBranch=main", ...a], { cwd, encoding: "utf8" }); assert.equal(r.status, 0, r.stderr); return r.stdout.trim(); };
const write = (file, text) => { fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, text); return file; };

// A synthetic workspace: one project, one mission (code tb9) with slices 01-board and 02-index.
function workspace() {
  const root = tmp();
  write(path.join(root, "workspace.yaml"), "schema: openrig.workspace/v0alpha1\nprojects:\n  - id: acme.shop\n    root: orgs/acme/projects/shop\n    rigs: []\n");
  const m = path.join(root, "orgs/acme/projects/shop/missions/tracking");
  write(path.join(m, "SPEC.md"), "---\ncode: tb9\nmilestone: 1\n---\n# Mission\n");
  for (const s of ["01-board", "02-index"]) { write(path.join(m, "slices", s, "SPEC.md"), `---\nid: OPR.1.${s.slice(0, 2)}\nintent: "x"\n---\n`); write(path.join(m, "slices", s, "slice.yaml"), "schema: x\n"); }
  return { root, mission: m, slice1: path.join(m, "slices/01-board"), slice2: path.join(m, "slices/02-index") };
}
const RIG = { OPENRIG_SESSION_NAME: "dev-impl@rig" };
function repo(name, branch) {
  const parent = tmp(), dir = path.join(parent, name);
  fs.mkdirSync(dir);
  git(dir, "init", "-q");
  git(dir, "commit", "-q", "--allow-empty", "-m", "init");
  if (branch) git(dir, "checkout", "-q", "-b", branch);
  return dir;
}

test("a missing or unknown command prints usage and exits 2", () => {
  assert.equal(run([]).code, 2);
  const r = run(["frobnicate"]);
  assert.equal(r.code, 2);
  assert.match(r.err, /usage|unknown command/i);
});

// ---- resolve: rig mode ------------------------------------------------------------------------------------------

test("resolve in a rig with --slice NN-slug returns the slice folder and the rig proof command", () => {
  const w = workspace();
  const r = run(["resolve", "--slice", "01-board", "--json"], { cwd: w.root, env: { ...RIG, PROJECTS_ROOT: w.root } });
  assert.equal(r.code, 0, r.err);
  const j = r.json();
  assert.equal(j.mode, "rig");
  assert.equal(j.dir, w.slice1);
  assert.equal(j.spec, path.join(w.slice1, "SPEC.md"));
  assert.equal(j.progress, path.join(w.slice1, "PROGRESS.md"));
  assert.equal(j.proofFile, path.join(w.slice1, "PROOF.md"));
  assert.equal(j.proofDir, path.join(w.slice1, "proof"));
  assert.equal(j.reports, path.join(w.slice1, "reports"));
  assert.match(j.proofAdd, new RegExp(`^rig proof --workspace .+ add .*01-board`));
});

test("resolve takes a slice path and a mission/slice pair too", () => {
  const w = workspace(), env = { ...RIG, PROJECTS_ROOT: w.root };
  assert.equal(run(["resolve", "--slice", w.slice2, "--json"], { cwd: w.root, env }).json().dir, w.slice2);
  assert.equal(run(["resolve", "--slice", "tracking/02-index", "--json"], { cwd: w.root, env }).json().dir, w.slice2);
});

test("an ambiguous or unknown slice name exits 2 and names the candidates", () => {
  const w = workspace(), env = { ...RIG, PROJECTS_ROOT: w.root };
  write(path.join(w.root, "orgs/acme/projects/shop/missions/other/slices/01-board/SPEC.md"), "---\nid: x\n---\n");
  const amb = run(["resolve", "--slice", "01-board"], { cwd: w.root, env });
  assert.equal(amb.code, 2);
  assert.match(amb.err, /ambiguous/i);
  assert.match(amb.err, /tracking\/01-board/);
  const none = run(["resolve", "--slice", "09-nope"], { cwd: w.root, env });
  assert.equal(none.code, 2);
  assert.match(none.err, /no slice/i);
});

test("in a rig the slice is found from the worktree name <repo>-<code>-s<nn>", () => {
  const w = workspace(), wt = repo("skills-tb9-s02");
  const r = run(["resolve", "--json"], { cwd: wt, env: { ...RIG, PROJECTS_ROOT: w.root } });
  assert.equal(r.code, 0, r.err);
  assert.equal(r.json().dir, w.slice2);
});

test("in a rig the slice is found from a cwd inside the slice folder", () => {
  const w = workspace();
  fs.mkdirSync(path.join(w.slice1, "proof"));
  const r = run(["resolve", "--json"], { cwd: path.join(w.slice1, "proof"), env: { ...RIG, PROJECTS_ROOT: w.root } });
  assert.equal(r.json().dir, w.slice1);
});

test("a rig that cannot name its slice exits 2 and never falls back to .workbench", () => {
  const w = workspace(), plain = repo("scratch", "feat/PROJ-1-thing");
  const r = run(["resolve"], { cwd: plain, env: { ...RIG, PROJECTS_ROOT: w.root } });
  assert.equal(r.code, 2);
  assert.match(r.err, /--slice/);
  assert.equal(fs.existsSync(path.join(plain, ".workbench")), false);
});

test("a worktree name whose code matches no mission, or two missions, is refused", () => {
  const w = workspace();
  const none = run(["resolve"], { cwd: repo("skills-zz9-s01"), env: { ...RIG, PROJECTS_ROOT: w.root } });
  assert.equal(none.code, 2);
  write(path.join(w.root, "orgs/acme/projects/shop/missions/twin/SPEC.md"), "---\ncode: tb9\n---\n");
  write(path.join(w.root, "orgs/acme/projects/shop/missions/twin/slices/01-board/SPEC.md"), "---\nid: y\n---\n");
  const two = run(["resolve"], { cwd: repo("skills-tb9-s01"), env: { ...RIG, PROJECTS_ROOT: w.root } });
  assert.equal(two.code, 2);
  assert.match(two.err, /ambiguous/i);
});

test("the workspace is found by walking up from the cwd when PROJECTS_ROOT is unset", () => {
  const w = workspace();
  const r = run(["resolve", "--slice", "01-board", "--json"], { cwd: w.slice1, env: RIG });
  assert.equal(r.json().dir, w.slice1);
});

// ---- resolve: bench mode ----------------------------------------------------------------------------------------

test("outside a rig the folder is .workbench/<id> from the branch, lower-cased", () => {
  const dir = repo("proj", "feat/PROJ-3316-Fix_Thing");
  const r = run(["resolve", "--json"], { cwd: dir });
  assert.equal(r.code, 0, r.err);
  const j = r.json();
  assert.equal(j.mode, "bench");
  assert.equal(j.dir, path.join(dir, ".workbench", "proj-3316-fix-thing"));
  assert.equal(j.reports, path.join(j.dir, "reports"));
  assert.match(j.proofAdd, /records\.cjs proof add /);
});

test("--id wins over the branch, and a bad id is refused", () => {
  const dir = repo("proj", "feat/other");
  assert.equal(run(["resolve", "--id", "my-task", "--json"], { cwd: dir }).json().dir, path.join(dir, ".workbench", "my-task"));
  const bad = run(["resolve", "--id", "../escape"], { cwd: dir });
  assert.equal(bad.code, 2);
});

test("on a default branch with no --id it asks for one", () => {
  const dir = repo("proj");
  const r = run(["resolve"], { cwd: dir });
  assert.equal(r.code, 2);
  assert.match(r.err, /--id/);
});

test("a linked worktree resolves to the main worktree's .workbench", () => {
  const main = repo("main-checkout", "feat/PROJ-7-thing");
  git(main, "checkout", "-q", "main");
  const wt = path.join(tmp(), "linked");
  git(main, "worktree", "add", "-q", wt, "feat/PROJ-7-thing");
  const r = run(["resolve", "--json"], { cwd: wt });
  assert.equal(r.json().dir, path.join(main, ".workbench", "proj-7-thing"));
});

test("outside a git repository the folder is under the cwd", () => {
  const dir = tmp();
  assert.equal(run(["resolve", "--id", "loose", "--json"], { cwd: dir }).json().dir, path.join(dir, ".workbench", "loose"));
});

test("OPENRIG_SESSION_NAME without a findable workspace exits 2: a rig never degrades to bench mode", () => {
  const dir = repo("proj", "feat/PROJ-2-x");
  const r = run(["resolve"], { cwd: dir, env: RIG });
  assert.equal(r.code, 2);
  assert.match(r.err, /workspace\.yaml/);
  assert.equal(fs.existsSync(path.join(dir, ".workbench")), false);
});

test("a stale PROJECTS_ROOT or --root falls through to the cwd walk-up, so a rig seat stays in rig mode", () => {
  const w = workspace(), stale = tmp();
  const viaEnv = run(["resolve", "--slice", "01-board", "--json"], { cwd: w.slice1, env: { ...RIG, PROJECTS_ROOT: stale } });
  assert.equal(viaEnv.code, 0, viaEnv.err);
  assert.equal(viaEnv.json().mode, "rig");
  assert.equal(viaEnv.json().dir, w.slice1);
  const viaFlag = run(["resolve", "--root", stale, "--slice", "01-board", "--json"], { cwd: w.slice1, env: RIG });
  assert.equal(viaFlag.json().mode, "rig");
  const none = run(["resolve", "--slice", "01-board"], { cwd: stale, env: { ...RIG, PROJECTS_ROOT: stale } });
  assert.equal(none.code, 2);
});

test("--slice with an arbitrary directory is refused unless it sits under missions/<m>/(slices|closed)/", () => {
  const w = workspace(), env = { ...RIG, PROJECTS_ROOT: w.root };
  const stray = tmp();
  write(path.join(stray, "SPEC.md"), "---\nid: x\n---\n");
  const r = run(["resolve", "--slice", stray], { cwd: w.root, env });
  assert.equal(r.code, 2);
  assert.match(r.err, /missions/);
  assert.equal(run(["resolve", "--slice", w.slice1, "--json"], { cwd: w.root, env }).json().dir, w.slice1);
  const closed = path.join(w.mission, "closed", "00-old");
  write(path.join(closed, "SPEC.md"), "---\nid: o\n---\n");
  assert.equal(run(["resolve", "--slice", closed, "--json"], { cwd: w.root, env }).json().dir, closed);
});

test("--print gives just the directory", () => {
  const dir = repo("proj", "feat/PROJ-5-x");
  assert.equal(run(["resolve", "--print"], { cwd: dir }).out.trim(), path.join(dir, ".workbench", "proj-5-x"));
});

// ---- init and check ---------------------------------------------------------------------------------------------

test("init creates the shape and is idempotent; it never overwrites authored text", () => {
  const dir = repo("proj", "feat/PROJ-9-x");
  const r = run(["init", "--json"], { cwd: dir });
  assert.equal(r.code, 0, r.err);
  const d = path.join(dir, ".workbench", "proj-9-x");
  for (const f of ["SPEC.md", "PROGRESS.md", "PROOF.md"]) assert.ok(fs.existsSync(path.join(d, f)), f);
  assert.ok(fs.statSync(path.join(d, "reports")).isDirectory());
  fs.writeFileSync(path.join(d, "SPEC.md"), "authored\n");
  assert.equal(run(["init"], { cwd: dir }).code, 0);
  assert.equal(fs.readFileSync(path.join(d, "SPEC.md"), "utf8"), "authored\n");
});

test("init --intent fills the intent, and the new SPEC carries the audit headings", () => {
  const dir = repo("proj", "feat/PROJ-9-x");
  run(["init", "--intent", "Ship the thing"], { cwd: dir });
  const spec = fs.readFileSync(path.join(dir, ".workbench", "proj-9-x", "SPEC.md"), "utf8");
  assert.match(spec, /^intent: "Ship the thing"$/m);
  assert.match(spec, /^## Mini-requirements$/m);
  assert.match(spec, /^## Proof contract$/m);
  assert.match(spec, /^id: proj-9-x$/m);
});

test("init is refused in a rig: slice folders come from rig scope slice create", () => {
  const w = workspace();
  const r = run(["init", "--slice", "01-board"], { cwd: w.root, env: { ...RIG, PROJECTS_ROOT: w.root } });
  assert.equal(r.code, 2);
  assert.match(r.err, /rig scope slice create/);
});

test("a fresh init folder fails check until it is authored; then it passes", () => {
  const dir = repo("proj", "feat/PROJ-9-x");
  run(["init"], { cwd: dir });
  const d = path.join(dir, ".workbench", "proj-9-x");
  const fresh = run(["check", d], { cwd: dir });
  assert.equal(fresh.code, 1);
  assert.match(fresh.out, /FAIL NO_INTENT/);
  assert.match(fresh.out, /FAIL NO_MINI_REQUIREMENTS/);
  assert.match(fresh.out, /FAIL NO_PROOF_CONTRACT/);
  fs.writeFileSync(path.join(d, "SPEC.md"), '---\nid: proj-9-x\nintent: "Ship it"\n---\n\n## Mini-requirements\n\n1. It ships.\n\n## Proof contract\n\n- [ ] It shipped, with a capture.\n');
  const ok = run(["check", d], { cwd: dir });
  assert.equal(ok.code, 0, ok.out);
  assert.match(ok.out, /check: ok/);
});

test("check --stage close also needs the retro line slice-check reads", () => {
  const dir = repo("proj", "feat/PROJ-9-x");
  run(["init", "--intent", "x"], { cwd: dir });
  const d = path.join(dir, ".workbench", "proj-9-x");
  fs.writeFileSync(path.join(d, "SPEC.md"), '---\nid: p\nintent: "x"\n---\n## Mini-requirements\n1. a\n## Proof contract\n- [ ] b\n');
  assert.match(run(["check", d, "--stage", "close"]).out, /FAIL NO_RETRO/);
  fs.appendFileSync(path.join(d, "PROGRESS.md"), "\n- 2026-11-08T03:00Z: retro: none\n");
  assert.equal(run(["check", d, "--stage", "close"]).code, 0);
});

test("check rejects a missing folder and a proof artifact with a bad header", () => {
  const dir = repo("proj", "feat/PROJ-9-x");
  assert.equal(run(["check", path.join(dir, "nope")]).code, 2);
  run(["init"], { cwd: dir });
  const d = path.join(dir, ".workbench", "proj-9-x");
  fs.writeFileSync(path.join(d, "SPEC.md"), '---\nid: p\nintent: "x"\n---\n## Mini-requirements\n1. a\n## Proof contract\n- [ ] b\n');
  write(path.join(d, "proof", "bad.md"), "---\nslice: p\nverdict: MAYBE\n---\nbody\n");
  const r = run(["check", d]);
  assert.equal(r.code, 1);
  assert.match(r.out, /FAIL BAD_PROOF_HEADER: proof\/bad\.md/);
});

// ---- bench proof add --------------------------------------------------------------------------------------------

function benchDir() {
  const dir = repo("proj", "feat/PROJ-9-x");
  run(["init", "--intent", "x"], { cwd: dir });
  const d = path.join(dir, ".workbench", "proj-9-x");
  return { dir, d };
}
// The flat C1 header of an artifact: scalars and one list.
function header(file) {
  const m = /^---\n([\s\S]*?)\n---\n/.exec(fs.readFileSync(file, "utf8"));
  const out = {};
  let list = null;
  for (const line of m[1].split("\n")) {
    const item = /^\s+-\s+(.*)$/.exec(line);
    if (item && list) { list.push(JSON.parse(/^["']/.test(item[1]) ? item[1].replace(/^'(.*)'$/, '"$1"') : JSON.stringify(item[1]))); continue; }
    const kv = /^([a-z_]+):\s*(.*)$/.exec(line);
    if (!kv) continue;
    if (kv[2] === "") { list = out[kv[1]] = []; continue; }
    list = null;
    out[kv[1]] = /^"/.test(kv[2]) ? JSON.parse(kv[2]) : kv[2];
  }
  return out;
}

test("proof add writes the C1 header the daemon expects, with the slice id from SPEC.md", () => {
  const { d } = benchDir();
  const r = run(["proof", "add", d, "--artifact-type", "qa", "--verdict", "PASS", "--candidate-sha", "abc1234", "--money-evidence", "exit 0 on the fixture", "--body", "Ran it.", "--name", "qa-pass.md", "--json"]);
  assert.equal(r.code, 0, r.err);
  const h = header(path.join(d, "proof", "qa-pass.md"));
  assert.deepEqual(Object.keys(h), ["slice", "candidate_sha", "artifact_type", "verdict", "money_evidence"]);
  assert.deepEqual(h, { slice: "proj-9-x", candidate_sha: "abc1234", artifact_type: "qa", verdict: "PASS", money_evidence: "exit 0 on the fixture" });
  assert.match(fs.readFileSync(path.join(d, "proof", "qa-pass.md"), "utf8"), /\nRan it\.\n$/);
});

test("proof add: evidences, self-check, media, file body, slice id override", () => {
  const { d, dir } = benchDir();
  write(path.join(dir, "body.md"), "From a file.\n");
  const r = run(["proof", "add", d, "--artifact-type", "rev1-r1", "--verdict", "CONCERNING", "--candidate-sha", "deadbee", "--money-evidence", "colon: and # hash \"quoted\"", "--file", path.join(dir, "body.md"), "--evidences", "1,3", "--self-check", "I looked at the capture.", "--media", "shot.png,two.png", "--slice-id", "OPR.9.9"]);
  assert.equal(r.code, 0, r.err);
  const f = path.join(d, "proof", "body.md");
  assert.ok(fs.existsSync(f), "name defaults to the file stem plus .md");
  const h = header(f);
  assert.equal(h.slice, "OPR.9.9");
  assert.equal(h.money_evidence, 'colon: and # hash "quoted"');
  assert.deepEqual(h.evidences, ["1", "3"]);
  assert.equal(h.self_check, "I looked at the capture.");
  const text = fs.readFileSync(f, "utf8");
  assert.match(text, /shot\.png/);
  assert.match(text, /two\.png/);
});

test("proof add refuses a bad enum, a missing flag, an existing file without --replace, and a rig slice folder", () => {
  const { d } = benchDir();
  const base = ["proof", "add", d, "--artifact-type", "qa", "--verdict", "PASS", "--candidate-sha", "abc1234", "--money-evidence", "m", "--body", "b", "--name", "a.md"];
  assert.equal(run(["proof", "add", d, "--artifact-type", "nope", "--verdict", "PASS", "--candidate-sha", "a", "--money-evidence", "m", "--body", "b"]).code, 2);
  assert.equal(run(["proof", "add", d, "--artifact-type", "qa", "--verdict", "FINE", "--candidate-sha", "a", "--money-evidence", "m", "--body", "b"]).code, 2);
  assert.equal(run(["proof", "add", d, "--artifact-type", "qa", "--verdict", "PASS", "--money-evidence", "m", "--body", "b"]).code, 2);
  assert.equal(run(base).code, 0);
  const again = run(base);
  assert.equal(again.code, 2);
  assert.match(again.err, /--replace/);
  assert.equal(run([...base, "--replace"]).code, 0);
  const w = workspace();
  const rig = run(["proof", "add", w.slice1, ...base.slice(3)]);
  assert.equal(rig.code, 2);
  assert.match(rig.err, /rig proof/);
  assert.equal(fs.existsSync(path.join(w.slice1, "proof")), false);
});

test("proof add lists the artifact in PROOF.md, once", () => {
  const { d } = benchDir();
  const args = ["proof", "add", d, "--artifact-type", "guard", "--verdict", "CLEAR", "--candidate-sha", "abc1234", "--money-evidence", "clean", "--body", "b", "--name", "g.md"];
  run(args);
  run([...args, "--replace"]);
  const proof = fs.readFileSync(path.join(d, "PROOF.md"), "utf8");
  assert.equal(proof.split("proof/g.md").length - 1, 1);
});

const GOOD = d => ["proof", "add", d, "--artifact-type", "qa", "--verdict", "PASS", "--candidate-sha", "abc1234", "--money-evidence", "m", "--body", "b", "--name", "a.md"];

test("proof add --media mirrors the rig writer: relative to proof/, contained in the record, absolute refused", () => {
  const { d } = benchDir();
  const abs = run([...GOOD(d), "--media", path.join(d, "proof", "shot.png")]);
  assert.equal(abs.code, 2);
  assert.match(abs.err, /absolute/);
  const out = run([...GOOD(d), "--media", "../../escape.png"]);
  assert.equal(out.code, 2);
  assert.match(out.err, /outside/);
  assert.equal(fs.existsSync(path.join(d, "proof", "a.md")), false, "nothing is written on a refused ref");
  write(path.join(d, "proof", "shot.png"), "png");
  write(path.join(d, "proof", "clip.mp4"), "mp4");
  const ok = run([...GOOD(d), "--media", "shot.png,clip.mp4,missing.png", "--replace"]);
  assert.equal(ok.code, 0, ok.err);
  assert.match(ok.err, /missing\.png.*does not exist/);
  const text = fs.readFileSync(path.join(d, "proof", "a.md"), "utf8");
  assert.match(text, /\n## Media\n/);
  assert.match(text, /!\[shot\.png\]\(shot\.png\)/);
  assert.match(text, /<video src="clip\.mp4"><\/video>/);
});

test("proof add --replace never writes through a symlink or hardlink", () => {
  const { d, dir } = benchDir();
  const victim = path.join(dir, "victim.txt");
  write(victim, "keep me\n");
  fs.mkdirSync(path.join(d, "proof"), { recursive: true });
  fs.symlinkSync(victim, path.join(d, "proof", "a.md"));
  assert.equal(run([...GOOD(d), "--replace"]).code, 0);
  assert.equal(fs.readFileSync(victim, "utf8"), "keep me\n", "the link target is untouched");
  assert.equal(fs.lstatSync(path.join(d, "proof", "a.md")).isSymbolicLink(), false, "the link was replaced, not followed");
  fs.rmSync(path.join(d, "proof", "a.md"));
  fs.linkSync(victim, path.join(d, "proof", "a.md"));
  assert.equal(run([...GOOD(d), "--replace"]).code, 0);
  assert.equal(fs.readFileSync(victim, "utf8"), "keep me\n", "the hardlinked file is untouched");
  assert.ok(!ls(path.join(d, "proof")).some(n => n.endsWith(".replace-tmp")), "no staging file left behind");
});
function ls(p) { return fs.readdirSync(p); }

test("proof add --file rejects binary content the way the rig writer does", () => {
  const { d, dir } = benchDir();
  write(path.join(dir, "shot.png"), "not really a png");
  const byExt = run(["proof", "add", d, "--artifact-type", "qa", "--verdict", "PASS", "--candidate-sha", "a", "--money-evidence", "m", "--file", path.join(dir, "shot.png")]);
  assert.equal(byExt.code, 2);
  assert.match(byExt.err, /binary/i);
  fs.writeFileSync(path.join(dir, "nul.md"), Buffer.from([0x68, 0x69, 0x00, 0x21]));
  const byNul = run(["proof", "add", d, "--artifact-type", "qa", "--verdict", "PASS", "--candidate-sha", "a", "--money-evidence", "m", "--file", path.join(dir, "nul.md")]);
  assert.equal(byNul.code, 2);
  assert.match(byNul.err, /binary/i);
  assert.deepEqual(fs.existsSync(path.join(d, "proof")) ? ls(path.join(d, "proof")) : [], []);
});

test("the PROOF.md index line is one line however the evidence is written", () => {
  const { d } = benchDir();
  run(["proof", "add", d, "--artifact-type", "qa", "--verdict", "PASS", "--candidate-sha", "abc1234", "--money-evidence", "line one\nline two\n\n  - injected bullet", "--body", "b", "--name", "n.md"]);
  const line = fs.readFileSync(path.join(d, "PROOF.md"), "utf8").split("\n").filter(l => l.includes("proof/n.md"));
  assert.equal(line.length, 1);
  assert.match(line[0], /line one line two - injected bullet$/);
  assert.equal(fs.readFileSync(path.join(d, "PROOF.md"), "utf8").split("\n").filter(l => /injected/.test(l)).length, 1);
});

test("the printed proof commands survive a path with spaces and quotes", () => {
  const parent = tmp(), dirName = "my repo's dir", dir = path.join(parent, dirName);
  fs.mkdirSync(dir);
  git(dir, "init", "-q", "-b", "feat/PROJ-4-x");
  git(dir, "commit", "-q", "--allow-empty", "-m", "i");
  const bench = run(["resolve", "--json"], { cwd: dir }).json();
  const split = cmd => spawnSync("bash", ["-c", `set -- ${cmd}; printf '%s\\n' "$@"`], { encoding: "utf8" }).stdout.trim().split("\n");
  const words = split(bench.proofAdd);
  assert.equal(words[words.length - 1], bench.dir);
  assert.equal(words[words.length - 3], "proof");
  const w = workspace();
  const spaced = path.join(parent, "ws with space");
  fs.renameSync(w.root, spaced);
  const rig = run(["resolve", "--slice", "01-board", "--json"], { cwd: spaced, env: { ...RIG, PROJECTS_ROOT: spaced } }).json();
  const rw = split(rig.proofAdd);
  assert.deepEqual(rw.slice(0, 3), ["rig", "proof", "--workspace"]);
  assert.equal(rw[3], spaced);
  assert.equal(rw[rw.length - 1], rig.dir);
});

test("init and migrate never write through a symlink at SPEC.md, PROGRESS.md or PROOF.md", () => {
  const dir = repo("proj", "feat/PROJ-9-x");
  const d = path.join(dir, ".workbench", "proj-9-x");
  fs.mkdirSync(d, { recursive: true });
  const victim = path.join(dir, "victim.txt");
  write(victim, "keep me\n");
  fs.symlinkSync(victim, path.join(d, "SPEC.md"));
  fs.symlinkSync(path.join(dir, "does-not-exist"), path.join(d, "PROOF.md"));
  assert.equal(run(["init"], { cwd: dir }).code, 0);
  assert.equal(fs.readFileSync(victim, "utf8"), "keep me\n");
  assert.equal(fs.existsSync(path.join(dir, "does-not-exist")), false, "a dangling link is not created through");
  assert.ok(fs.lstatSync(path.join(d, "SPEC.md")).isSymbolicLink(), "an existing entry is left alone by init");
  const m = legacy();
  write(victim, "keep me\n");
  fs.mkdirSync(path.join(m.wb, "proj-1-alpha"), { recursive: true });
  fs.symlinkSync(victim, path.join(m.wb, "proj-1-alpha", "SPEC.md"));
  run(["migrate", "--apply"], { cwd: m.dir });
  assert.equal(fs.readFileSync(victim, "utf8"), "keep me\n", "migrate does not write the SPEC.md through a link");
});

test("a missing --file is a clean error, not a stack trace", () => {
  const { d } = benchDir();
  const r = run(["proof", "add", d, "--artifact-type", "qa", "--verdict", "PASS", "--candidate-sha", "a", "--money-evidence", "m", "--file", path.join(d, "nope.md")]);
  assert.equal(r.code, 2);
  assert.match(r.err, /^records: .*--file/);
  assert.doesNotMatch(r.err, /\n\s+at /);
});

test("SKILL.md states the new record layout and points at records.cjs", () => {
  const skill = fs.readFileSync(path.join(__dirname, "..", "SKILL.md"), "utf8");
  assert.match(skill, /records\.cjs/);
  assert.match(skill, /\.workbench\/<id>\/\{SPEC\.md,PROGRESS\.md,PROOF\.md,proof\/,reports\/\}/);
  assert.match(skill, /migrate --apply/);
});

test("the enums and required fields are the daemon's (skipped when the OpenRig package is not installed)", { skip: !(() => { try { return !!findAudit(); } catch { return false; } })() }, () => {
  const src = fs.readFileSync(findAudit(), "utf8");
  const arr = name => JSON.parse(new RegExp(`const ${name} = (\\[[^\\]]*\\]);`).exec(src)[1]);
  const mod = require(RECORDS);
  assert.deepEqual(mod.C1_REQUIRED_FIELDS, arr("C1_REQUIRED_FIELDS"));
  assert.deepEqual(mod.C1_ARTIFACT_TYPES, arr("C1_ARTIFACT_TYPES"));
  assert.deepEqual(mod.C1_VERDICTS, arr("C1_VERDICTS"));
});
function findAudit() {
  const roots = [process.env.OPENRIG_CLI_DIR, path.join(os.homedir(), ".local", "openrig-cli", "node_modules", "@openrig", "cli")].filter(Boolean);
  for (const r of roots) { const f = path.join(r, "daemon", "dist", "domain", "scope", "scope-audit.js"); if (fs.existsSync(f)) return f; }
  return null;
}

// ---- migrate ----------------------------------------------------------------------------------------------------

function legacy() {
  const dir = repo("proj", "feat/PROJ-1-x");
  const wb = path.join(dir, ".workbench");
  write(path.join(wb, "features/proj-1-alpha/feature.json"), JSON.stringify({ id: "proj-1-alpha", ticket: "PROJ-1", label: "Alpha rollout", status: "active" }));
  write(path.join(wb, "features/proj-1-alpha/reports/r1.md"), "report one\n");
  write(path.join(wb, "features/proj-1-alpha/plans/p1.md"), "plan one\n");
  write(path.join(wb, "features/proj-1-alpha/visuals/v1.png"), "png\n");
  write(path.join(wb, "features/proj-1-alpha/journals/j1.md"), "journal\n");
  write(path.join(wb, "features/proj-1-alpha/state/s.json"), "{}\n");
  write(path.join(wb, "features/beta/feature.json"), JSON.stringify({ id: "beta", label: "Beta" }));
  write(path.join(wb, "features/beta/reports/b.md"), "beta report\n");
  write(path.join(wb, "INDEX.md"), "index\n");
  write(path.join(wb, "_global/scratch/x.md"), "scratch\n");
  write(path.join(wb, "plans/loose.md"), "loose\n");
  return { dir, wb };
}
const tree = root => { const out = []; (function walk(d) { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); if (e.isDirectory()) walk(p); else out.push(path.relative(root, p) + ":" + fs.readFileSync(p, "utf8")); } })(root); return out.sort(); };

test("migrate without --apply changes nothing and says what it would do", () => {
  const { dir, wb } = legacy();
  const before = tree(wb);
  const r = run(["migrate"], { cwd: dir });
  assert.equal(r.code, 0, r.err);
  assert.deepEqual(tree(wb), before);
  assert.match(r.out, /features\/proj-1-alpha\/reports\/r1\.md -> proj-1-alpha\/reports\/r1\.md/);
  assert.match(r.out, /features\/proj-1-alpha\/plans\/p1\.md -> proj-1-alpha\/reports\/plans\/p1\.md/);
  assert.match(r.out, /dry run/i);
});

test("migrate --apply moves every file into the record shape without loss", () => {
  const { dir, wb } = legacy();
  const before = tree(wb).filter(e => e.startsWith("features/")).map(e => e.split(":").slice(1).join(":")).sort();
  const r = run(["migrate", "--apply"], { cwd: dir });
  assert.equal(r.code, 0, r.err);
  const a = path.join(wb, "proj-1-alpha");
  assert.equal(fs.readFileSync(path.join(a, "reports/r1.md"), "utf8"), "report one\n");
  assert.equal(fs.readFileSync(path.join(a, "reports/plans/p1.md"), "utf8"), "plan one\n");
  assert.equal(fs.readFileSync(path.join(a, "reports/visuals/v1.png"), "utf8"), "png\n");
  assert.equal(fs.readFileSync(path.join(a, "reports/journals/j1.md"), "utf8"), "journal\n");
  assert.equal(fs.readFileSync(path.join(a, "reports/state/s.json"), "utf8"), "{}\n");
  assert.ok(fs.existsSync(path.join(a, "reports/feature.json")), "feature.json is kept, not dropped");
  assert.match(fs.readFileSync(path.join(a, "SPEC.md"), "utf8"), /^intent: "Alpha rollout"$/m);
  assert.equal(fs.readFileSync(path.join(wb, "beta/reports/b.md"), "utf8"), "beta report\n");
  assert.equal(fs.existsSync(path.join(wb, "features/proj-1-alpha")), false, "emptied feature folder removed");
  const after = tree(wb).map(e => e.split(":").slice(1).join(":"));
  for (const content of before) assert.ok(after.includes(content), `content kept: ${JSON.stringify(content)}`);
  assert.equal(fs.readFileSync(path.join(wb, "INDEX.md"), "utf8"), "index\n", "root INDEX.md untouched");
  assert.equal(fs.readFileSync(path.join(wb, "_global/scratch/x.md"), "utf8"), "scratch\n");
  assert.equal(fs.readFileSync(path.join(wb, "plans/loose.md"), "utf8"), "loose\n");
});

test("a second migrate --apply is a no-op", () => {
  const { dir, wb } = legacy();
  run(["migrate", "--apply"], { cwd: dir });
  const before = tree(wb);
  const r = run(["migrate", "--apply"], { cwd: dir });
  assert.equal(r.code, 0);
  assert.deepEqual(tree(wb), before);
  assert.match(r.out, /nothing to migrate/i);
});

test("migrate never overwrites: a name clash is reported, skipped and exits 1", () => {
  const { dir, wb } = legacy();
  write(path.join(wb, "proj-1-alpha/reports/r1.md"), "different\n");
  const r = run(["migrate", "--apply"], { cwd: dir });
  assert.equal(r.code, 1);
  assert.match(r.out, /CONFLICT .*r1\.md/);
  assert.equal(fs.readFileSync(path.join(wb, "proj-1-alpha/reports/r1.md"), "utf8"), "different\n");
  assert.equal(fs.readFileSync(path.join(wb, "features/proj-1-alpha/reports/r1.md"), "utf8"), "report one\n");
  assert.equal(fs.readFileSync(path.join(wb, "proj-1-alpha/reports/plans/p1.md"), "utf8"), "plan one\n", "the other files still moved");
});

test("migrate on a repo with no old tree says so and exits 0", () => {
  const dir = repo("proj", "feat/PROJ-1-x");
  const r = run(["migrate"], { cwd: dir });
  assert.equal(r.code, 0);
  assert.match(r.out, /nothing to migrate/i);
});
