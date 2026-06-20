#!/usr/bin/env node
'use strict';
/**
 * workbench.cjs — lifecycle CLI for the feature-first .workbench umbrella.
 *
 * Reuses the deployed control-plane libs (~/.claude/hooks/lib) so the id it
 * creates is exactly the id the hooks resolve — no divergence. It owns the WRITE
 * path (create/archive/gc); hooks own the read-path resolution.
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const LIB = path.join(os.homedir(), '.claude', 'hooks', 'lib');
let loadConfig, P, state;
try {
  ({ loadConfig } = require(path.join(LIB, 'config.cjs')));
  P = require(path.join(LIB, 'paths.cjs'));
  state = require(path.join(LIB, 'state.cjs'));
} catch (e) {
  console.error(`workbench: control-plane libs not found at ${LIB}.\nRun \`vd install hooks\` first. (${e.message})`);
  process.exit(2);
}

const TYPES = ['plans', 'reports', 'visuals', 'journals', 'state'];

// ── arg parsing ─────────────────────────────────────────────────────────────
const BOOLEAN_FLAGS = new Set(['from-scratch', 'json', 'force']);
function parseArgs(argv) {
  const pos = [], flags = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const k = a.slice(2);
      if (!BOOLEAN_FLAGS.has(k) && i + 1 < argv.length && !argv[i + 1].startsWith('--')) flags[k] = argv[++i];
      else flags[k] = true;
    } else pos.push(a);
  }
  return { pos, flags };
}

// ── umbrella + feature helpers ───────────────────────────────────────────────
function ctx() {
  const cfg = loadConfig();
  const cwd = process.cwd();
  const umbrella = P.resolveUmbrellaRoot(cfg, cwd);
  if (!umbrella) {
    console.error('workbench: no .workbench umbrella for this repo. Set `paths.umbrella` in <git-root>/.vd.json.');
    process.exit(2);
  }
  return { cfg, cwd, umbrella, featuresDir: path.join(umbrella, 'features'), archiveDir: path.join(umbrella, '_archive'), globalDir: path.join(umbrella, '_global'), unsortedDir: path.join(umbrella, '_unsorted') };
}
function readMeta(dir) { try { return JSON.parse(fs.readFileSync(path.join(dir, 'feature.json'), 'utf8')); } catch { return null; } }
function writeMeta(dir, meta) {
  fs.mkdirSync(dir, { recursive: true });
  const tmp = path.join(dir, `.feature.${process.pid}.tmp`);
  fs.writeFileSync(tmp, JSON.stringify(meta, null, 2));
  fs.renameSync(tmp, path.join(dir, 'feature.json'));
}
function nowISO() { return new Date().toISOString(); }
function gitBranch(cwd) { try { return P.getGitBranch(cwd); } catch { return null; } }
function listDirs(d) { try { return fs.readdirSync(d, { withFileTypes: true }).filter(e => e.isDirectory()).map(e => e.name); } catch { return []; } }
function countFiles(dir) { let n = 0; (function walk(p) { let ents; try { ents = fs.readdirSync(p, { withFileTypes: true }); } catch { return; } for (const e of ents) { const fp = path.join(p, e.name); if (e.isDirectory()) walk(fp); else if (e.name !== 'feature.json') n++; } })(dir); return n; }
function setSession(id) {
  const sid = process.env.VD_SESSION_ID;
  if (!sid) return false;
  return state.updateSessionState(sid, { featureId: id });
}
function warnIfNoSession(ok) { if (!ok) console.error('  (VD_SESSION_ID unset — feature not set as the session default)'); }

// ── commands ─────────────────────────────────────────────────────────────────
function cmdNew({ pos, flags }) {
  const c = ctx();
  const br = gitBranch(c.cwd);
  let ticket = flags.ticket || null;
  // Normalize a user-provided slug through the same cleaner the resolver uses, so a later
  // branch resolution matches feature.json.slug. A branch-derived slug already matches.
  let slug = pos[0] ? P.cleanSlug(String(pos[0]).toLowerCase()) : null;
  if (!slug && !ticket) {
    ticket = P.extractTicketFromBranch(br, c.cfg.plan?.ticketPrefixes);
    slug = P.slugFromBranch(br, c.cfg.plan?.resolution?.branchPattern);
  }
  const id = P.computeFeatureId(ticket || null, slug || null);
  if (!id) { console.error('workbench new: need a slug or --ticket (or run on a feat/* branch).'); process.exit(1); }
  const dir = path.join(c.featuresDir, id);
  if (fs.existsSync(path.join(dir, 'feature.json'))) {
    console.log(`exists: features/${id} — switching to it`);
    warnIfNoSession(setSession(id));
    return;
  }
  for (const t of TYPES) fs.mkdirSync(path.join(dir, t), { recursive: true });
  writeMeta(dir, { id, ticket: ticket || null, slug: slug || null, label: slug || id, status: 'active', created: nowISO(), parentId: flags.parent || null, supersededBy: null, relatedDocs: [], branches: br ? [br] : [] });
  if (flags['from-scratch']) {
    const scratch = path.join(c.globalDir, 'scratch');
    let entries = [];
    try { entries = fs.readdirSync(scratch); } catch { /* no scratch dir */ }
    for (const name of entries) {
      try { fs.renameSync(path.join(scratch, name), path.join(dir, 'state', name)); }
      catch (e) { console.error(`  ! skipped scratch/${name}: ${e.code || e.message}`); }
    }
  }
  console.log(`created: features/${id}/{${TYPES.join(',')}}`);
  warnIfNoSession(setSession(id));
}

