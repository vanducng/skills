// One-level directory listing for the sidebar's lazy tree.

const fs = require('fs');
const path = require('path');

const MD_EXTS = new Set(['.md', '.markdown', '.mdx']);
const PDF_EXTS = new Set(['.pdf']);
const TABLE_EXTS = new Set(['.csv', '.tsv', '.xlsx']);
const IMAGE_EXTS = new Set([
  '.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif',
  '.svg', '.bmp', '.ico', '.heic', '.heif', '.jxl', '.apng'
]);
const VIDEO_EXTS = new Set(['.mp4', '.webm', '.mov', '.m4v', '.mkv', '.ogv']);
const AUDIO_EXTS = new Set(['.mp3', '.m4a', '.aac', '.ogg', '.opus', '.wav', '.flac']);

function classifyFile(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (MD_EXTS.has(ext)) return 'markdown';
  if (PDF_EXTS.has(ext)) return 'pdf';
  if (TABLE_EXTS.has(ext)) return 'table';
  if (IMAGE_EXTS.has(ext)) return 'image';
  if (VIDEO_EXTS.has(ext)) return 'video';
  if (AUDIO_EXTS.has(ext)) return 'audio';
  return 'other';
}

function listDir(dirPath, opts = {}) {
  const showHidden = !!opts.hidden;
  let names;
  try {
    names = fs.readdirSync(dirPath);
  } catch (err) {
    const e = new Error(`cannot read directory: ${err.code || err.message}`);
    e.code = 'EREAD';
    throw e;
  }

  const dirs = [];
  const files = [];
  for (const name of names) {
    if (!showHidden && name.startsWith('.')) continue;
    const full = path.join(dirPath, name);
    let stats;
    try {
      stats = fs.statSync(full);
    } catch {
      continue;
    }
    if (stats.isDirectory()) {
      dirs.push({ name, path: full, kind: 'dir' });
    } else if (stats.isFile()) {
      files.push({ name, path: full, kind: 'file', fileType: classifyFile(full) });
    }
  }

  const byName = (a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase());
  dirs.sort(byName);
  files.sort(byName);

  return { path: dirPath, entries: [...dirs, ...files] };
}

// Recursive substring search by basename. Walks `dir` BFS, skipping dot
// entries, common heavy directories, and symlinks (cycle guard). Returns at
// most `limit` matches, ordered by directory traversal. Capped by both result
// count and node count so a misuse on a huge tree can't lock the server.
const HEAVY_DIRS = new Set([
  'node_modules', '.git', '.svn', '.hg', 'venv', '.venv', '__pycache__',
  'dist', 'build', '.next', '.turbo', 'target', '.cache', '.idea', '.vscode'
]);

function searchTree(rootDir, query, opts = {}) {
  const limit = Math.max(1, Math.min(opts.limit || 200, 1000));
  const maxNodes = Math.max(limit * 50, 5000);
  const showHidden = !!opts.hidden;
  const lc = String(query || '').toLowerCase();
  if (lc.length < 2) return { dir: rootDir, query, results: [], visited: 0, truncated: false };

  const results = [];
  const queue = [rootDir];
  let visited = 0;
  let truncated = false;

  while (queue.length > 0) {
    const dir = queue.shift();
    if (visited >= maxNodes) { truncated = true; break; }
    let names;
    try {
      names = fs.readdirSync(dir);
    } catch {
      continue;
    }
    for (const name of names) {
      if (!showHidden && name.startsWith('.')) continue;
      visited++;
      if (visited >= maxNodes) { truncated = true; break; }
      const full = path.join(dir, name);
      let stats;
      try {
        stats = fs.lstatSync(full);
      } catch {
        continue;
      }
      if (stats.isSymbolicLink()) continue;
      const isDir = stats.isDirectory();
      if (name.toLowerCase().includes(lc)) {
        results.push({
          name,
          path: full,
          kind: isDir ? 'dir' : 'file',
          fileType: isDir ? null : classifyFile(full)
        });
        if (results.length >= limit) { truncated = true; break; }
      }
      if (isDir && !HEAVY_DIRS.has(name)) {
        queue.push(full);
      }
    }
    if (results.length >= limit) { truncated = true; break; }
  }

  return { dir: rootDir, query, results, visited, truncated };
}

module.exports = { listDir, searchTree, classifyFile, MD_EXTS, PDF_EXTS, TABLE_EXTS, IMAGE_EXTS, VIDEO_EXTS, AUDIO_EXTS };
