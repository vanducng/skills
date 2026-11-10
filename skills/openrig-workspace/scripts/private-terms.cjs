#!/usr/bin/env node
// Private-name terms from a projects workspace's records, and a scan of text, files or a git repo against them.
// It holds no names: every term is read from $PROJECTS_ROOT (or --root) at run time.
//
//   private-terms.cjs terms [--own <org>] [--allow a,b] --json        the terms, what was allowed, what was dropped
//   private-terms.cjs scan <file|->... [--own <org>] [--allow a,b] [--shapes] --json
//   private-terms.cjs scan-repo <git dir> [--history] [--own <org>] [--allow a,b] [--shapes] [--group] --json
//                     the working tree (tracked and untracked, not ignored); --history adds every commit
//
// Exit 0 clean, 1 hits, 2 no records or a usage error (it fails closed).
// Sources: orgs/<org>/ (dir, org.yaml id, name, github_owner); repos.yaml (repo ids, the owner and repo of each origin,
// a project's host); project dirs and workspace.yaml ids; contacts.yaml (key, name, each name word of 3+ letters);
// fleet/machines.yaml (machine key, ssh_alias, hostname, openrig_host, openrig_id, the host labels of its URLs); the
// Host trailers of the workspace's commits. A term matches with no letter or digit on either side, so - _ . / # are
// boundaries; the words of a multi-word name may be joined by space, -, _ or nothing.
// One-word person terms match only in Title case; full names in any case. Placeholder hosts (local) are skipped.
// --own drops that org's org, owner, repo and project names, never its people or hosts (a host whose value is exactly
// the own org's name or owner stays masked). --allow drops org, project,
// repo and owner names that exist in the records; anything else is ignored and listed. A dropped name still masks its
// own span, so the org inside an allowed repo id is not reported. --shapes adds private paths, tailnet hosts and emails.
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const { spawn, spawnSync } = require("node:child_process");
const readline = require("node:readline");

