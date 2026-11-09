#!/usr/bin/env node
// Workspace records for a devlog, and the scrub gate a draft passes before anyone sees it.
//
//   records.cjs week [--since YYYY-MM-DD] [--root <dir>]   JSON: retro lines, review verdicts, board decisions and commit
//                                                         trailers (Host, Rig, Seat) across <root>/orgs/*/projects/*
//   records.cjs scrub <draft-file> [--root <dir>]          exit 0 clean; exit 1 with the hits: an org, a project, a host
//                                                         or a person named in the records, or a private path; exit 2
//                                                         with no records
//
// <root> is $PROJECTS_ROOT; without one, `week` exits 2 (use plain git log). Boards come from $OPENRIG_BOARDS_ROOT
// (default ~/.share/openrig/boards). $DEVLOG_ALLOW (comma list) names public orgs and projects from the records; the
// scrub lets those names through, reports them, and ignores every other value.
"use strict";
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

class Usage extends Error {}
const read = f => { try { return fs.readFileSync(f, "utf8"); } catch { return ""; } };
const dirs = d => { try { return fs.readdirSync(d, { withFileTypes: true }).filter(e => e.isDirectory()).map(e => e.name).sort(); } catch { return []; } };
const files = d => { try { return fs.readdirSync(d).filter(n => n.endsWith(".md")).sort(); } catch { return []; } };
const day = s => (String(s || "").match(/\d{4}-\d{2}-\d{2}/) || [""])[0];

function projects(root) {
  const out = [];
  for (const org of dirs(path.join(root, "orgs")))
    for (const project of dirs(path.join(root, "orgs", org, "projects"))) out.push({ org, project, dir: path.join(root, "orgs", org, "projects", project) });
  return out;
}

function slices(p) {
  const out = [];
  for (const m of dirs(path.join(p.dir, "missions")))
    for (const s of dirs(path.join(p.dir, "missions", m, "slices"))) out.push({ mission: m, slice: s, dir: path.join(p.dir, "missions", m, "slices", s) });
  return out;
}

function week(root, since) {
  const after = d => !since || (d && d >= since);
  const w = { root, since: since || null, retros: [], verdicts: [], decisions: [], commits: [] };
  for (const p of projects(root)) {
    const project = `${p.org}/${p.project}`;
    for (const s of slices(p)) {
      for (const line of read(path.join(s.dir, "PROGRESS.md")).split("\n")) {
        const m = line.match(/^\s*-\s*(\S*?)\s*:?\s*(?:[\w.@-]+:\s*)?retro:\s*(.+)$/i);
        if (m && after(day(m[1]))) w.retros.push({ project, slice: s.slice, date: day(m[1]), text: m[2].trim() });
      }
      for (const f of files(path.join(s.dir, "proof"))) {
        const text = read(path.join(s.dir, "proof", f));
        const axes = (text.match(/^axes:\s*\{([^}]*)\}/m) || [])[1];
        const when = day((text.match(/^reviewed_at:\s*(\S+)/m) || [])[1]);
        if (axes && after(when)) w.verdicts.push({ project, slice: s.slice, file: f, date: when, axes: axes.trim() });
      }
    }
  }
  const boards = process.env.OPENRIG_BOARDS_ROOT || path.join(os.homedir(), ".share/openrig/boards");
  for (const org of dirs(boards)) for (const project of dirs(path.join(boards, org))) for (const slug of dirs(path.join(boards, org, project))) {
    let board; try { board = JSON.parse(read(path.join(boards, org, project, slug, "board.json"))); } catch { continue; }
    for (const d of board.decisions || [])
      if (/^(accepted|c)$/i.test(String(d.status || "")) && d.decided && after(day(d.decided))) w.decisions.push({ board: `${org}/${project}/${slug}`, id: d.id, q: d.q, rec: d.rec, decided: day(d.decided) });
  }
  const log = spawnSync("git", ["-C", root, "log", ...(since ? [`--since=${since}`] : ["-n", "200"]),
    "--format=%H%x1f%cs%x1f%s%x1f%(trailers:key=Host,valueonly,separator=%x2c)%x1f%(trailers:key=Rig,valueonly,separator=%x2c)%x1f%(trailers:key=Seat,valueonly,separator=%x2c)%x1e"], { encoding: "utf8" });
  if (log.status === 0)
    for (const rec of log.stdout.split("\x1e").map(r => r.trim()).filter(Boolean)) {
      const [sha, date, subject, host, rig, seat] = rec.split("\x1f").map(x => x.trim());
      if (host || rig || seat) w.commits.push({ sha: sha.slice(0, 12), date, subject, host, rig, seat });
    }
  return w;
}