function cmdResolve({ flags }) {
  const c = ctx();
  const ff = c.cfg.paths?.layout === 'feature-first';
  // In feature-first mode, resolve may create feature.json on first strong signal.
  // In type-first mode, these feature resolvers are not called.
  const writeOpts = { readOnly: false };
  const sid = process.env.VD_SESSION_ID || null;
  const readState = sid ? state.readSessionState : null;
  const id = ff ? P.resolveFeatureId(c.cfg, c.cwd, sid, readState, writeOpts) : null;
  const root = ff
    ? (id ? path.join(c.featuresDir, id) : path.join(c.globalDir, 'scratch'))
    : c.umbrella;
  const out = {
    layout: c.cfg.paths?.layout || 'type-first',
    feature: id, featureRoot: ff ? root : null,
    reports: path.join(root, 'reports'), plans: path.join(root, 'plans'),
    visuals: path.join(root, 'visuals'), journals: path.join(root, 'journals'), state: path.join(root, 'state'),
    global: P.getGlobalPath(c.cwd, c.cfg), archive: P.getArchivePath(c.cwd, c.cfg),
  };
  if (flags.json) { console.log(JSON.stringify(out, null, 2)); return; }
  console.log(`layout:  ${out.layout}`);
  console.log(`feature: ${id || '(none — no signal; artifacts → _global/scratch)'}`);
  for (const t of TYPES) console.log(`  ${t.padEnd(9)} ${out[t]}`);
  if (!ff) console.log('note: repo is type-first — hooks use the flat layout; the above shows the would-be feature paths.');
}

function cmdSwitch({ pos }) {
  const c = ctx();
  const key = pos[0];
  if (!key) { console.error('workbench switch <id|ticket|slug>'); process.exit(1); }
  const match = listDirs(c.featuresDir).find(d => {
    if (d === key) return true;
    const m = readMeta(path.join(c.featuresDir, d));
    return m && (m.ticket === key || m.slug === key || (m.ticket || '').toLowerCase() === key.toLowerCase());
  });
  if (!match) { console.error(`workbench switch: no feature matching "${key}". Try \`workbench list\`.`); process.exit(1); }
  if (!setSession(match)) { console.error('workbench switch: VD_SESSION_ID not set; cannot set per-session feature.'); process.exit(1); }
  console.log(`switched session → features/${match}`);
}

