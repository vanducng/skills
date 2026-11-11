// node --test skills/openrig-workspace/scripts/slice-judges.test.cjs
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const S = path.join(__dirname, "slice-judges.cjs");
const SLICE_YAML = "schema: openrig.slice/v0alpha1\nkind: slice\ncomposition:\n  mission: ../../mission.yaml\n";

// A synthetic mission with one slice, and a fake `rig` on PATH that answers `rig ps --nodes --json --rig <rig>`.
function setup({ seats, owner = "dev-build@demo-rig", missionPolicy = false, slicePolicy = false } = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "slice-judges-"));
  const mission = path.join(root, "missions", "m1");
  const slice = path.join(mission, "slices", "01-thing");
  fs.mkdirSync(slice, { recursive: true });
  fs.writeFileSync(path.join(mission, "mission.yaml"), "schema: openrig.mission/v0alpha1\nkind: mission\n" +
    (missionPolicy ? "proofPolicy:\n  judges:\n    - dev-qa@demo-rig\n" : ""));
  fs.writeFileSync(path.join(slice, "slice.yaml"), SLICE_YAML + (slicePolicy ? "proofPolicy:\n  judges:\n    - x@demo-rig\n" : ""));
  fs.writeFileSync(path.join(slice, "SPEC.md"), `---\nid: OPR.1\nslice: 01-thing\n${owner ? `owner: ${owner}\n` : ""}---\n\n# Thing\n`);
  const bin = path.join(root, "bin");
  fs.mkdirSync(bin);
  // `rig ps --nodes --json --rig <rig>` answers a bare array of nodes.
  const ps = (seats || []).map(([logicalId, model]) => ({ logicalId, canonicalSessionName: `${logicalId.replace(".", "-")}@demo-rig`, rigName: "demo-rig", model }));
  fs.writeFileSync(path.join(root, "ps.json"), JSON.stringify(ps));
  fs.writeFileSync(path.join(bin, "rig"), `#!/bin/sh\necho "$@" >> "${root}/rig.calls"\ncat "${root}/ps.json"\n`, { mode: 0o755 });
  return { root, slice, env: { PATH: `${bin}:${process.env.PATH}`, HOME: root } };
}
const run = (s, ...args) => spawnSync(process.execPath, [S, s.slice, ...args], { env: s.env, encoding: "utf8" });
const yaml = s => fs.readFileSync(path.join(s.slice, "slice.yaml"), "utf8");

const RIG = [
  ["orch.lead", "cpa/claude-opus-5-5:high"],
  ["dev.build", "cpa/claude-opus-5-5:high"],
  ["dev.qa", "cpa/gpt-6.1-terra:high"],
  ["dev.review", "cpa/glm-5.3:high"],
  ["orch.human", null],
];

test("judges are the rig's review and QA seats outside the builder's family", () => {
  const s = setup({ seats: RIG });
  const r = run(s, "--json");
  assert.equal(r.status, 0, r.stderr);
  const out = JSON.parse(r.stdout);
  assert.equal(out.written, true);
  assert.deepEqual(out.judges, ["dev-qa@demo-rig", "dev-review@demo-rig"]);
  assert.match(yaml(s), /^proofPolicy:\n {2}judges:\n {4}- dev-qa@demo-rig\n {4}- dev-review@demo-rig\n/m);
  assert.ok(yaml(s).startsWith(SLICE_YAML), "the scaffold is kept as written");
  assert.match(fs.readFileSync(path.join(s.root, "rig.calls"), "utf8"), /ps --nodes --json --rig demo-rig/, "the seats come from the rig");
});

test("a reviewer in the builder's family is excluded and listed", () => {
  const s = setup({ seats: [...RIG, ["review.r2", "cpa/claude-sonnet-5-5:high"]] });
  const out = JSON.parse(run(s, "--json").stdout);
  assert.deepEqual(out.judges, ["dev-qa@demo-rig", "dev-review@demo-rig"]);
  assert.deepEqual(out.excluded, [{ seat: "review-r2@demo-rig", family: "claude", why: "same family as the builder (claude)" }]);
});

