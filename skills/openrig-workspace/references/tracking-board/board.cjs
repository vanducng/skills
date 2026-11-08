#!/usr/bin/env node
// Tracking boards: one HTML page per initiative, rendered from board.json.
//   board.cjs init <org>/<project>/<slug> [--title "..."]   create board.json and index.html
//   board.cjs render <org>/<project>/<slug> | <dir>          rebuild index.html from board.json
//   board.cjs render --all                                   rebuild every board under the root
//   board.cjs url <org>/<project>/<slug>                     print the tailnet URL
//   board.cjs login <org>/<project>/<slug>                   print the one-time login URL (lets that browser send feedback)
//   board.cjs list                                           list boards with their headline
//   board.cjs check <org>/<project>/<slug>                   lint diagrams against the conventions; parse them with pele
//                                                            when it is installed ($PELE_DIR, default ~/.cache/openrig-boards)
// render draws each diagram with pele into the page (no CDN at view time); without pele the page shows the diagram source.
// Root: $OPENRIG_BOARDS_ROOT (default ~/.share/openrig/boards). URL base: $OPENRIG_BOARDS_URL, else the
// tailnet name from `tailscale status --json` plus /boards (see serve.sh).
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const { execFileSync } = require("node:child_process");

const root = process.env.OPENRIG_BOARDS_ROOT || path.join(os.homedir(), ".share", "openrig", "boards");
const template = path.join(__dirname, "template.html");
const slugRe = /^[a-z0-9][a-z0-9._-]*\/[a-z0-9][a-z0-9._-]*\/[a-z0-9][a-z0-9._-]*$/;

function die(msg) { console.error(`board: ${msg}`); process.exit(2); }

function boardDir(arg) {
  if (!arg) die("give <org>/<project>/<slug> or a board directory");
  if (fs.existsSync(path.join(arg, "board.json"))) return path.resolve(arg);
  if (!slugRe.test(arg)) die(`not <org>/<project>/<slug> (lowercase, digits, . _ -): ${arg}`);
  return path.join(root, arg);
}

