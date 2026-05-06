#!/usr/bin/env node
// Postinstall: copy pdfjs-dist runtime deps into assets/pdfjs-viewer/.
// We author our own viewer.html (Phase 3) — pdfjs-dist does NOT ship one.
// Plain fs.cpSync; no network calls; idempotent.

const fs = require('fs');
const path = require('path');

function fail(msg) {
  console.error(`[install-pdfjs-assets] ERROR: ${msg}`);
  process.exit(1);
}

function rmrf(p) {
  if (fs.existsSync(p)) fs.rmSync(p, { recursive: true, force: true });
}

function dirSize(p) {
  let total = 0;
  if (!fs.existsSync(p)) return 0;
  for (const entry of fs.readdirSync(p, { withFileTypes: true })) {
    const full = path.join(p, entry.name);
    if (entry.isDirectory()) total += dirSize(full);
    else if (entry.isFile()) total += fs.statSync(full).size;
  }
  return total;
}

function removeMaps(p) {
  if (!fs.existsSync(p)) return;
  for (const entry of fs.readdirSync(p, { withFileTypes: true })) {
    const full = path.join(p, entry.name);
    if (entry.isDirectory()) removeMaps(full);
    else if (entry.isFile() && full.endsWith('.map')) fs.unlinkSync(full);
  }
}

let pkgPath;
try {
  pkgPath = require.resolve('pdfjs-dist/package.json');
} catch (e) {
  fail(`pdfjs-dist is not installed (require.resolve failed): ${e.message}`);
}

const srcRoot = path.dirname(pkgPath);
const dstRoot = path.join(__dirname, '..', 'assets', 'pdfjs-viewer');

const buildFiles = ['pdf.mjs', 'pdf.worker.mjs'];
const webFiles = ['pdf_viewer.mjs', 'pdf_viewer.css'];
const dirCopies = [
  ['web/images', 'web/images'],
  ['cmaps', 'cmaps'],
  ['standard_fonts', 'standard_fonts'],
  ['wasm', 'wasm'],
];

for (const f of buildFiles) {
  const src = path.join(srcRoot, 'build', f);
  if (!fs.existsSync(src)) fail(`expected source missing: ${src}`);
}
for (const f of webFiles) {
  const src = path.join(srcRoot, 'web', f);
  if (!fs.existsSync(src)) fail(`expected source missing: ${src}`);
}
for (const [s] of dirCopies) {
  const src = path.join(srcRoot, s);
  if (!fs.existsSync(src)) fail(`expected source dir missing: ${src}`);
}

// Wipe vendored subtrees so re-runs are idempotent. Authored files
// (viewer.html / viewer.js / viewer.css) live alongside, untouched.
const wipeSubdirs = ['build', 'web', 'cmaps', 'standard_fonts', 'wasm'];
for (const sub of wipeSubdirs) rmrf(path.join(dstRoot, sub));

fs.mkdirSync(path.join(dstRoot, 'build'), { recursive: true });
for (const f of buildFiles) {
  fs.copyFileSync(path.join(srcRoot, 'build', f), path.join(dstRoot, 'build', f));
}

fs.mkdirSync(path.join(dstRoot, 'web'), { recursive: true });
for (const f of webFiles) {
  fs.copyFileSync(path.join(srcRoot, 'web', f), path.join(dstRoot, 'web', f));
}

for (const [src, dst] of dirCopies) {
  fs.cpSync(path.join(srcRoot, src), path.join(dstRoot, dst), { recursive: true });
}

removeMaps(dstRoot);

const totalBytes = dirSize(dstRoot);
const totalMb = (totalBytes / 1024 / 1024).toFixed(2);
const topDirs = fs.readdirSync(dstRoot, { withFileTypes: true })
  .filter((e) => e.isDirectory())
  .map((e) => e.name)
  .sort();

console.log(`[install-pdfjs-assets] source: ${srcRoot}`);
console.log(`[install-pdfjs-assets] dest:   ${dstRoot}`);
console.log(`[install-pdfjs-assets] size:   ${totalMb} MB`);
console.log(`[install-pdfjs-assets] dirs:   ${topDirs.join(', ')}`);
console.log('[install-pdfjs-assets] PDF.js runtime deps installed');