test("an existing mission or slice proofPolicy means no write", () => {
  for (const opt of [{ missionPolicy: true }, { slicePolicy: true }]) {
    const s = setup({ seats: RIG, ...opt });
    const before = yaml(s);
    const r = run(s, "--json");
    assert.equal(r.status, 0, r.stderr);
    const out = JSON.parse(r.stdout);
    assert.equal(out.written, false);
    assert.match(out.reason, opt.missionPolicy ? /mission/ : /slice/);
    assert.equal(yaml(s), before);
  }
});

test("when it cannot tell a family, it says so and writes nothing (exit 1)", () => {
  for (const seats of [
    [["dev.build", "cpa/claude-opus-5-5:high"], ["dev.review", null]], // a judge with no model
    [["dev.build", null], ["dev.review", "cpa/glm-5.3:high"]], // the builder with no model
  ]) {
    const s = setup({ seats });
    const before = yaml(s);
    const r = run(s, "--json");
    assert.equal(r.status, 1, r.stdout);
    assert.match(JSON.parse(r.stdout).reason, /cannot tell/);
    assert.equal(yaml(s), before);
  }
});

test("no independent judge left: nothing is written (exit 1)", () => {
  const s = setup({ seats: [["dev.build", "cpa/claude-opus-5-5:high"], ["dev.review", "cpa/claude-sonnet-5-5:high"]] });
  const r = run(s, "--json");
  assert.equal(r.status, 1);
  assert.match(JSON.parse(r.stdout).reason, /no review or QA seat outside/);
  assert.doesNotMatch(yaml(s), /proofPolicy/);
});

test("the builder is the SPEC owner, or --builder; a builder missing from the rig is an error", () => {
  const s = setup({ seats: [["dev.impl2", "cpa/gpt-6.1-sol:high"], ["dev.build", "cpa/claude-opus-5-5:high"], ["dev.review", "cpa/glm-5.3:high"], ["dev.qa", "cpa/gpt-6.1-terra:high"]], owner: "dev-impl2@demo-rig" });
  assert.deepEqual(JSON.parse(run(s, "--json", "--dry-run").stdout).judges, ["dev-review@demo-rig"], "qa shares the owner's family (gpt)");
  assert.deepEqual(JSON.parse(run(s, "--json", "--dry-run", "--builder", "dev-build@demo-rig").stdout).judges, ["dev-qa@demo-rig", "dev-review@demo-rig"]);
  const gone = run(s, "--json", "--builder", "dev-nobody@demo-rig");
  assert.equal(gone.status, 1);
  assert.match(JSON.parse(gone.stdout).reason, /not a seat of demo-rig/);
  assert.doesNotMatch(yaml(s), /proofPolicy/, "--dry-run and errors write nothing");
});

test("without an owner or --builder, every build seat counts as the builder", () => {
  const s = setup({ seats: [["dev.build", "cpa/claude-opus-5-5:high"], ["dev.build2", "cpa/gpt-6.1-sol:high"], ["dev.review", "cpa/glm-5.3:high"], ["dev.qa", "cpa/gpt-6.1-terra:high"]], owner: null });
  const out = JSON.parse(run(s, "--json", "--rig", "demo-rig").stdout);
  assert.deepEqual(out.judges, ["dev-review@demo-rig"]);
});

test("a rig with no seats on this host is an error, not an empty policy", () => {
  const s = setup({ seats: [] });
  const r = run(s, "--json");
  assert.equal(r.status, 1);
  assert.match(JSON.parse(r.stdout).reason, /no seats of demo-rig on this host/);
  assert.doesNotMatch(yaml(s), /proofPolicy/);
});

test("usage errors exit 2: no slice dir, a dir without slice.yaml, an unknown flag", () => {
  assert.equal(spawnSync(process.execPath, [S], { encoding: "utf8" }).status, 2);
  const empty = fs.mkdtempSync(path.join(os.tmpdir(), "slice-judges-empty-"));
  assert.equal(spawnSync(process.execPath, [S, empty], { encoding: "utf8" }).status, 2);
  const s = setup({ seats: RIG });
  assert.equal(run(s, "--nope").status, 2);
});
