#!/usr/bin/env node
'use strict';
// workbench.test.cjs — integration test for the workbench lifecycle CLI.
// Requires the deployed control-plane libs (~/.claude/hooks/lib) — run `vd install hooks` first.
// Run: node skills/workbench/scripts/workbench.test.cjs

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const WB = path.join(__dirname, 'workbench.cjs');
const P = require(path.join(os.homedir(), '.claude', 'hooks', 'lib', 'paths.cjs'));
let pass = 0, fail = 0;
const ok = (n, c) => { if (c) { pass++; console.log('  ✓', n); } else { fail++; console.log('  ✗', n); } };
const git = (cwd, ...a) => execFileSync('git', a, { cwd, stdio: ['ignore', 'ignore', 'ignore'] });
const wb = (cwd, ...a) => { try { return execFileSync('node', [WB, ...a], { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }); } catch (e) { return (e.stdout || '') + (e.stderr || ''); } };

function repo(branch) {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), 'wbt-'));
  git(d, 'init', '-q'); git(d, 'checkout', '-q', '-b', branch);
  fs.writeFileSync(path.join(d, '.vd.json'), JSON.stringify({ paths: { umbrella: '.workbench', layout: 'feature-first' } }));
  return d;
}
const meta = (d, id) => { try { return JSON.parse(fs.readFileSync(path.join(d, '.workbench', 'features', id, 'feature.json'), 'utf8')); } catch { return null; } };

console.log('new — branch-derived:');
let d = repo('feat/ELT-3316-manual-upload');
wb(d, 'new');
let m = meta(d, 'elt-3316-manual-upload');
ok('creates feature from branch', !!m);
ok('feature.json ticket = ELT-3316', m && m.ticket === 'ELT-3316');
ok('stored slug matches hooks slugFromBranch (parity)', m && m.slug === P.slugFromBranch('feat/ELT-3316-manual-upload'));
ok('5 type subdirs created', ['plans', 'reports', 'visuals', 'journals', 'state'].every(t => fs.existsSync(path.join(d, '.workbench', 'features', 'elt-3316-manual-upload', t))));

console.log('new — user slug (H2: cleaned/lowercased + parity):');
d = repo('trunk');
wb(d, 'new', 'My Cool Feature');
m = meta(d, 'my-cool-feature');
ok('user slug → lowercased cleaned id', !!m);
ok('stored slug == branch-resolved slug for feat/my-cool-feature', m && m.slug === P.slugFromBranch('feat/my-cool-feature'));

console.log('new — idempotent:');
const out2 = wb(d, 'new', 'My Cool Feature');
ok('second new says exists (no dup)', /exists: features\/my-cool-feature/.test(out2));
ok('exactly one dir', fs.readdirSync(path.join(d, '.workbench', 'features')).length === 1);

console.log('parseArgs (H1: positional after boolean flag):');
d = repo('trunk');
wb(d, 'new', '--from-scratch', 'other-feature');
ok('slug not swallowed by --from-scratch', fs.existsSync(path.join(d, '.workbench', 'features', 'other-feature')));

console.log('list / archive / restore:');
d = repo('feat/ELT-1-alpha'); wb(d, 'new'); wb(d, 'new', 'beta');
ok('list --status all shows both', (() => { const o = wb(d, 'list', '--status', 'all'); return /elt-1-alpha/.test(o) && /beta/.test(o); })());
wb(d, 'archive', 'beta');
ok('archived appears under archived', /beta/.test(wb(d, 'list', '--status', 'archived')));
ok('beta moved to _archive', fs.existsSync(path.join(d, '.workbench', '_archive', 'beta')));
ok('active list excludes archived', !/beta/.test(wb(d, 'list')));
wb(d, 'restore', 'beta');
ok('restored back to features', fs.existsSync(path.join(d, '.workbench', 'features', 'beta')));

console.log('resolve / reindex / gc:');
d = repo('feat/ELT-9-gamma'); wb(d, 'new');
const r = JSON.parse(wb(d, 'resolve', '--json'));
ok('resolve --json feature', r.feature === 'elt-9-gamma');
ok('resolve reports path', r.reports.endsWith(path.join('features', 'elt-9-gamma', 'reports')));
wb(d, 'reindex');
ok('reindex writes INDEX.md', fs.existsSync(path.join(d, '.workbench', 'INDEX.md')));
fs.mkdirSync(path.join(d, '.workbench', 'tmp'), { recursive: true });
ok('gc dry-run lists tmp, does not delete', (() => { const o = wb(d, 'gc'); return /would remove/.test(o) && fs.existsSync(path.join(d, '.workbench', 'tmp')); })());
ok('gc --force deletes tmp', (() => { wb(d, 'gc', '--force'); return !fs.existsSync(path.join(d, '.workbench', 'tmp')); })());

console.log(`\n${pass + fail} tests: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
