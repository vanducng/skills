#!/usr/bin/env node
// The review verdict, bound to the exact diff it judged.
//
//   verdict.cjs tier  --base <ref> [--head <ref>]           Quick | Standard | Deep, the axes it needs, and why
//   verdict.cjs round <proof-dir> [--seat S] [--pr N]        this review's round number (prior verdicts + 1: with --pr, that
//                                                          PR's of any seat; else this seat's), the proof artifact type and
//                                                          file name (with the PR number when given); exit 3 past round 3
//   verdict.cjs write --base <ref> [--head <ref>] --out <file> --spec R --standards R [--security R]
//                     [--finding "F1|spec|Important|open|one line"]... [--seat S] [--family F: vendor family, e.g. claude] [--round N]
//                     [--pr N: recorded as pr: N, which round --pr counts]
//   verdict.cjs check <file> --base <ref> [--head <ref>]    does the file still bind to <base>..<head>?
//
// R is pass | fail | inconclusive. The binding is the merge-base diff's `git patch-id --stable` (ignores whitespace)
// and the sha256 of `git diff --binary` (does not), the same keys `fleet verdict-check` recomputes.
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { spawnSync } = require("node:child_process");

const RESULTS = ["pass", "fail", "inconclusive"];
const TAGS = ["Important", "Nit", "Pre-existing"];
const STATUSES = ["open", "fixed", "declined"];
const AXES = ["spec", "standards", "security"];
// Paths that make a change Deep (adds the security axis): auth, secrets, migrations, CI, money, infra.
const DEEP = /(^|\/)(auth|login|session|secrets?|credentials?|\.env|migrations?|\.github\/workflows|ci|billing|payments?|money|invoice|terraform|infra|k8s|helm|Dockerfile)(\/|\.|$)/i;
// API surface is Deep too: a routes/api file, a route, controller, handler or endpoint file under an api/ path, an
// Api controller folder, or an OpenAPI or Swagger spec. Generic shapes only, no framework list.
const API = [
  /(^|\/)routes\/api\.[a-z]+$/i,
  /(^|\/)api\/(?:[^/]+\/)*[^/]*(route|controller|handler|endpoint)s?[^/]*\.[a-z]+$/i,
  /(^|\/)controllers?\/api\//i,
  /(^|\/)(openapi|swagger)[^/]*\.(ya?ml|json)$/i,
];
// A configs/ change that sets a key which writes to people (post, send, notify, a chat, email or webhook target) is
// Deep, whatever the file type: one added key can switch on an automatic message.
const CONFIG = /(^|\/)configs?\//i;
const MESSAGE_KEY = /^\+[ \t]*(?:[-*][ \t]+)?["']?([\w.-]*(?:post|posting|send|sending|notify|notification|slack|email|webhook|message|reply)[\w.-]*)["']?[ \t]*[:=]/gim;
const DOCS = /\.(md|mdx|txt|rst)$|(^|\/)docs\//i;
// A REVIEW.md line "Security axis: always" asks for the security axis on every change, whatever the tier. Read at the
// base and the head: a PR that deletes the line still needs the axis it would drop.
const ASKS_SECURITY = /^[ \t]*(?:[-*][ \t]+)?\**security axis\**:[ \t]*always\b/im;

class Fail extends Error {}
function git(args, opts = {}) {
  const r = spawnSync("git", args, { encoding: opts.binary ? "buffer" : "utf8", input: opts.input, maxBuffer: 1 << 28 });
  if (r.status !== 0) throw new Fail(`git ${args[0]} failed: ${String(r.stderr).trim().slice(0, 200)}`);
  return r.stdout;
}

function keys(base, head) {
  const mergeBase = git(["merge-base", base, head]).trim();
  const headSha = git(["rev-parse", head]).trim();
  const plain = git(["diff", `${mergeBase}..${headSha}`], { binary: true });
  const patch = String(git(["patch-id", "--stable"], { input: plain })).split(/\s+/)[0] || "";
  const digest = crypto.createHash("sha256").update(git(["diff", "--binary", `${mergeBase}..${headSha}`], { binary: true })).digest("hex");
  return { base: mergeBase, head: headSha, patch_id: patch, diff_digest: `sha256:${digest}` };
}

function tier(base, head, k = keys(base, head)) {
  const rows = git(["diff", "--numstat", `${k.base}..${k.head}`]).trim().split("\n").filter(Boolean).map(l => l.split("\t"));
  const files = rows.map(r => r[2]);
  const lines = rows.reduce((n, r) => n + (Number(r[0]) || 0) + (Number(r[1]) || 0), 0);
  if (!files.length) throw new Fail(`${k.base.slice(0, 12)}..${k.head.slice(0, 12)} changes nothing: there is no diff to judge`);
  const deep = files.filter(f => DEEP.test(f) || API.some(re => re.test(f)));
  if (deep.length) return { tier: "Deep", axes: ["spec", "standards", "security"], why: `risky paths: ${deep.join(", ")}`, files: files.length, lines };
  const configs = files.filter(f => CONFIG.test(f));
  const msgKeys = configs.length ? [...git(["diff", "-U0", `${k.base}..${k.head}`, "--", ...configs]).matchAll(MESSAGE_KEY)].map(m => m[1]) : [];
  if (msgKeys.length) return { tier: "Deep", axes: ["spec", "standards", "security"], why: `message-writing config: ${[...new Set(msgKeys)].join(", ")}`, files: files.length, lines };
  const t = files.every(f => DOCS.test(f)) ? { tier: "Quick", why: "docs only" }
    : { tier: lines < 50 ? "Quick" : "Standard", why: `${lines} changed lines, no risky path` };
  if (asksSecurity(k.base) || asksSecurity(k.head)) return { ...t, axes: ["spec", "standards", "security"], why: `${t.why}; REVIEW.md asks for the security axis`, files: files.length, lines };
  return { ...t, axes: ["spec", "standards"], files: files.length, lines };
}

function asksSecurity(head) {
  const r = spawnSync("git", ["show", `${head}:REVIEW.md`], { encoding: "utf8" });
  return r.status === 0 && ASKS_SECURITY.test(r.stdout);
}

// The leading `---` blocks of a file (the C1 header, then the verdict's own), as fleet's verdict check reads them.
function blocks(text) {
  const found = [];
  const block = /^\s*---\n([\s\S]*?)\n---[ \t]*(?:\n|$)/;
  for (let m; found.length < 3 && (m = text.match(block)); text = text.slice(m[0].length)) found.push(m[1]);
  return found;
}
const isVerdict = text => blocks(text).some(b => /^axes:\s*\{/m.test(b));

function prNumber(v) {
  const n = String(v).replace(/^#/, "");
  if (!/^\d+$/.test(n)) throw new Fail(`--pr takes the PR number, not '${v}'`);
  return n;
}

// With a PR number, only that PR's verdicts count (any seat: a rename does not reset the rounds); else the seat's.
function priorVerdicts(dir, seat, pr) {
  if (!fs.existsSync(dir)) return [];
  const same = (text) => {
    if (pr) return (text.match(/^pr:\s*"?#?(\d+)"?$/m) || [])[1] === pr;
    if (!seat) return true;
    const m = text.match(/^reviewer_seat:\s*"?([^"\n]+)"?/m);
    return m ? m[1] === seat : true; // a verdict with no seat counts: an old format is still a round
  };
  return fs.readdirSync(dir).filter(n => {
    const text = fs.readFileSync(path.join(dir, n), "utf8");
    return n.endsWith(".md") && same(text) && isVerdict(text);
  });
}

function parseFinding(s) {
  const [id, axis, tag, status, ...rest] = s.split("|");
  if (!id || !AXES.includes(axis) || !TAGS.includes(tag) || !STATUSES.includes(status))
    throw new Fail(`--finding '${s}': want "ID|axis|tag|status|text" with axis ${AXES.join("/")}, tag ${TAGS.join("/")}, status ${STATUSES.join("/")}`);
  return { id, axis, tag, status, text: rest.join("|").trim() };
}

function write(o) {
  if (!o["--out"]) throw new Fail("--out <file> is required");
  const axes = {};
  for (const axis of AXES) {
    const r = o[`--${axis}`];
    if (r === undefined) continue;
    if (!RESULTS.includes(r)) throw new Fail(`--${axis} must be ${RESULTS.join(" | ")}`);
    axes[axis] = r;
  }
  for (const axis of ["spec", "standards"]) if (!axes[axis]) throw new Fail(`--${axis} is required: the axes are never blended`);
  const k = keys(o["--base"], o["--head"] || "HEAD");
  const t = tier(o["--base"], o["--head"] || "HEAD", k);
  const security = t.axes.includes("security");
  if (security && !axes.security) throw new Fail(`this change needs the security axis (${t.tier}: ${t.why}): --security is required`);
  if (!security && axes.security) throw new Fail(`--security is the Deep axis and this change is ${t.tier} (${t.why}): put a security finding on the standards axis, or add "Security axis: always" to REVIEW.md`);
  const findings = (o["--finding"] || []).map(parseFinding);
  for (const f of findings) if (!axes[f.axis]) throw new Fail(`finding ${f.id} is on the ${f.axis} axis, which has no result`);
  for (const [axis, r] of Object.entries(axes))
    if (r === "pass" && findings.some(f => f.axis === axis && f.tag === "Important" && f.status === "open"))
      throw new Fail(`${axis} cannot pass with an open Important finding on it`);
  const q = JSON.stringify;
  const lines = ["---", `axes: {${Object.entries(axes).map(([a, r]) => `${a}: ${r}`).join(", ")}}`, `tier: ${t.tier}`,
    `base: ${k.base}`, `head: ${k.head}`, `patch_id: ${k.patch_id}`, `diff_digest: ${q(k.diff_digest)}`,
    `reviewed_at: ${new Date().toISOString().replace(/\.\d+Z$/, "Z")}`];
  if (o["--round"]) lines.push(`round: ${Number(o["--round"])}`);
  if (o["--pr"]) lines.push(`pr: ${prNumber(o["--pr"])}`);
  if (o["--seat"]) lines.push(`reviewer_seat: ${q(o["--seat"])}`);
  if (o["--family"]) lines.push(`reviewer_family: ${q(o["--family"])}`);
  lines.push(findings.length ? "findings:" : "findings: []");
  for (const f of findings) lines.push(`  - {id: ${q(f.id)}, axis: ${f.axis}, tag: ${f.tag}, status: ${f.status}, text: ${q(f.text)}}`);
  lines.push("---", "", `# Review verdict (${t.tier}): ${Object.entries(axes).map(([a, r]) => `${a} ${r}`).join(", ")}`, "");
  for (const f of findings) lines.push(`- ${f.id} [${f.axis}, ${f.tag}, ${f.status}] ${f.text}`);
  fs.mkdirSync(path.dirname(path.resolve(o["--out"])), { recursive: true });
  fs.writeFileSync(o["--out"], lines.join("\n") + "\n");
  const overall = Object.values(axes).includes("fail") ? "BLOCKING" : Object.values(axes).includes("inconclusive") ? "NOT-CLEAR" : "PASS";
  return { file: path.resolve(o["--out"]), verdict: overall, ...k, tier: t.tier };
}

function check(file, base, head) {
  const block = blocks(fs.readFileSync(file, "utf8")).find(b => /^axes:\s*\{/m.test(b));
  if (!block) throw new Fail(`${file} has no verdict block (a leading --- block with axes)`);
  const field = n => (block.match(new RegExp(`^${n}: "?([^"\\n]+)"?$`, "m")) || [])[1];
  const k = keys(base, head);
  const stale = ["patch_id", "diff_digest"].filter(n => field(n) !== k[n]);
  return { file, bound: stale.length === 0, stale, ...k };
}

function parse(argv) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith("--")) { o._.push(a); continue; }
    const v = argv[i + 1];
    if (v === undefined || v.startsWith("--")) throw new Fail(`${a} needs a value`);
    if (a === "--finding") (o[a] = o[a] || []).push(v); else o[a] = v;
    i++;
  }
  return o;
}

