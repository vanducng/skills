// node --test skills/intake/scripts/contract.test.cjs
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const C = path.join(__dirname, "contract.cjs");
const run = (...a) => spawnSync(process.execPath, [C, ...a], { encoding: "utf8" });

test("--list names every work type, the BI dashboard among them", () => {
  const r = run("--list");
  assert.equal(r.status, 0);
  const types = r.stdout.trim().split("\n");
  for (const t of ["feature", "bug-fix", "investigation", "data-analysis", "bi-dashboard"]) assert.ok(types.includes(t), t);
});

test("the BI dashboard contract carries the bi-dash proof: sheet, mockup sign-off, field map, reconciliation, UAT, glossary", () => {
  const r = run("BI dashboard");
  assert.equal(r.status, 0, r.stderr);
  const lines = r.stdout.trim().split("\n");
  assert.ok(lines.every(l => l.startsWith("- [ ] ")), r.stdout);
  for (const want of [/question sheet/i, /mockup.*sign/i, /field map.*missing.*variant|field map.*variant.*missing/i, /reconcil.*tolerance/i, /UAT|screenshot/i, /glossary/i])
    assert.ok(lines.some(l => want.test(l)), String(want));
});

test("an unknown type exits 2 and lists the types", () => {
  const r = run("dashboardz");
  assert.equal(r.status, 2);
  assert.match(r.stderr, /bi-dashboard/);
});