class Usage extends Error {}
// Project and repo ids that are exactly a plain word: dropped as terms, and every drop is listed. Org names, owners,
// people and hosts are never dropped this way; neither is a longer id that contains one of these words.
const GENERIC_WORDS = new Set(["api", "app", "conductor", "dashboard", "data", "devlog", "docs", "http", "infra", "ops", "platform", "products", "projects", "skills", "web", "workspace"]);
const GENERIC_KINDS = new Set(["project", "repo"]);
const ALLOWABLE = new Set(["org", "project", "repo", "owner"]);
const PLACEHOLDER_HOSTS = new Set(["local", "localhost", "127.0.0.1"]);
// A one-word person term (a key or one word of a name) matches only in Title case: "Raman", never raman_mode.
const titleOnly = e => e.kind === "person" && !/[\s_-]/.test(e.term);
// The forms a one-word person term matches: canonical Title case, plus the stored form when that is mixed case (McDonald).
const titles = t => [...new Set([t[0].toUpperCase() + t.slice(1).toLowerCase(), ...(/[a-z]/.test(t) && /[A-Z]/.test(t.slice(1)) ? [t] : [])])];
const SHAPES = [
  ["/Users/", /\/Users\/[^/\s"'`]+/], ["/home/", /\/home\/[^/\s"'`]+/], ["/Volumes/", /\/Volumes\/[^/\s"'`]+/],
  ["tailnet host", /\b[\w-]+\.ts\.net\b/], ["email", /\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b/],
];

const read = f => { try { return fs.readFileSync(f, "utf8"); } catch { return ""; } };
const dirs = d => { try { return fs.readdirSync(d, { withFileTypes: true }).filter(e => e.isDirectory()).map(e => e.name).sort(); } catch { return []; } };

// A flow collection ({a: 1, b: [x, "y, z"]}), nested, with quoted strings; a trailing comment is ignored.
function flow(s) {
  let i = 0;
  const ws = () => { while (/\s/.test(s[i] || "")) i++; };
  const atom = stop => {
    ws();
    if (s[i] === '"' || s[i] === "'") { const q = s[i++]; let v = ""; while (i < s.length && s[i] !== q) v += s[i++]; i++; return v; }
    let v = ""; while (i < s.length && !stop.includes(s[i])) v += s[i++];
    return v.trim();
  };
  const value = () => {
    ws();
    if (s[i] === "{") {
      i++; const m = {};
      for (ws(); i < s.length && s[i] !== "}"; ws()) {
        const k = atom(":,}"); if (s[i] === ":") i++;
        const v = /[,}]/.test((ws(), s[i])) ? "" : value();
        if (k) m[k] = v;
        ws(); if (s[i] === ",") i++;
      }
      i++; return m;
    }
    if (s[i] === "[") {
      i++; const l = [];
      for (ws(); i < s.length && s[i] !== "]"; ws()) { const v = value(); if (v !== "") l.push(v); ws(); if (s[i] === ",") i++; }
      i++; return l;
    }
    return atom(",}]");
  };
  return value();
}

// A YAML subset reader for these records: block maps and lists, flow maps and lists, quoted or plain scalars, comments.
function yaml(text) {
  const lines = [];
  for (const raw of text.split("\n")) {
    if (/^\s*(#|$)/.test(raw) || /^(---|\.\.\.)\s*$/.test(raw)) continue;
    lines.push({ indent: raw.match(/^ */)[0].length, text: raw.trim() });
  }
  let i = 0;
  const scalar = s => {
    s = s.trim();
    if (s[0] === "{" || s[0] === "[") return flow(s);
    const q = s.match(/^(["'])(.*?)\1\s*(#.*)?$/);
    if (q) return q[2];
    return s.replace(/\s+#.*$/, "");
  };
  const block = indent => {
    if (i >= lines.length || lines[i].indent < indent) return null;
    const at = lines[i].indent;
    if (lines[i].text.startsWith("- ") || lines[i].text === "-") {
      const list = [];
      while (i < lines.length && lines[i].indent === at && (lines[i].text.startsWith("- ") || lines[i].text === "-")) {
        const rest = lines[i].text.slice(1).trim();
        if (!rest) { i++; list.push(block(at + 1)); continue; }
        if (/^[^"'[{][^:]*:(\s|$)/.test(rest)) { lines[i] = { indent: at + 2, text: rest }; list.push(block(at + 2)); continue; }
        i++; list.push(scalar(rest));
      }
      return list;
    }
    const map = {};
    while (i < lines.length && lines[i].indent === at) {
      const m = lines[i].text.match(/^("[^"]*"|'[^']*'|[^:]+?):(?:\s+(.*))?$/);
      if (!m) { i++; continue; }
      const key = scalar(m[1]);
      i++;
      map[key] = m[2] !== undefined && m[2] !== "" ? scalar(m[2]) : block(at + 1);
    }
    return map;
  };
  return block(0) || {};
}
const doc = f => yaml(read(f));

function origin(url) {
  const m = String(url || "").match(/[:/]([^/:\s]+)\/([^/\s]+?)(?:\.git)?\/?$/);
  return m ? { owner: m[1], repo: m[2] } : null;
}

// Every term entry the records hold: {term, kind, org, source}. One term may come from several sources.
function entries(root, warnings = []) {
  const out = [];
  const add = (term, kind, org, source) => {
    const t = String(term || "").trim();
    if (t.length >= 3 && !(kind === "host" && PLACEHOLDER_HOSTS.has(t.toLowerCase()))) out.push({ term: t, kind, org, source });
  };
  for (const org of dirs(path.join(root, "orgs"))) {
    const base = `orgs/${org}`;
    add(org, "org", org, base);
    const o = doc(path.join(root, base, "org.yaml"));
    add(o.id, "org", org, `${base}/org.yaml`);
    add(o.name, "org", org, `${base}/org.yaml`);
    add(o.github_owner, "owner", org, `${base}/org.yaml`);
    for (const r of [].concat(doc(path.join(root, base, "repos.yaml")).repos || [])) {
      if (!r || typeof r !== "object") continue;
      add(r.id, "repo", org, `${base}/repos.yaml`);
      const g = origin(r.origin);
      if (g) { add(g.owner, "owner", org, `${base}/repos.yaml`); add(g.repo, "repo", org, `${base}/repos.yaml`); }
    }
    for (const project of dirs(path.join(root, base, "projects"))) {
      const p = `${base}/projects/${project}`;
      add(project, "project", org, p);
      const pr = doc(path.join(root, p, "repos.yaml"));
      add(pr.host, "host", org, `${p}/repos.yaml`);
      for (const r of [].concat(pr.repos || [])) add(typeof r === "string" ? r : r && r.id, "repo", org, `${p}/repos.yaml`);
    }
    const contacts = doc(path.join(root, base, "contacts.yaml")).contacts || {};
    for (const [key, c] of Object.entries(typeof contacts === "object" ? contacts : {})) {
      add(key, "person", org, `${base}/contacts.yaml`);
      const name = c && typeof c === "object" ? String(c.name || "") : "";
      add(name, "person", org, `${base}/contacts.yaml`);
      for (const w of name.split(/\s+/)) add(w, "person", org, `${base}/contacts.yaml`); // a surname alone still names them
    }
  }
  const ws = doc(path.join(root, "workspace.yaml"));
  for (const p of [].concat(ws.projects || [])) {
    const [org, ...rest] = String((p && p.id) || "").split(".");
    if (rest.length) add(rest.join("."), "project", org, "workspace.yaml");
  }
  for (const o of [].concat(ws.orgs || [])) add(o && o.id, "org", o && o.id, "workspace.yaml");
  const machines = doc(path.join(root, "fleet/machines.yaml")).machines || {};
  for (const [key, m] of Object.entries(typeof machines === "object" ? machines : {})) {
    add(key, "host", null, "fleet/machines.yaml");
    if (!m || typeof m !== "object") continue;
    for (const f of ["ssh_alias", "hostname", "openrig_host", "openrig_id"]) add(m[f], "host", null, "fleet/machines.yaml");
    for (const f of ["openrig_url", "rex_url"]) {
      const h = (String(m[f] || "").match(/^\w+:\/\/([^/:]+)/) || [])[1];
      if (h) for (const label of h.split(".").filter(l => !["ts", "net"].includes(l))) add(label, "host", null, "fleet/machines.yaml");
    }
  }
  const log = spawnSync("git", ["-C", root, "log", "-n", "5000", "--format=%(trailers:key=Host,valueonly,separator=%x0a)"], { encoding: "utf8" });
  if (log.status === 0) for (const h of log.stdout.split("\n")) add(h, "host", null, "git log Host trailers");
  else warnings.push("git log Host trailers: not read (not a git repository?)");
  return out;
}

const norm = t => t.toLowerCase().replace(/[\s_-]+/g, "");

// The term set for one caller: kept terms, masked (own or allowed) terms, and the lists that make each drop visible.
function load(root, { own = "", allow = [] } = {}) {
  if (!root || !fs.existsSync(path.join(root, "orgs"))) throw new Usage("no workspace records ($PROJECTS_ROOT unset or without orgs/): nothing to check against");
  const warnings = [];
  const all = entries(root, warnings);
  const asked = [...new Set(allow.map(a => a.trim().toLowerCase()).filter(Boolean))].sort();
  const allowable = new Set(all.filter(e => ALLOWABLE.has(e.kind)).map(e => e.term.toLowerCase()));
  const allowed = asked.filter(a => allowable.has(a));
  // The own org's exact name, id and owner stay masked even where a host has the same value (they are public already).
  const ownExact = new Set(all.filter(e => own && e.org === own && (e.kind === "org" || e.kind === "owner")).map(e => e.term.toLowerCase()));
  const keep = new Map(), mask = new Map(), dropped = new Map();
  for (const e of all) {
    const k = e.term.toLowerCase();
    if (GENERIC_KINDS.has(e.kind) && GENERIC_WORDS.has(k)) { if (!dropped.has(k)) dropped.set(k, { ...e, why: "generic word" }); continue; }
    const ownName = own && e.org === own && ALLOWABLE.has(e.kind);
    if (ownName || ownExact.has(k) || (ALLOWABLE.has(e.kind) && allowed.includes(k))) { mask.set(norm(e.term), e); continue; }
    // One term, several sources: the any-case match wins over the Title-case-only person match.
    if (!keep.has(k) || (titleOnly(keep.get(k)) && !titleOnly(e))) keep.set(k, e);
  }
  for (const k of keep.keys()) mask.delete(norm(keep.get(k).term)); // a name kept by any source is reported
  for (const k of keep.keys()) dropped.delete(k);
  return { root, terms: [...keep.values()], masked: [...mask.values()], allowed, ignored_allow: asked.filter(a => !allowed.includes(a)),
    dropped: [...dropped.values()], warnings, ...matcher([...keep.values()], [...mask.values()]) };
}

// Two regexes: any case for most terms, exact Title case for one-word person terms. Matches from both are resolved by
// span (the longest wins), so a full name or a masked name is never also reported in part.
function matcher(keep, mask) {
  const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const any = new Map(), exact = new Map();
  for (const e of keep) {
    if (titleOnly(e)) for (const f of titles(e.term)) exact.set(f, { entry: e, report: true });
    else any.set(norm(e.term), { entry: e, report: true });
  }
  for (const e of mask) if (!any.has(norm(e.term))) any.set(norm(e.term), { entry: e, report: false });
  const build = (terms, flags) => {
    const alts = terms.sort((a, b) => b.length - a.length).map(t => t.split(/[\s_-]+/).filter(Boolean).map(esc).join("[\\s_-]*"));
    return alts.length ? new RegExp(`(?<![\\p{L}\\p{N}])(?:${alts.join("|")})(?![\\p{L}\\p{N}])`, flags) : null;
  };
  return { any, exact, reAny: build([...any.values()].map(v => v.entry.term), "giu"), reExact: build([...exact.keys()], "gu") };
}

function matches(line, t) {
  const found = [];
  if (t.reAny) for (const m of line.matchAll(t.reAny)) found.push({ at: m.index, end: m.index + m[0].length, v: t.any.get(norm(m[0])) });
  if (t.reExact) for (const m of line.matchAll(t.reExact)) found.push({ at: m.index, end: m.index + m[0].length, v: t.exact.get(m[0]) });
  found.sort((a, b) => a.at - b.at || b.end - a.end);
  const kept = [];
  for (const f of found) if (f.v && !kept.some(k => f.at < k.end && k.at < f.end)) kept.push(f);
  return kept.filter(f => f.v.report).map(f => f.v.entry);
}

// Hits in one text: [{term, kind, org, source, line}], at most one per term per line.
function scanText(text, t, { shapes = false } = {}) {
  const hits = [];
  String(text).split("\n").forEach((line, n) => {
    const seen = new Set();
    for (const e of matches(line, t))
      if (!seen.has(e.term)) { seen.add(e.term); hits.push({ term: e.term, kind: e.kind, org: e.org, source: e.source, line: n + 1 }); }
    if (shapes) for (const [label, re] of SHAPES) if (re.test(line)) hits.push({ term: label, kind: "path", org: null, source: "shape", line: n + 1 });
  });
  return hits;
}

// The working tree: tracked and untracked files, not ignored ones. A file that cannot be read is listed in `skipped`.
function treeHits(repo, t, opts, skipped) {
  const ls = spawnSync("git", ["-C", repo, "ls-files", "-z", "--cached", "--others", "--exclude-standard"], { encoding: "utf8", maxBuffer: 1 << 28 });
  if (ls.status !== 0) throw new Usage(`${repo} is not a git repository`);
  const hits = [];
  for (const file of [...new Set(ls.stdout.split("\0").filter(Boolean))]) {
    let buf; try { buf = fs.readFileSync(path.join(repo, file)); } catch { skipped.push(file); continue; }
    if (buf.includes(0)) continue; // binary
    for (const h of scanText(buf.toString("utf8"), t, opts)) hits.push({ ...h, file });
    for (const h of scanText(file, t, opts)) hits.push({ ...h, file, line: 0 }); // the path itself
  }
  return hits;
}

// Every commit's added lines and message, streamed: one hit per term, file and commit.
function historyHits(repo, t, opts) {
  return new Promise((resolve, reject) => {
    const p = spawn("git", ["-C", repo, "log", "--all", "-p", "--no-color", "--no-ext-diff", "--format=%x00%H%n%B%x00"]);
    const hits = [], seen = new Set();
    let commit = "", file = "(message)", inMsg = false;
    const rl = readline.createInterface({ input: p.stdout, crlfDelay: Infinity });
    rl.on("line", raw => {
      if (inMsg && raw.endsWith("\0")) { inMsg = false; raw = raw.slice(0, -1); } // the message's closing NUL
      else if (raw.startsWith("\0")) { commit = raw.slice(1, 13); inMsg = true; file = "(message)"; return; }
      let text = null;
      if (inMsg) text = raw;
      else if (raw.startsWith("+++ ")) { file = raw.replace(/^\+\+\+ (b\/)?/, ""); text = file; }
      else if (raw.startsWith("+") && !raw.startsWith("+++")) text = raw.slice(1);
      if (text === null) return;
      for (const h of scanText(text, t, opts)) {
        const k = `${h.term}\0${file}\0${commit}`;
        if (!seen.has(k)) { seen.add(k); hits.push({ term: h.term, kind: h.kind, org: h.org, source: h.source, file, commit }); }
      }
    });
    p.on("error", reject);
    p.on("close", code => code === 0 ? resolve(hits) : reject(new Usage(`git log failed in ${repo}`)));
  });
}

// Hits by term for a hand review: kind, count, and the first three places (file:line, or file@commit in history).
function group(hits) {
  const by = new Map();
  for (const h of hits) {
    const g = by.get(h.term) || { term: h.term, kind: h.kind, count: 0, first: [] };
    g.count++;
    if (g.first.length < 3) g.first.push(h.commit ? `${h.file}@${h.commit}` : `${h.file}:${h.line}`);
    by.set(h.term, g);
  }
  return [...by.values()].sort((a, b) => b.count - a.count || a.term.localeCompare(b.term));
}

function args(argv) {
  const o = { _: [], "--allow": "" };
  const flags = new Set(["--json", "--history", "--shapes", "--group"]);
  const valued = new Set(["--own", "--allow", "--root"]);
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (flags.has(a)) o[a] = true;
    else if (valued.has(a)) { if (argv[i + 1] === undefined) throw new Usage(`${a} needs a value`); o[a] = argv[++i]; }
    else if (a.startsWith("--")) throw new Usage(`unknown flag ${a}`);
    else o._.push(a);
  }
  return o;
}

async function main(argv) {
  const [cmd, ...rest] = argv;
  const o = args(rest);
  const t = () => load(o["--root"] || process.env.PROJECTS_ROOT || "", { own: o["--own"] || "", allow: o["--allow"].split(",") });
  const opts = { shapes: !!o["--shapes"] };
  const meta = x => ({ allowed: x.allowed, ignored_allow: x.ignored_allow, dropped: x.dropped, warnings: x.warnings });
  if (cmd === "terms") { const x = t(); return { code: 0, out: { terms: x.terms, masked: x.masked, ...meta(x) } }; }
  if (cmd === "scan") {
    if (!o._.length) throw new Usage("scan <file|->...");
    const x = t(), hits = [];
    for (const f of o._) {
      const text = f === "-" ? fs.readFileSync(0, "utf8") : fs.readFileSync(f, "utf8");
      for (const h of scanText(text, x, opts)) hits.push({ ...h, file: f });
    }
    return { code: hits.length ? 1 : 0, out: { clean: !hits.length, hits, ...meta(x) } };
  }
  if (cmd === "scan-repo") {
    if (!o._[0]) throw new Usage("scan-repo <git dir>");
    const x = t();
    // --history covers every commit and the working tree as it is now.
    const skipped = [];
    const hits = [...(o["--history"] ? await historyHits(o._[0], x, opts) : []), ...treeHits(o._[0], x, opts, skipped)];
    const out = { repo: o._[0], history: !!o["--history"], clean: !hits.length, skipped, ...meta(x) };
    return { code: hits.length ? 1 : 0, out: o["--group"] ? { ...out, groups: group(hits) } : { ...out, hits } };
  }
  throw new Usage("usage: private-terms.cjs terms|scan|scan-repo (see the header of this file)");
}

if (require.main === module) {
  main(process.argv.slice(2)).then(({ code, out }) => {
    process.stdout.write(JSON.stringify(out, null, 2) + "\n");
    process.exitCode = code; // not process.exit: a large answer on a pipe would be cut before it drains
  }, e => {
    if (!(e instanceof Usage)) { process.stderr.write(`private-terms.cjs: ${e.stack || e}\n`); process.exitCode = 2; return; }
    process.stderr.write(`private-terms.cjs: ${e.message}\n`);
    process.exitCode = 2;
  });
}

module.exports = { GENERIC_WORDS, load, scanText, entries, yaml };