function main(argv) {
  const [cmd, ...rest] = argv;
  const o = parse(rest);
  const need = () => { if (!o["--base"]) throw new Fail("--base <ref> is required (the PR's base branch)"); };
  switch (cmd) {
    case "tier": need(); return tier(o["--base"], o["--head"] || "HEAD");
    case "round": {
      const dir = o._[0] || "proof";
      const pr = o["--pr"] && prNumber(o["--pr"]);
      const n = priorVerdicts(dir, o["--seat"], pr).length + 1;
      if (n > 3) { process.stdout.write(JSON.stringify({ round: n, stop: "round cap: hand the approach back to the lead, do not review again" }) + "\n"); process.exit(3); }
      // rig proof add takes rev1-r1 and rev1-r2 only: every later round is rev1-r2, and the name keeps rounds apart in proof/.
      const slice = path.basename(path.dirname(path.resolve(dir)));
      return { round: n, artifact_type: n === 1 ? "rev1-r1" : "rev1-r2", proof_name: `${slice}${pr ? `-pr${pr}` : ""}-rev1-round${n}.md` };
    }
    case "write": need(); return write(o);
    case "check": { need(); if (!o._[0]) throw new Fail("check <verdict file>"); const r = check(o._[0], o["--base"], o["--head"] || "HEAD"); if (!r.bound) { process.stdout.write(JSON.stringify(r) + "\n"); process.exit(1); } return r; }
    default: throw new Fail("usage: verdict.cjs tier|round|write|check (see the header of this file)");
  }
}

try {
  process.stdout.write(JSON.stringify(main(process.argv.slice(2))) + "\n");
} catch (e) {
  if (!(e instanceof Fail)) throw e;
  process.stderr.write(`verdict: ${e.message}\n`);
  process.exit(2);
}