// Every private name the records hold, with its kind. DEVLOG_ALLOW may name orgs and projects from the records only:
// an allowed org drops its own name and its projects' names, never its people or hosts. Other values are ignored.
function names(root) {
  const asked = [...new Set((process.env.DEVLOG_ALLOW || "").split(",").map(s => s.trim().toLowerCase()).filter(Boolean))].sort();
  const orgs = dirs(path.join(root, "orgs")).map(org => ({ org, projects: dirs(path.join(root, "orgs", org, "projects")) }));
  const public_ = new Set(orgs.flatMap(o => [o.org, ...o.projects]).map(n => n.toLowerCase()));
  const allowed = asked.filter(n => public_.has(n));
  const found = new Map();
  const add = (kind, name, allowable = false) => {
    const n = String(name || "").trim().replace(/^["']|["']$/g, "");
    if (n.length < 3 || found.has(n.toLowerCase()) || (allowable && allowed.includes(n.toLowerCase()))) return;
    found.set(n.toLowerCase(), { kind, name: n });
  };
  for (const { org, projects } of orgs) {
    if (!allowed.includes(org.toLowerCase())) {
      add("org", org, true);
      for (const project of projects) add("project", project, true);
    }
    const contacts = read(path.join(root, "orgs", org, "contacts.yaml"));
    for (const m of contacts.matchAll(/^ {2}([A-Za-z][\w.-]*):\s*$/gm)) add("person", m[1]);
    for (const m of contacts.matchAll(/^\s+name:\s*(.+)$/gm)) {
      add("person", m[1]);
      for (const token of m[1].replace(/^["']|["']$/g, "").split(/\s+/)) add("person", token); // a surname alone still names them
    }
    for (const m of read(path.join(root, "orgs", org, "repos.yaml")).matchAll(/^\s*host:\s*(\S+)/gm)) add("host", m[1]);
  }
  const log = spawnSync("git", ["-C", root, "log", "-n", "2000", "--format=%(trailers:key=Host,valueonly,separator=%x0a)"], { encoding: "utf8" });
  if (log.status === 0) for (const h of log.stdout.split("\n")) add("host", h);
  return { names: [...found.values()], allowed, ignored_allow: asked.filter(n => !allowed.includes(n)) };
}

// Private by shape, whatever the records say; a hit is reported by its label, never by the user or host it names.
const PATHS = [
  ["/Users/", /\/Users\//], ["/home/", /\/home\/[^/\s]+/], ["/Volumes/", /\/Volumes\/[^/\s]+/],
  ["tailnet host", /\b[\w-]+\.ts\.net\b/], ["email", /\b[\w.+-]+@[\w-]+\.[\w.-]+\b/],
];

function scrub(file, root) {
  const lines = fs.readFileSync(file, "utf8").split("\n");
  const hits = [];
  const first = re => lines.findIndex(l => re.test(l)) + 1; // 0 when no line matches
  const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const known = names(root);
  for (const { kind, name } of known.names) {
    // A hyphen is a boundary: an org inside `org-repo#12` is still the org. A longer word (`ledgers`) is not a hit.
    const re = new RegExp(`(^|[^\\p{L}\\p{N}_])${esc(name)}(?![\\p{L}\\p{N}_])`, "iu");
    const line = first(re);
    if (line) hits.push({ kind, name, line });
  }
  for (const [name, re] of PATHS) {
    const line = first(re);
    if (line) hits.push({ kind: "path", name, line });
  }
  return { file, clean: hits.length === 0, hits, allowed: known.allowed, ignored_allow: known.ignored_allow };
}

function main(argv) {
  const [cmd, ...rest] = argv;
  const o = { _: [] };
  for (let i = 0; i < rest.length; i++) {
    if (!rest[i].startsWith("--")) { o._.push(rest[i]); continue; }
    if (rest[i + 1] === undefined) throw new Usage(`${rest[i]} needs a value`);
    o[rest[i]] = rest[++i];
  }
  const root = o["--root"] || process.env.PROJECTS_ROOT || "";
  if (cmd === "week") {
    if (!root || !fs.existsSync(path.join(root, "orgs"))) throw new Usage("no workspace records ($PROJECTS_ROOT unset or without orgs/): use plain git log");
    if (o["--since"] && !/^\d{4}-\d{2}-\d{2}$/.test(o["--since"])) throw new Usage("--since takes YYYY-MM-DD");
    return { code: 0, out: week(root, o["--since"]) };
  }
  if (cmd === "scrub") {
    if (!o._[0]) throw new Usage("scrub <draft-file>");
    // No records means no names to check: that is not a clean draft.
    if (!root || !fs.existsSync(path.join(root, "orgs"))) throw new Usage("no workspace records ($PROJECTS_ROOT unset or without orgs/): the scrub cannot check names");
    const r = scrub(o._[0], root);
    return { code: r.clean ? 0 : 1, out: r };
  }
  throw new Usage("usage: records.cjs week|scrub (see the header of this file)");
}

try {
  const { code, out } = main(process.argv.slice(2));
  process.stdout.write(JSON.stringify(out, null, 2) + "\n");
  process.exitCode = code; // not process.exit: a large answer on a pipe would be cut before it drains
} catch (e) {
  if (!(e instanceof Usage)) throw e;
  process.stderr.write(`records.cjs: ${e.message}\n`);
  process.exit(2);
}
