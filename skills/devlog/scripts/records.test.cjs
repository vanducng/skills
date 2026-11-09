// node --test skills/devlog/scripts/records.test.cjs
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const R = path.join(__dirname, "records.cjs");
const ENV = { PATH: process.env.PATH, HOME: os.tmpdir(), GIT_CONFIG_GLOBAL: "/dev/null", GIT_CONFIG_SYSTEM: "/dev/null",
  GIT_AUTHOR_NAME: "t", GIT_AUTHOR_EMAIL: "t@example.test", GIT_COMMITTER_NAME: "t", GIT_COMMITTER_EMAIL: "t@example.test" };
const run = (env, ...a) => {
  const r = spawnSync(process.execPath, [R, ...a], { env: { ...ENV, ...env }, encoding: "utf8" });
  return { code: r.status, out: r.stdout, err: r.stderr, json: () => JSON.parse(r.stdout) };
};
const put = (root, rel, body) => { fs.mkdirSync(path.dirname(path.join(root, rel)), { recursive: true }); fs.writeFileSync(path.join(root, rel), body); };

// A synthetic workspace: one public org (oss) and one client org (northwind), a person and a host in the records.
function workspace() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "devlog-ws-"));
  const slice = "orgs/northwind/projects/ledger/missions/m1/slices/03-export";
  put(root, `${slice}/PROGRESS.md`, [
    "- 2026-03-02T10:00Z: dev: retro: none escaped; the export retries now stop after 5 tries",
    "- 2026-02-20T10:00Z: dev: retro: older line, outside the week",
  ].join("\n") + "\n");
  put(root, `${slice}/proof/03-export-rev1-round1.md`,
    "---\naxes: {spec: pass, standards: pass}\ntier: Standard\nreviewed_at: 2026-03-02T09:00:00Z\n---\n");
  put(root, "orgs/oss/projects/toolkit/missions/m2/slices/01-cli/PROGRESS.md", "- 2026-03-03T08:00Z: retro: the CLI prints JSON envelopes\n");
  put(root, "orgs/northwind/contacts.yaml", "schema: x\norg: northwind\ncontacts:\n  priya:\n    name: Priya Raman\n    role: buyer\n");
  put(root, "orgs/northwind/repos.yaml", "repos:\n  ledger:\n    host: build-box-7\n");
  spawnSync("git", ["init", "-q", "-b", "main"], { cwd: root, env: ENV });
  spawnSync("git", ["add", "-A"], { cwd: root, env: ENV });
  spawnSync("git", ["commit", "-q", "-m", "feat(northwind.ledger): export retries\n\nHost: lab-mini\nRig: ledger-team\nSeat: dev@ledger-team"],
    { cwd: root, env: { ...ENV, GIT_AUTHOR_DATE: "2026-03-02T11:00:00Z", GIT_COMMITTER_DATE: "2026-03-02T11:00:00Z" } });
  const boards = fs.mkdtempSync(path.join(os.tmpdir(), "devlog-boards-"));
  put(boards, "northwind/ledger/m1/board.json", JSON.stringify({ decisions: [
    { id: "C1", q: "Retry budget?", rec: "5 tries", status: "accepted", decided: "2026-03-02" },
    { id: "Q2", q: "Open one", status: "open" },
  ] }));
  return { root, boards };
}

test("week gathers retro lines, verdicts, decisions and commit trailers since a date", () => {
  const { root, boards } = workspace();
  const r = run({ PROJECTS_ROOT: root, OPENRIG_BOARDS_ROOT: boards }, "week", "--since", "2026-03-01");
  assert.equal(r.code, 0, r.err);
  const w = r.json();
  assert.deepEqual(w.retros.map(x => x.text), ["none escaped; the export retries now stop after 5 tries", "the CLI prints JSON envelopes"]);
  assert.equal(w.retros[0].project, "northwind/ledger");
  assert.deepEqual(w.verdicts.map(v => [v.slice, v.axes]), [["03-export", "spec: pass, standards: pass"]]);
  assert.deepEqual(w.decisions.map(d => d.id), ["C1"]);
  assert.deepEqual(w.commits.map(c => [c.host, c.rig, c.seat]), [["lab-mini", "ledger-team", "dev@ledger-team"]]);
});

test("week without PROJECTS_ROOT says to fall back to git log", () => {
  const r = run({}, "week");
  assert.equal(r.code, 2);
  assert.match(r.err, /git log/);
});

test("scrub refuses a draft naming an org, client project, host or person from the records", () => {
  const { root } = workspace();
  const draft = path.join(root, "draft.txt");
  fs.writeFileSync(draft, `shipped the Northwind ledger export for Priya, built on build-box-7 and lab-mini.\nsee ${["", "Users", "someone", "x"].join("/")}\n`);
  const r = run({ PROJECTS_ROOT: root }, "scrub", draft);
  assert.equal(r.code, 1, r.out);
  const kinds = r.json().hits.map(h => `${h.kind}:${h.name}`).sort();
  assert.deepEqual(kinds, ["host:build-box-7", "host:lab-mini", "org:northwind", "path:/Users/", "person:priya", "project:ledger"]);
});

test("scrub passes a clean draft, and allowed orgs and names do not count", () => {
  const { root } = workspace();
  const draft = path.join(root, "draft.txt");
  fs.writeFileSync(draft, "the toolkit CLI prints JSON envelopes now; export retries stop after 5 tries.\n");
  assert.equal(run({ PROJECTS_ROOT: root }, "scrub", draft).code, 1); // toolkit is a project of the oss org
  const ok = run({ PROJECTS_ROOT: root, DEVLOG_ALLOW: "oss" }, "scrub", draft);
  assert.equal(ok.code, 0, ok.out);
  assert.equal(ok.json().clean, true);
  fs.writeFileSync(draft, "a ledger of what broke this week\n");
  assert.equal(run({ PROJECTS_ROOT: root, DEVLOG_ALLOW: "oss,ledger" }, "scrub", draft).code, 0);
});

test("scrub matches whole words only, so a longer word is not a hit", () => {
  const { root } = workspace();
  const draft = path.join(root, "draft.txt");
  fs.writeFileSync(draft, "ledgers and northwinds are words here; priyanka is someone else\n");
  assert.equal(run({ PROJECTS_ROOT: root, DEVLOG_ALLOW: "oss" }, "scrub", draft).code, 0);
});

test("a week too large for one pipe buffer still arrives whole", () => {
  const { root, boards } = workspace();
  const lines = Array.from({ length: 3000 }, (_, i) => `- 2026-03-04T10:00Z: dev: retro: line ${i} ${"x".repeat(60)}`);
  put(root, "orgs/oss/projects/toolkit/missions/m2/slices/02-big/PROGRESS.md", lines.join("\n") + "\n");
  const r = run({ PROJECTS_ROOT: root, OPENRIG_BOARDS_ROOT: boards }, "week", "--since", "2026-03-01");
  assert.equal(r.code, 0, r.err);
  assert.equal(r.json().retros.length, 3002);
});
