#!/usr/bin/env node
// Records resolver: one command that says where a unit of work keeps its SPEC.md, PROGRESS.md, PROOF.md and reports/.
//   records.cjs resolve [--slice <NN-slug|mission/NN-slug|path>] [--id <id>] [--json|--print]
//   records.cjs init [--id <id>] [--intent "<text>"]            create the .workbench/<id>/ folder (no rig only)
//   records.cjs check <dir> [--stage close]                      the shape checks `rig scope audit` makes, for any record folder
//   records.cjs proof add <dir> --artifact-type .. --verdict .. --candidate-sha .. --money-evidence .. (--file F | --body T)
//   records.cjs migrate [--apply]                                move .workbench/features/<id>/ into .workbench/<id>/
// In a rig (OPENRIG_SESSION_NAME set and a workspace.yaml found) the folder is the slice folder and evidence goes through
// `rig proof add`. Anywhere else it is <main worktree>/.workbench/<id>/, in the same shape.
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

// The C1 header contract of `rig proof add` (daemon scope-audit.js); a test compares these with the installed daemon.
const C1_REQUIRED_FIELDS = ["slice", "candidate_sha", "artifact_type", "verdict", "money_evidence"];
const C1_ARTIFACT_TYPES = ["guard", "qa", "rev1-r1", "rev1-r2", "adjudication"];
const C1_VERDICTS = ["CLEAR", "BLOCKING", "CONCERNING", "PASS", "NOT-CLEAR"];
const RETRO = /^\s*[-*]\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z)\b[^\n]*?\bretro:[ \t]*(\S[^\n]*)$/im;
const ID = /^[a-z0-9][a-z0-9._-]*$/;
const SLICE_PATH = /[\\/]missions[\\/][^\\/]+[\\/](slices|closed)[\\/][^\\/]+$/;
const VIDEO_EXT = new Set([".mp4", ".mov", ".webm", ".m4v", ".avi", ".mkv"]);
const BINARY_EXT = new Set([".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".pdf", ".mp3", ".wav", ".ogg", ".mp4", ".mov", ".webm", ".m4v", ".avi", ".mkv", ".zip", ".gz", ".7z", ".exe"]);

class Fail extends Error { constructor(msg, code = 2) { super(msg); this.code = code; } }

// ---- arguments ----------------------------------------------------------------------------------------------------

const VALUE_FLAGS = new Set(["--slice", "--id", "--intent", "--root", "--stage", "--artifact-type", "--verdict", "--candidate-sha", "--money-evidence",
  "--file", "--body", "--name", "--evidences", "--self-check", "--media", "--slice-id"]);
const BOOL_FLAGS = new Set(["--json", "--print", "--apply", "--replace"]);
function parse(argv) {
  const pos = [], opts = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (VALUE_FLAGS.has(a)) {
      const v = argv[++i];
      if (v === undefined || (v.startsWith("--") && VALUE_FLAGS.has(v))) throw new Fail(`${a} needs a value`);
      if (a in opts) throw new Fail(`${a} given twice`);
      opts[a] = v;
    } else if (BOOL_FLAGS.has(a)) opts[a] = true;
    else if (a.startsWith("--")) throw new Fail(`unknown option ${a}`);
    else pos.push(a);
  }
  return { pos, opts };
}

// ---- small helpers ------------------------------------------------------------------------------------------------

const exists = p => fs.existsSync(p);
const isDir = p => { try { return fs.statSync(p).isDirectory(); } catch { return false; } };
const readText = p => fs.readFileSync(p, "utf8");
const ls = p => (isDir(p) ? fs.readdirSync(p).sort() : []);
function git(cwd, ...args) {
  const r = spawnSync("git", args, { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
  return r.status === 0 ? r.stdout.trim() : null;
}
function frontmatter(file) {
  if (!exists(file)) return {};
  const m = /^---\r?\n([\s\S]*?)\r?\n---/.exec(readText(file));
  const out = {};
  for (const line of m ? m[1].split(/\r?\n/) : []) {
    const kv = /^([A-Za-z_][\w-]*):[ \t]*(.*)$/.exec(line);
    if (!kv) continue;
    const raw = kv[2].trim(), q = /^(["'])(.*)\1/.exec(raw);
    out[kv[1]] = q ? q[2] : raw.replace(/\s+#.*$/, "");
  }
  return out;
}
const quote = s => JSON.stringify(String(s));
// A header scalar: plain when it is plainly safe, JSON-quoted (valid YAML) otherwise.
const scalar = s => (/^[A-Za-z][A-Za-z0-9_./ -]*$/.test(s) && !/^(true|false|null|yes|no|on|off)$/i.test(s) ? s : quote(s));

// ---- where the workspace and the git roots are ----------------------------------------------------------------------

// --root, then $PROJECTS_ROOT, then the nearest parent of the cwd: a stale or wrong explicit root falls through.
function workspaceRoot(opts, cwd) {
  for (const given of [opts["--root"], process.env.PROJECTS_ROOT]) {
    if (!given) continue;
    const r = path.resolve(given);
    if (exists(path.join(r, "workspace.yaml"))) return r;
  }
  for (let d = cwd; ; d = path.dirname(d)) {
    if (exists(path.join(d, "workspace.yaml"))) return d;
    if (path.dirname(d) === d) return null;
  }
}
function projectRoots(ws) {
  const roots = [];
  for (const m of readText(path.join(ws, "workspace.yaml")).matchAll(/^\s+root:\s*(\S+)\s*$/gm)) roots.push(path.resolve(ws, m[1]));
  return roots;
}
// Every slice folder in the workspace: {mission, slice, dir}. Closed slices count too.
function allSlices(ws) {
  const out = [];
  for (const root of projectRoots(ws)) {
    const missions = path.join(root, "missions");
    for (const mission of ls(missions)) for (const kind of ["slices", "closed"]) for (const slice of ls(path.join(missions, mission, kind)))
      if (isDir(path.join(missions, mission, kind, slice))) out.push({ mission, slice, dir: path.join(missions, mission, kind, slice), missionDir: path.join(missions, mission), root });
  }
  return out;
}
function mainWorktree(cwd) {
  const common = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir");
  if (common && path.basename(common) === ".git") return path.dirname(common);
  const top = git(cwd, "rev-parse", "--show-toplevel");
  return top || cwd;
}

// ---- resolve --------------------------------------------------------------------------------------------------------

function findSlice(ws, opts, cwd) {
  const all = allSlices(ws);
  const pick = (matches, what) => {
    if (matches.length === 1) return matches[0];
    if (!matches.length) throw new Fail(`no slice matches ${what}`);
    throw new Fail(`${what} is ambiguous: ${matches.map(m => `${m.mission}/${m.slice}`).join(", ")}; use mission/NN-slug or a path`);
  };
  const flag = opts["--slice"];
  if (flag) {
    const asPath = path.resolve(cwd, flag);
    if (isDir(asPath)) {
      const known = all.find(s => s.dir === asPath);
      if (known) return known;
      if (SLICE_PATH.test(asPath) && exists(path.join(asPath, "SPEC.md"))) return { dir: asPath, slice: path.basename(asPath), mission: path.basename(path.dirname(path.dirname(asPath))) };
      throw new Fail(`${asPath} is not a slice folder: a path must sit under missions/<mission>/(slices|closed)/<slice>/ and hold a SPEC.md`);
    }
    if (flag.includes("/")) { const [m, s] = flag.split("/"); return pick(all.filter(x => x.mission === m && x.slice === s), flag); }
    return pick(all.filter(x => x.slice === flag), `slice '${flag}'`);
  }
  const inside = all.find(s => cwd === s.dir || cwd.startsWith(s.dir + path.sep));
  if (inside) return inside;
  const top = git(cwd, "rev-parse", "--show-toplevel") || cwd;
  const named = /^(.+)-([a-z0-9]+)-s(\d{2})$/.exec(path.basename(top));
  if (named) {
    const [, , code, nn] = named;
    const matches = all.filter(s => s.slice.startsWith(`${nn}-`) && frontmatter(path.join(s.missionDir, "SPEC.md")).code === code);
    if (matches.length) return pick(matches, `worktree '${path.basename(top)}'`);
    throw new Fail(`worktree '${path.basename(top)}' matches no slice (no mission with code '${code}' and a slice ${nn}-*); pass --slice`);
  }
  throw new Fail(`in a rig (OPENRIG_SESSION_NAME=${process.env.OPENRIG_SESSION_NAME}) but no slice found: pass --slice <NN-slug|mission/NN-slug|path>`);
}
function benchId(opts, cwd) {
  let id = opts["--id"];
  if (!id) {
    const branch = git(cwd, "rev-parse", "--abbrev-ref", "HEAD");
    if (!branch || ["main", "master", "dev", "develop", "HEAD"].includes(branch)) throw new Fail("no branch to name this record after: pass --id <id>");
    id = branch.replace(/^[a-z]+\//i, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  }
  if (!ID.test(id)) throw new Fail(`invalid id '${id}': lowercase letters, digits, '.', '_' and '-', starting with a letter or digit`);
  return id;
}
function shape(dir, mode, extra) {
  return { mode, dir, spec: path.join(dir, "SPEC.md"), progress: path.join(dir, "PROGRESS.md"), proofFile: path.join(dir, "PROOF.md"), proofDir: path.join(dir, "proof"), reports: path.join(dir, "reports"), ...extra };
}
function resolve(opts, cwd) {
  const inRig = !!process.env.OPENRIG_SESSION_NAME;
  const ws = inRig ? workspaceRoot(opts, cwd) : null;
  if (inRig && !ws) throw new Fail(`in a rig (OPENRIG_SESSION_NAME=${process.env.OPENRIG_SESSION_NAME}) but no workspace.yaml found from --root, $PROJECTS_ROOT or the current directory; a rig does not write a .workbench record`);
  if (ws) {
    const s = findSlice(ws, opts, cwd);
    return shape(s.dir, "rig", { workspace: ws, mission: s.mission, slice: s.slice, proofAdd: `rig proof --workspace ${ws} add ${s.dir}` });
  }
  const id = benchId(opts, cwd), root = mainWorktree(cwd), dir = path.join(root, ".workbench", id);
  return shape(dir, "bench", { id, proofAdd: `node ${__filename} proof add ${dir}` });
}

// ---- init and check ---------------------------------------------------------------------------------------------------

const SPEC_TEMPLATE = (id, intent) => `---\nid: ${id}\nintent: ${quote(intent || "TODO: what this delivers, in one sentence")}\n---\n\n# ${id}\n\n## Mini-requirements\n\n1. TODO: one observable outcome.\n\n## Proof contract\n\n- [ ] TODO: one promised deliverable, written as an observable outcome.\n`;
const PROGRESS_TEMPLATE = id => `# Progress - ${id}\n\n## Current state\n\nTODO: where this stands and the next action.\n\n## Outcomes\n\nAt close, one line: \`- <UTC time>: retro: <what escaped or cost a round, or none>\`.\n`;
const PROOF_TEMPLATE = id => `# Proof - ${id}\n\nEvidence is added with \`records.cjs proof add\`; captures stay under ~/.share/openrig and are cited by sha256.\n\n## Artifacts\n`;
function init(opts, cwd) {
  const r = resolve(opts, cwd);
  if (r.mode === "rig") throw new Fail("in a rig the slice folder comes from `rig scope slice create`; records.cjs init is for work outside a rig");
  fs.mkdirSync(r.reports, { recursive: true });
  const made = [];
  for (const [file, body] of [[r.spec, SPEC_TEMPLATE(r.id, opts["--intent"])], [r.progress, PROGRESS_TEMPLATE(r.id)], [r.proofFile, PROOF_TEMPLATE(r.id)]])
    if (!exists(file)) { fs.writeFileSync(file, body); made.push(path.basename(file)); }
  return { ...r, created: made };
}
function sections(spec) {
  const body = spec.replace(/^---[\s\S]*?\n---/, "");
  const part = name => { const m = new RegExp(`^## ${name}\\s*$([\\s\\S]*?)(?=^## |(?![\\s\\S]))`, "m").exec(body); return m ? m[1] : null; };
  return { mini: part("Mini-requirements"), contract: part("Proof contract") };
}
const authored = line => !/^\s*(?:\d+\.|- \[[ x]\])\s*(TODO\b|\[)/i.test(line);
function readHeader(file) {
  const m = /^---\r?\n([\s\S]*?)\r?\n---/.exec(readText(file));
  const h = {};
  if (m) for (const line of m[1].split(/\r?\n/)) { const kv = /^([a-z_]+):\s*(.*)$/.exec(line); if (kv) h[kv[1]] = kv[2].trim(); }
  return h;
}
function check(dir, stage) {
  if (!isDir(dir)) throw new Fail(`${dir} is not a directory`);
  const findings = [], add = (code, message) => findings.push({ code, message });
  const specFile = path.join(dir, "SPEC.md");
  if (!exists(specFile)) add("NO_SPEC", "SPEC.md does not exist");
  else {
    const spec = readText(specFile), intent = frontmatter(specFile).intent;
    if (!intent || !intent.trim() || /^TODO\b/i.test(intent.trim())) add("NO_INTENT", "SPEC.md has no authored `intent:` in its frontmatter");
    const { mini, contract } = sections(spec);
    const items = (mini || "").split("\n").filter(l => /^\s*\d+\.\s/.test(l) && authored(l));
    if (!items.length) add("NO_MINI_REQUIREMENTS", "`## Mini-requirements` has no authored numbered item (`1. ...`)");
    const boxes = (contract || "").split("\n").filter(l => /^\s*- \[[ x]\]\s/.test(l) && authored(l));
    if (!boxes.length) add("NO_PROOF_CONTRACT", "`## Proof contract` has no authored checkbox deliverable (`- [ ] ...`)");
  }
  for (const f of ls(path.join(dir, "proof")).filter(n => n.endsWith(".md"))) {
    const h = readHeader(path.join(dir, "proof", f)), problems = [];
    for (const k of C1_REQUIRED_FIELDS) if (!h[k]) problems.push(`missing ${k}`);
    if (h.artifact_type && !C1_ARTIFACT_TYPES.includes(h.artifact_type)) problems.push(`artifact_type '${h.artifact_type}'`);
    if (h.verdict && !C1_VERDICTS.includes(h.verdict)) problems.push(`verdict '${h.verdict}'`);
    if (problems.length) add("BAD_PROOF_HEADER", `proof/${f}: ${problems.join(", ")}`);
  }
  if (stage === "close") {
    const p = path.join(dir, "PROGRESS.md");
    if (!exists(p) || !RETRO.test(readText(p))) add("NO_RETRO", "PROGRESS.md has no retro line: `- <UTC time>: retro: <what escaped or cost a round, or none>`");
  }
  return findings;
}

const lexists = p => { try { fs.lstatSync(p); return true; } catch { return false; } };
// Writes through a staging file and a rename, so an existing symlink or hardlink at the name is replaced, never written through.
function replaceFile(target, text) {
  const staging = path.join(path.dirname(target), `.${path.basename(target)}.${process.pid}.replace-tmp`);
  const prior = fs.lstatSync(target, { throwIfNoEntry: false });
  fs.writeFileSync(staging, text, { flag: "wx", mode: prior && prior.isFile() ? prior.mode & 0o777 : 0o666 });
  try { fs.renameSync(staging, target); } catch (e) { fs.rmSync(staging, { force: true }); throw e; }
}

// ---- proof add (no rig) --------------------------------------------------------------------------------------------------

function proofAdd(dir, opts) {
  if (!isDir(dir)) throw new Fail(`${dir} is not a directory`);
  if (exists(path.join(dir, "slice.yaml")) || /[\\/]missions[\\/][^\\/]+[\\/](slices|closed)[\\/]/.test(dir))
    throw new Fail(`${dir} is a rig slice folder: use \`rig proof add\` (records.cjs resolve prints the exact command)`);
  const need = { "--artifact-type": "artifact type", "--verdict": "verdict", "--candidate-sha": "candidate sha", "--money-evidence": "money evidence" };
  for (const [flag, what] of Object.entries(need)) if (!opts[flag]) throw new Fail(`${flag} is required (${what})`);
  if (!C1_ARTIFACT_TYPES.includes(opts["--artifact-type"])) throw new Fail(`--artifact-type must be one of: ${C1_ARTIFACT_TYPES.join(" | ")}`);
  if (!C1_VERDICTS.includes(opts["--verdict"])) throw new Fail(`--verdict must be one of: ${C1_VERDICTS.join(" | ")}`);
  if (opts["--file"] && opts["--body"] !== undefined) throw new Fail("--file and --body are mutually exclusive");
  if (!opts["--file"] && opts["--body"] === undefined) throw new Fail("give the artifact body with --file or --body");
  let body = opts["--body"];
  if (opts["--file"]) {
    const raw = fs.readFileSync(path.resolve(opts["--file"]));
    if (BINARY_EXT.has(path.extname(opts["--file"]).toLowerCase()) || raw.includes(0)) throw new Fail(`--file ${opts["--file"]} is binary: an artifact body is text; put captures under proof/ and pass them with --media`);
    body = raw.toString("utf8");
  }
  const slice = opts["--slice-id"] || frontmatter(path.join(dir, "SPEC.md")).id;
  if (!slice) throw new Fail("no slice id: SPEC.md has no `id:`; pass --slice-id");
  const name = opts["--name"] || (opts["--file"] ? path.basename(opts["--file"]).replace(/\.[^.]*$/, "") + ".md" : `${opts["--artifact-type"]}-${opts["--verdict"]}-${new Date().toISOString().replace(/[-:]|\.\d+/g, "")}.md`);
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]*\.md$/.test(name)) throw new Fail(`invalid --name '${name}'`);
  const target = path.join(dir, "proof", name);
  if (lexists(target) && !opts["--replace"]) throw new Fail(`${target} exists; pass --replace to overwrite it`);
  // Media refs are relative to proof/ and must stay inside the record folder, as in the rig writer.
  const mediaLines = [];
  for (const ref of (opts["--media"] || "").split(",").map(x => x.trim()).filter(Boolean)) {
    if (path.isAbsolute(ref)) throw new Fail(`--media ref '${ref}' is absolute: copy the file under proof/ and pass its relative name`);
    const resolved = path.resolve(dir, "proof", ref);
    if (!resolved.startsWith(path.resolve(dir) + path.sep)) throw new Fail(`--media ref '${ref}' resolves outside the record folder`);
    if (!exists(resolved)) process.stderr.write(`warning: --media ref '${ref}' does not exist yet (${resolved})\n`);
    mediaLines.push(VIDEO_EXT.has(path.extname(ref).toLowerCase()) ? `<video src="${ref}"></video>` : `![${ref}](${ref})`);
  }
  if (mediaLines.length) body = `${body.replace(/\s*$/, "")}\n\n## Media\n\n${mediaLines.join("\n")}\n`;
  const lines = ["---", `slice: ${scalar(slice)}`, `candidate_sha: ${scalar(opts["--candidate-sha"])}`, `artifact_type: ${opts["--artifact-type"]}`, `verdict: ${opts["--verdict"]}`, `money_evidence: ${scalar(opts["--money-evidence"])}`];
  if (opts["--evidences"]) { lines.push("evidences:"); for (const e of opts["--evidences"].split(",").map(s => s.trim()).filter(Boolean)) lines.push(`  - ${quote(e)}`); }
  if (opts["--self-check"]) lines.push(`self_check: ${scalar(opts["--self-check"])}`);
  lines.push("---", "");
  fs.mkdirSync(path.dirname(target), { recursive: true });
  replaceFile(target, lines.join("\n") + body.replace(/\s*$/, "\n"));
  const proofFile = path.join(dir, "PROOF.md"), entry = `- proof/${name}: ${opts["--artifact-type"]} ${opts["--verdict"]}, ${opts["--money-evidence"]}`.replace(/\s+/g, " ");
  let proof = exists(proofFile) ? readText(proofFile) : PROOF_TEMPLATE(slice);
  const re = new RegExp(`^- proof/${name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}:.*$`, "m");
  if (re.test(proof)) proof = proof.replace(re, entry);
  else { if (!/^## Artifacts\s*$/m.test(proof)) proof = proof.replace(/\s*$/, "\n\n## Artifacts\n"); proof = proof.replace(/\s*$/, "\n") + entry + "\n"; }
  replaceFile(proofFile, proof);
  return { file: target, header: { slice, candidate_sha: opts["--candidate-sha"], artifact_type: opts["--artifact-type"], verdict: opts["--verdict"], money_evidence: opts["--money-evidence"] } };
}

// ---- migrate ---------------------------------------------------------------------------------------------------------------

const TYPES = ["plans", "visuals", "journals", "state"];
function migrate(opts, cwd) {
  const wb = path.join(mainWorktree(cwd), ".workbench"), features = path.join(wb, "features");
  const moves = [], conflicts = [], specs = [];
  for (const id of ls(features)) {
    const from = path.join(features, id);
    if (!isDir(from) || !ID.test(id)) continue;
    const to = path.join(wb, id);
    const walk = (dir, rel) => { for (const e of fs.readdirSync(dir, { withFileTypes: true })) { const p = path.join(dir, e.name), r = path.join(rel, e.name); if (e.isDirectory()) walk(p, r); else plan(p, r); } };
    const plan = (file, rel) => {
      const parts = rel.split(path.sep);
      let dest;
      if (parts[0] === "reports") dest = path.join(to, rel);
      else if (TYPES.includes(parts[0])) dest = path.join(to, "reports", rel);
      else if (rel === "feature.json") dest = path.join(to, "reports", "feature.json");
      else dest = path.join(to, "reports", "other", rel);
      moves.push({ from: file, to: dest, label: `features/${id}/${rel.split(path.sep).join("/")} -> ${path.relative(wb, dest).split(path.sep).join("/")}` });
    };
    walk(from, "");
    const meta = path.join(from, "feature.json");
    const specFile = path.join(to, "SPEC.md");
    if (!exists(specFile)) {
      let label = id; try { label = JSON.parse(readText(meta)).label || id; } catch { /* no usable feature.json */ }
      specs.push({ file: specFile, id, intent: label });
    }
  }
  for (const m of moves) if (exists(m.to)) conflicts.push(m);
  const todo = moves.filter(m => !exists(m.to));
  if (opts["--apply"]) {
    for (const m of todo) { fs.mkdirSync(path.dirname(m.to), { recursive: true }); fs.renameSync(m.from, m.to); }
    for (const s of specs) { fs.mkdirSync(path.dirname(s.file), { recursive: true }); fs.writeFileSync(s.file, SPEC_TEMPLATE(s.id, s.intent)); }
    for (const id of ls(features)) pruneEmpty(path.join(features, id));
    if (!ls(features).length && isDir(features)) fs.rmdirSync(features);
  }
  return { moves: todo, conflicts, specs, apply: !!opts["--apply"] };
}
function pruneEmpty(dir) {
  if (!isDir(dir)) return;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) if (e.isDirectory()) pruneEmpty(path.join(dir, e.name));
  if (!fs.readdirSync(dir).length) fs.rmdirSync(dir);
}

// ---- main ----------------------------------------------------------------------------------------------------------------------

const USAGE = "usage: records.cjs resolve|init|check|proof add|migrate (see the header of this file)";
function main(argv) {
  const [cmd, ...rest] = argv;
  if (!cmd) throw new Fail(USAGE);
  const cwd = process.cwd();
  if (cmd === "resolve") {
    const { opts } = parse(rest), r = resolve(opts, cwd);
    process.stdout.write(opts["--print"] ? `${r.dir}\n` : opts["--json"] ? `${JSON.stringify(r, null, 2)}\n` : Object.entries(r).map(([k, v]) => `${k}: ${v}`).join("\n") + "\n");
  } else if (cmd === "init") {
    const { opts } = parse(rest), r = init(opts, cwd);
    process.stdout.write(opts["--json"] ? `${JSON.stringify(r, null, 2)}\n` : `${r.dir}\n${r.created.length ? `created: ${r.created.join(", ")}` : "already complete"}\n`);
  } else if (cmd === "check") {
    const { pos, opts } = parse(rest);
    if (pos.length !== 1) throw new Fail("usage: records.cjs check <dir> [--stage close]");
    if (opts["--stage"] && opts["--stage"] !== "close") throw new Fail("--stage must be close");
    const f = check(path.resolve(cwd, pos[0]), opts["--stage"]);
    process.stdout.write(f.map(x => `FAIL ${x.code}: ${x.message}`).concat(`check: ${f.length ? `${f.length} finding(s)` : "ok"}`).join("\n") + "\n");
    return f.length ? 1 : 0;
  } else if (cmd === "proof") {
    const { pos, opts } = parse(rest.slice(1));
    if (rest[0] !== "add" || pos.length !== 1) throw new Fail("usage: records.cjs proof add <dir> --artifact-type .. --verdict .. --candidate-sha .. --money-evidence .. (--file F | --body T)");
    const r = proofAdd(path.resolve(cwd, pos[0]), opts);
    process.stdout.write(opts["--json"] ? `${JSON.stringify(r, null, 2)}\n` : `wrote ${r.file}\n`);
  } else if (cmd === "migrate") {
    const { opts } = parse(rest), r = migrate(opts, cwd);
    if (!r.moves.length && !r.conflicts.length) { process.stdout.write("nothing to migrate\n"); return 0; }
    const out = r.moves.map(m => `${r.apply ? "moved" : "would move"} ${m.label}`)
      .concat(r.specs.map(s => `${r.apply ? "wrote" : "would write"} ${s.id}/SPEC.md (intent from feature.json)`))
      .concat(r.conflicts.map(m => `CONFLICT ${m.label}: destination exists, left in place`));
    if (!r.apply) out.push("dry run: pass --apply to move these files");
    process.stdout.write(out.join("\n") + "\n");
    return r.conflicts.length ? 1 : 0;
  } else throw new Fail(`unknown command '${cmd}'. ${USAGE}`);
  return 0;
}

if (require.main === module) {
  try { process.exitCode = main(process.argv.slice(2)); } catch (e) {
    if (!(e instanceof Fail)) throw e;
    process.stderr.write(`records: ${e.message}\n`); process.exitCode = e.code;
  }
}
module.exports = { C1_REQUIRED_FIELDS, C1_ARTIFACT_TYPES, C1_VERDICTS, resolve, check, proofAdd, migrate };