function cmdList({ flags }) {
  const c = ctx();
  const want = flags.status || 'active';
  const rows = [];
  for (const [scope, d] of [['active', c.featuresDir], ['archived', c.archiveDir]]) {
    for (const id of listDirs(d)) {
      const m = readMeta(path.join(d, id)) || {};
      // archived scope always renders as 'archived'; active scope shows feature.json status.
      const st = scope === 'archived' ? 'archived' : (m.status || 'active');
      if (want !== 'all' && want !== st) continue;
      rows.push({ id, ticket: m.ticket || '-', status: st, artifacts: countFiles(path.join(d, id)), label: m.label || '' });
    }
  }
  if (!rows.length) { console.log(`(no ${want} features)`); return; }
  console.log(`FEATURE${' '.repeat(34)}TICKET      STATUS    FILES`);
  for (const r of rows.sort((a, b) => a.id.localeCompare(b.id))) {
    console.log(`${r.id.slice(0, 40).padEnd(40)} ${String(r.ticket).padEnd(11)} ${r.status.padEnd(9)} ${r.artifacts}`);
  }
}

function cmdStatus({ pos }) {
  const c = ctx();
  const id = pos[0] || P.resolveFeatureId(c.cfg, c.cwd);
  if (!id) { console.error('workbench status <id> (or run on a feature branch)'); process.exit(1); }
  let base = path.join(c.featuresDir, id);
  if (!fs.existsSync(base)) base = path.join(c.archiveDir, id);
  if (!fs.existsSync(base)) { console.error(`workbench status: no feature "${id}"`); process.exit(1); }
  const m = readMeta(base) || {};
  console.log(`feature: ${id}`);
  console.log(`ticket:  ${m.ticket || '-'}   status: ${m.status || '?'}   created: ${m.created || '?'}`);
  if (m.supersededBy) console.log(`superseded-by: ${m.supersededBy}`);
  if (m.parentId) console.log(`parent: ${m.parentId}`);
  for (const t of TYPES) { const n = countFiles(path.join(base, t)); if (n) console.log(`  ${t.padEnd(9)} ${n} file(s)`); }
  if (Array.isArray(m.relatedDocs) && m.relatedDocs.length) console.log(`relatedDocs: ${m.relatedDocs.join(', ')}`);
}

function cmdArchive({ pos, flags }) {
  const c = ctx();
  const id = pos[0];
  if (!id) { console.error('workbench archive <id> [--reason r] [--superseded-by id]'); process.exit(1); }
  const src = path.join(c.featuresDir, id);
  if (!fs.existsSync(src)) { console.error(`workbench archive: no active feature "${id}"`); process.exit(1); }
  const dst = path.join(c.archiveDir, id);
  if (fs.existsSync(dst)) { console.error(`workbench archive: _archive/${id} already exists`); process.exit(1); }
  fs.mkdirSync(c.archiveDir, { recursive: true });
  fs.renameSync(src, dst);
  const m = readMeta(dst) || { id };
  m.status = 'done'; m.archivedAt = nowISO();
  if (flags.reason) m.reason = flags.reason;
  if (flags['superseded-by']) m.supersededBy = flags['superseded-by'];
  writeMeta(dst, m);
  console.log(`archived: features/${id} → _archive/${id}`);
}

function cmdRestore({ pos }) {
  const c = ctx();
  const id = pos[0];
  const src = path.join(c.archiveDir, id || '');
  if (!id || !fs.existsSync(src)) { console.error(`workbench restore <id>: no _archive/${id}`); process.exit(1); }
  const dst = path.join(c.featuresDir, id);
  if (fs.existsSync(dst)) { console.error(`workbench restore: features/${id} already exists`); process.exit(1); }
  fs.renameSync(src, dst);
  const m = readMeta(dst) || { id }; m.status = 'active'; delete m.archivedAt; writeMeta(dst, m);
  console.log(`restored: _archive/${id} → features/${id}`);
}

