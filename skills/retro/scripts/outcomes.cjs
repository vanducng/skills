#!/usr/bin/env node
// Count review outcomes from the verdict files in one or more records (their proof/ folders).
//   outcomes.cjs <record dir>... [--json]
// Per record: verdict rounds, rounds to pass (the first verdict with every axis pass), and findings by tag and status
// (latest verdict wins per finding id). Across records: finding texts that recur, the candidates for a rule.
"use strict";
const fs = require("node:fs");
const path = require("node:path");

function blocks(text) {
  const found = [];
  const re = /^\s*---\n([\s\S]*?)\n---[ \t]*(?:\n|$)/;
  for (let m; found.length < 3 && (m = text.match(re)); text = text.slice(m[0].length)) found.push(m[1]);
  return found;
}
function verdictOf(file) {
  const b = blocks(fs.readFileSync(file, "utf8")).find(x => /^axes:\s*\{/m.test(x));
  if (!b) return null;
  const axes = Object.fromEntries((b.match(/^axes:\s*\{([^}]*)\}/m)[1]).split(",").map(p => p.split(":").map(s => s.trim())).filter(p => p[0]));
  const when = (b.match(/^reviewed_at:\s*"?([^"\n]+)/m) || [])[1] || "";
  const findings = [...b.matchAll(/^\s*-\s*\{(.*)\}\s*$/gm)].map(m => {
    const f = {};
    for (const [, k, v] of m[1].matchAll(/(\w+):\s*("(?:[^"\\]|\\.)*"|[^,]+)/g)) f[k] = v.startsWith('"') ? JSON.parse(v) : v.trim();
    return f;
  });
  return { file: path.basename(file), when, axes, pass: Object.values(axes).every(r => r === "pass"), findings };
}
function record(dir) {
  const proof = path.join(dir, "proof");
  const verdicts = (fs.existsSync(proof) ? fs.readdirSync(proof) : []).filter(n => n.endsWith(".md"))
    .map(n => verdictOf(path.join(proof, n))).filter(Boolean).sort((a, b) => (a.when + a.file).localeCompare(b.when + b.file));
  const latest = new Map();
  for (const v of verdicts) for (const f of v.findings) latest.set(f.id, f);
  const count = {};
  for (const f of latest.values()) { const k = `${f.tag}/${f.status}`; count[k] = (count[k] || 0) + 1; }
  const first = verdicts.findIndex(v => v.pass);
  return { record: dir, rounds: verdicts.length, rounds_to_pass: first === -1 ? null : first + 1, findings: count, texts: [...latest.values()].map(f => ({ id: f.id, axis: f.axis, tag: f.tag, status: f.status, text: f.text || "" })) };
}
const dirs = process.argv.slice(2).filter(a => !a.startsWith("--"));
if (!dirs.length) { process.stderr.write("usage: outcomes.cjs <record dir>... [--json]\n"); process.exit(2); }
const records = dirs.map(record);
const norm = t => t.toLowerCase().replace(/[^a-z0-9 ]+/g, " ").split(/\s+/).filter(w => w.length > 3).sort().join(" ");
const seen = new Map();
for (const r of records) for (const f of r.texts) if (f.text) { const k = `${f.axis}:${norm(f.text)}`; seen.set(k, [...(seen.get(k) || []), `${path.basename(r.record)}#${f.id}`]); }
const repeated = [...seen.entries()].filter(([, at]) => at.length > 1).map(([k, at]) => ({ class: k, at }));
const out = { records: records.map(({ texts, ...r }) => r), repeated };
process.stdout.write(process.argv.includes("--json") ? JSON.stringify(out) + "\n" : JSON.stringify(out, null, 2) + "\n");
