#!/usr/bin/env node
// Writes proofPolicy.judges into a new slice's slice.yaml, so the first `rig proof judge` does not stop on
// policy_required. Run it right after `rig scope slice create`.
//
//   slice-judges.cjs <slice dir> [--builder <session>] [--rig <rig>] [--dry-run] [--json]
//
// The judges are the rig's review and QA seats (member review*, qa*, r<n>) whose model family differs from the
// builder's. The seats and their models come from `rig ps --nodes --json --rig <rig>`, never from this file.
// The builder is --builder, else the SPEC.md `owner:`, else every build seat (build*, impl*) of the rig.
// A model's family is its prefix in $PROJECTS_ROOT/fleet/routing.yaml `families:` when that file exists, else the
// model id's first word (`claude-opus-5-5` -> claude).
// Nothing is written when the mission or the slice already has a proofPolicy (exit 0, with the reason), when a
// family cannot be told, when the builder is not a seat of the rig, or when no independent judge is left (exit 1).
// Exit 2 on a usage error.
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

class Usage extends Error {}
const JUDGE = /^(?:review|qa|r)\d*$/;
const BUILD = /^(?:build|impl)\d*$/;
const POLICY = /^proofPolicy:/m;

function args(argv) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--json" || a === "--dry-run") o[a] = true;
    else if (a === "--builder" || a === "--rig") { if (!argv[i + 1] || argv[i + 1].startsWith("--")) throw new Usage(`${a} needs a value`); o[a] = argv[++i]; }
    else if (a.startsWith("--")) throw new Usage(`unknown flag ${a}`);
    else o._.push(a);
  }
  if (o._.length !== 1) throw new Usage("usage: slice-judges.cjs <slice dir> [--builder <session>] [--rig <rig>] [--dry-run] [--json]");
  return o;
}

const read = f => { try { return fs.readFileSync(f, "utf8"); } catch { return ""; } };
const modelId = m => (m ? String(m).split("/").pop().split(":")[0] : "");

function familyRule() {
  const routing = process.env.PROJECTS_ROOT ? read(path.join(process.env.PROJECTS_ROOT, "fleet", "routing.yaml")) : "";
  const block = /^families:\n((?:[ \t]+\S.*\n?)+)/m.exec(routing);
  const table = block ? [...block[1].matchAll(/^\s+([\w.-]+):\s*([\w.-]+)/gm)].map(m => [m[1], m[2]]).sort((a, b) => b[0].length - a[0].length) : [];
  return model => {
    const id = modelId(model);
    if (!id) return null;
    if (table.length) { const hit = table.find(([prefix]) => id.startsWith(prefix)); return hit ? hit[1] : null; }
    return id.split("-")[0] || null;
  };
}

function seatsOf(rig) {
  const r = spawnSync("rig", ["ps", "--nodes", "--json", "--rig", rig], { encoding: "utf8" });
  let doc;
  try { doc = JSON.parse(r.stdout); } catch { doc = null; }
  // A bare array of nodes for --rig; a bounded envelope ({entries}) in other modes.
  const nodes = Array.isArray(doc) ? doc : doc && Array.isArray(doc.entries) ? doc.entries : null;
  if (r.status !== 0 || !nodes) throw new Error(`cannot tell the seats: rig ps --nodes --json --rig ${rig} failed`);
  if (!nodes.length) throw new Error(`cannot tell the seats: no seats of ${rig} on this host`);
  return nodes.map(e => ({ session: e.canonicalSessionName, member: String(e.logicalId || "").split(".").pop(), model: e.model }));
}

function plan(dir, o) {
  const sliceYaml = path.join(dir, "slice.yaml");
  if (!fs.existsSync(sliceYaml)) throw new Usage(`no slice.yaml in ${dir}`);
  const text = read(sliceYaml);
  if (POLICY.test(text)) return { written: false, reason: "the slice already has a proofPolicy" };
  const missionRef = (/^\s+mission:\s*(\S+)/m.exec(text) || [])[1];
  if (missionRef && POLICY.test(read(path.resolve(dir, missionRef)))) return { written: false, reason: `the mission already has a proofPolicy (${missionRef})` };

  const owner = (/^owner:\s*"?([^"\s]+)"?/m.exec(read(path.join(dir, "SPEC.md"))) || [])[1];
  const builder = o["--builder"] || owner || "";
  let rig = o["--rig"] || (builder.split("@")[1] || "");
  if (!rig) {
    const who = spawnSync("rig", ["whoami", "--json"], { encoding: "utf8" });
    try { rig = JSON.parse(who.stdout).identity.rigName; } catch { rig = ""; }
  }
  if (!rig) return { written: false, reason: "cannot tell the rig: pass --rig" };

  const family = familyRule();
  const seats = seatsOf(rig).map(s => ({ ...s, family: family(s.model) }));
  const builders = builder ? seats.filter(s => s.session === builder) : seats.filter(s => BUILD.test(s.member));
  if (builder && !builders.length) return { written: false, reason: `the builder ${builder} is not a seat of ${rig}` };
  if (!builders.length) return { written: false, reason: `cannot tell the builder: no --builder, no SPEC owner, no build seat in ${rig}` };
  const unknown = [...builders, ...seats.filter(s => JUDGE.test(s.member))].filter(s => !s.family).map(s => s.session);
  if (unknown.length) return { written: false, reason: `cannot tell the model family of ${unknown.join(", ")}` };

  const taken = new Set(builders.map(s => s.family));
  const judges = [], excluded = [];
  for (const s of seats.filter(x => JUDGE.test(x.member) && !builders.includes(x))) {
    if (taken.has(s.family)) excluded.push({ seat: s.session, family: s.family, why: `same family as the builder (${s.family})` });
    else judges.push(s.session);
  }
  judges.sort();
  if (!judges.length) return { written: false, reason: `no review or QA seat outside the builder's family (${[...taken].join(", ")}) in ${rig}`, excluded };
  return { written: false, rig, builder: builders.map(s => s.session), judges, excluded, sliceYaml, text };
}

function main(argv) {
  const o = args(argv);
  const p = plan(path.resolve(o._[0]), o);
  if (p.judges && !o["--dry-run"]) {
    const day = new Date().toISOString().slice(0, 10);
    const block = `# Judges: the rig's review and QA seats outside the builder's model family (slice-judges.cjs, ${day}). Undo: delete this block.\n` +
      `proofPolicy:\n  judges:\n${p.judges.map(j => `    - ${j}\n`).join("")}`;
    fs.writeFileSync(p.sliceYaml, p.text.replace(/\n*$/, "\n") + block);
    p.written = true;
  }
  const { sliceYaml, text, ...out } = p;
  const ok = !!p.judges || /already has a proofPolicy/.test(p.reason || "");
  return { code: ok ? 0 : 1, out };
}

try {
  const { code, out } = main(process.argv.slice(2));
  const json = process.argv.includes("--json");
  process.stdout.write(json ? JSON.stringify(out, null, 2) + "\n"
    : out.judges ? `${out.written ? "wrote" : "would write"} proofPolicy.judges: ${out.judges.join(", ")}\n` : `wrote nothing: ${out.reason}\n`);
  process.exitCode = code;
} catch (e) {
  if (e instanceof Usage) { process.stderr.write(`slice-judges: ${e.message}\n`); process.exit(2); }
  process.stdout.write(process.argv.includes("--json") ? JSON.stringify({ written: false, reason: e.message }) + "\n" : `wrote nothing: ${e.message}\n`);
  process.exit(1);
}