function now() {
  const d = new Date();
  const pad = n => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

const escHtml = v => String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function loadPele() {
  const peleDir = process.env.PELE_DIR || path.join(os.homedir(), ".cache", "openrig-boards");
  try { return require(require.resolve("pele", { paths: [peleDir, __dirname] })); } catch { return null; }
}

// pele output is trusted markup, but a diagram is board text: drop anything that could run, keep only safe links,
// and give every id a prefix so two diagrams (or the wide and tall variants of one) never share a marker id.
function cleanSvg(svg, prefix) {
  const safe = u => /^(#|https?:|mailto:)/i.test(u.trim());
  let out = svg.replace(/\s(?:xlink:)?href="([^"]*)"/gi, (m, u) => (safe(u) ? m : ""));
  if (/<script|<foreignObject|\son[a-z]+\s*=/i.test(out)) return null;
  const ids = [...out.matchAll(/\sid="([^"]+)"/g)].map(m => m[1]);
  for (const id of ids) {
    out = out.split(` id="${id}"`).join(` id="${prefix}${id}"`).split(`url(#${id})`).join(`url(#${prefix}${id})`)
      .split(`href="#${id}"`).join(`href="#${prefix}${id}"`);
  }
  return out;
}

// Wide flowcharts (LR, RL) get a second, top-down drawing for phones.
function prerender(data) {
  const diagrams = data.diagrams || {}, out = {};
  const ids = Object.keys(diagrams);
  if (!ids.length) return { out, missing: false, failed: [] };
  const pele = loadPele();
  if (!pele) return { out, missing: true, failed: [] };
  const failed = [];
  ids.forEach((id, i) => {
    const src = String(diagrams[id] || "");
    try {
      const svg = cleanSvg(pele.render(src).svg, `d${i}w-`);
      if (!svg) throw new Error("diagram markup was refused");
      const flip = /^(\s*(?:flowchart|graph)\s+)(?:LR|RL)\b/;
      out[id] = { svg };
      if (flip.test(src)) {
        const tall = cleanSvg(pele.render(src.replace(flip, "$1TB")).svg, `d${i}t-`);
        if (tall) out[id].tall = tall;
      }
    } catch (e) { failed.push(`${id}: ${String(e.message).split("\n")[0]}`); }
  });
  return { out, missing: false, failed };
}

// Plain-text summary for readers without JavaScript, filled into <noscript id="summary"> at render time.
function summary(data) {
  const needs = (data.needs || []).map(n => (typeof n === "string" ? n : (n && n.text) || "")).filter(Boolean);
  const slices = (data.missions || []).flatMap(m => m.slices || []);
  const open = (data.decisions || []).filter(d => d.status !== "accepted");
  const lines = [
    `<h1>${escHtml(data.title)}</h1>`,
    data.headline ? `<p><b>${escHtml(data.headline)}</b></p>` : "",
    `<p>${escHtml([data.phase, data.updated && `updated ${data.updated}`].filter(Boolean).join(", "))}</p>`,
    `<h2>Needs you</h2>${needs.length ? `<ol>${needs.map(n => `<li>${escHtml(n)}</li>`).join("")}</ol>` : "<p>Nothing is waiting on you.</p>"}`,
    `<h2>Open decisions</h2>${open.length ? `<ul>${open.map(d => `<li>${escHtml(d.id)}: ${escHtml(d.q)} Recommended: ${escHtml(d.rec)}</li>`).join("")}</ul>` : "<p>None.</p>"}`,
    `<h2>Missions</h2><ul>${(data.missions || []).map(m => `<li>${escHtml(m.id)} ${escHtml(m.name)}: ${escHtml(m.status)}, ${(m.slices || []).filter(s => s.status === "done").length}/${(m.slices || []).length} slices done</li>`).join("")}</ul>`,
    `<p>${slices.length} slices in all. JavaScript is needed for the full board; board.json beside this file has every row.</p>`,
  ];
  return `<noscript id="summary"><div class="card plain">${lines.join("")}</div></noscript>`;
}

function render(dir) {
  const file = path.join(dir, "board.json");
  const data = JSON.parse(fs.readFileSync(file, "utf8"));
  for (const key of ["title", "missions", "decisions"]) if (!(key in data)) throw new Error(`${file} has no "${key}"`);
  const drawn = prerender(data);
  if (drawn.missing) console.error(`board: pele not installed, diagrams show their source text (npm install --prefix ${process.env.PELE_DIR || path.join(os.homedir(), ".cache", "openrig-boards")} pele@1.13.0)`);
  for (const f of drawn.failed) console.error(`board: diagram not drawn, source shown: ${f}`);
  const embedded = { ...data, rendered: { diagrams: drawn.out } };
  // \u003c keeps "</script>" and "<!--" inside the data from ending or confusing the script element.
  const json = JSON.stringify(embedded, null, 2).replace(/</g, "\\u003c");
  const html = fs.readFileSync(template, "utf8").replace("__BOARD_JSON__", () => json).replace(/<noscript id="summary">[\s\S]*?<\/noscript>/, () => summary(data));
  fs.writeFileSync(path.join(dir, "index.html"), html);
  return path.join(dir, "index.html");
}

// Every <org>/<project>/<slug> directory under the root that holds a board.json.
function boards() {
  const dirs = p => (fs.existsSync(p) ? fs.readdirSync(p, { withFileTypes: true }).filter(e => e.isDirectory() && !e.name.startsWith(".")).map(e => e.name) : []);
  const out = [];
  for (const org of dirs(root)) for (const project of dirs(path.join(root, org))) for (const slug of dirs(path.join(root, org, project)))
    if (fs.existsSync(path.join(root, org, project, slug, "board.json"))) out.push({ slug: `${org}/${project}/${slug}`, dir: path.join(root, org, project, slug) });
  return out;
}

function base() {
  if (process.env.OPENRIG_BOARDS_URL) return process.env.OPENRIG_BOARDS_URL.replace(/\/$/, "");
  for (const bin of ["tailscale", "/Applications/Tailscale.app/Contents/MacOS/Tailscale"]) {
    try {
      const self = JSON.parse(execFileSync(bin, ["status", "--json"], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] })).Self;
      return `https://${self.DNSName.replace(/\.$/, "")}/boards`;
    } catch { /* try the next binary */ }
  }
  return "?/boards";
}