function cmdReindex() {
  const c = ctx();
  const lines = ['# .workbench index', '', `_Regenerated by \`workbench reindex\`._`, ''];
  for (const [title, d] of [['## Active', c.featuresDir], ['## Archived', c.archiveDir]]) {
    lines.push(title, '');
    const ids = listDirs(d).sort();
    if (!ids.length) lines.push('_(none)_', '');
    for (const id of ids) { const m = readMeta(path.join(d, id)) || {}; lines.push(`- **${id}** — ${m.ticket || 'no-ticket'} · ${m.status || '?'} · ${countFiles(path.join(d, id))} files`); }
    lines.push('');
  }
  fs.writeFileSync(path.join(c.umbrella, 'INDEX.md'), lines.join('\n'));
  console.log(`wrote ${path.join(c.umbrella, 'INDEX.md')}`);
}

function cmdGc({ flags }) {
  const c = ctx();
  const force = !!flags.force;
  const targets = [];
  const tmp = path.join(c.umbrella, 'tmp');
  if (fs.existsSync(tmp)) targets.push(tmp);
  // Scope *.pid/*.log sweep to ephemeral zones only — never features/ (a feature may keep a real .log).
  (function findJunk(p) { let ents; try { ents = fs.readdirSync(p, { withFileTypes: true }); } catch { return; } for (const e of ents) { const fp = path.join(p, e.name); if (e.isDirectory()) findJunk(fp); else if (/\.(pid|log)$/.test(e.name)) targets.push(fp); } })(c.globalDir);
  if (!targets.length) { console.log('gc: nothing to sweep (no tmp/, *.pid, *.log).'); return; }
  console.log(`gc: ${force ? 'removing' : 'would remove (use --force)'}:`);
  for (const t of targets) { console.log(`  ${path.relative(c.umbrella, t)}`); if (force) { try { fs.rmSync(t, { recursive: true, force: true }); } catch (e) { console.error(`  ! ${e.message}`); } } }
}

function cmdMigrate() {
  console.log('workbench migrate: delegates to the native migrator (Phase 4).');
  console.log('  vd migrate --dry-run   # classify + report');
  console.log('  vd migrate --apply     # snapshot, move, manifest (ask-first on real data)');
  console.log('  vd migrate --revert    # replay manifest in reverse');
}

function cmdTriage() {
  const c = ctx();
  const ids = listDirs(c.unsortedDir);
  const files = (() => { try { return fs.readdirSync(c.unsortedDir).filter(n => !ids.includes(n)); } catch { return []; } })();
  if (!ids.length && !files.length) { console.log('triage: _unsorted/ is empty.'); return; }
  console.log('triage: items needing a home (assign with `workbench new` then move, or wait for `vd migrate`):');
  for (const n of [...ids, ...files].sort()) console.log(`  _unsorted/${n}`);
}

const USAGE = `workbench <command>
  new [slug] [--ticket T] [--parent id] [--from-scratch]   create/switch a feature folder
  resolve [--json]                                         show the resolved feature + type paths
  switch <id|ticket|slug>                                  set this session's active feature
  list [--status active|done|archived|all]                list features (derived from feature.json)
  status [id]                                              detail for one feature
  archive <id> [--reason r] [--superseded-by id]          move feature → _archive
  restore <id>                                             move _archive → features
  reindex                                                  rebuild INDEX.md
  gc [--force]                                             sweep tmp/, *.pid, *.log (dry-run unless --force)
  triage                                                   list _unsorted/ items
  migrate [...]                                            pointer to \`vd migrate\` (Phase 4)`;

const CMDS = { new: cmdNew, resolve: cmdResolve, switch: cmdSwitch, list: cmdList, status: cmdStatus, archive: cmdArchive, restore: cmdRestore, reindex: cmdReindex, gc: cmdGc, migrate: cmdMigrate, triage: cmdTriage };

const argv = process.argv.slice(2);
const cmd = argv[0];
if (!cmd || cmd === '-h' || cmd === '--help' || !CMDS[cmd]) {
  console.log(USAGE);
  process.exit(cmd && !CMDS[cmd] ? 1 : 0);
}
CMDS[cmd](parseArgs(argv.slice(1)));