const [cmd, arg, ...rest] = process.argv.slice(2);
if (cmd === "init") {
  const dir = boardDir(arg);
  if (fs.existsSync(path.join(dir, "board.json"))) die(`${dir}/board.json exists; edit it and run render`);
  const titleAt = rest.indexOf("--title");
  const [org, project, slug] = arg.split("/");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "board.json"), JSON.stringify({
    title: titleAt >= 0 ? rest[titleAt + 1] : `${org} ${project}: ${slug}`,
    org, project, slug, owner_seat: process.env.OPENRIG_SESSION_NAME || "", updated: now(), headline: "", phase: "Started",
    needs: [], sections: [], diagrams: {}, missions: [], log: [], decisions: [], facts: [], links: [],
  }, null, 2) + "\n");
  try { console.log(render(dir)); } catch (e) { die(e.message); }
  console.log(`${base()}/${arg}/`);
} else if (cmd === "render" && arg === "--all") {
  let failed = 0;
  const all = boards();
  for (const { slug, dir } of all) {
    try { console.log(render(dir)); } catch (e) { failed++; console.error(`board: ${slug}: ${e.message}`); }
  }
  console.log(`render: ${all.length - failed} of ${all.length} board(s) rendered`);
  process.exit(failed ? 1 : 0);
} else if (cmd === "render") {
  try { console.log(render(boardDir(arg))); } catch (e) { die(e.message); }
} else if (cmd === "login") {
  boardDir(arg);
  const tokenFile = path.join(root, ".board-token");
  if (!fs.existsSync(tokenFile)) die("no token yet: start the board server first (serve.sh)");
  console.log(`${base()}/${arg}/?k=${fs.readFileSync(tokenFile, "utf8").trim()}`);
} else if (cmd === "url") {
  boardDir(arg);
  console.log(`${base()}/${arg}/`);
} else if (cmd === "check") {
  const dir = boardDir(arg);
  const data = JSON.parse(fs.readFileSync(path.join(dir, "board.json"), "utf8"));
  const roles = new Set(["ours", "provider", "person", "store", "legacy", "risk", "done"]);
  const peleDir = process.env.PELE_DIR || path.join(os.homedir(), ".cache", "openrig-boards");
  const pele = loadPele();
  let problems = 0;
  const placed = new Set((data.sections || []).flatMap(s => [...(s.html || "").matchAll(/data-diagram="([^"]+)"/g)].map(m => m[1])));
  for (const [id, src] of Object.entries(data.diagrams || {})) {
    const issues = [];
    if (!placed.has(id)) issues.push("not placed in any section (<div data-diagram=\"" + id + "\"></div>)");
    if (/^\s*(classDef|style|linkStyle)\b|\bfill:|rgb\(/m.test(src)) issues.push("sets colors; use a role class (:::ours, class <subgraph> provider) or a participant type instead");
    for (const m of src.matchAll(/:::(\w+)|^\s*class\s+[\w,]+\s+(\w+)/gm)) if (!roles.has(m[1] || m[2])) issues.push(`unknown role ${m[1] || m[2]}`);
    if (/^sequenceDiagram/.test(src.trim()) && /^\s*(Note|[\w]+\s*-[->x)]+)[^\n]*;/m.test(src)) issues.push("';' inside a sequence note or message ends the statement");
    if (pele) { try { pele.render(src); } catch (e) { issues.push(`pele: ${String(e.message).split("\n")[0]}`); } }
    for (const i of issues) console.log(`${id}: ${i}`);
    problems += issues.length;
  }
  if (!pele) console.log(`check: pele not installed, parse skipped (npm install --prefix ${peleDir} pele@1.13.0)`);
  console.log(problems ? `check: ${problems} problem(s)` : "check: ok");
  process.exit(problems ? 1 : 0);
} else if (cmd === "list") {
  for (const { slug, dir } of boards()) {
    const data = JSON.parse(fs.readFileSync(path.join(dir, "board.json"), "utf8"));
    console.log(`${slug}\t${data.updated || "?"}\t${data.headline || data.title}`);
  }
} else {
  die("usage: board.cjs init|render|url|login|check <org>/<project>/<slug> [--title \"...\"] | render --all | list");
}
