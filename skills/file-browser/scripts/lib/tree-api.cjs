/**
 * Lazy directory tree listing for the sidebar.
 *
 * Returns ONE level of children for a given path. Sidebar fetches more
 * via /api/tree?dir=<absolute-path> as the user expands folders.
 *
 * Classification mirrors media-renderer + markdown-page so the sidebar
 * can decorate files with the correct icon (📄 markdown, 🖼 image, ▶ video, ♪ audio, · other).
 */

const fs = require('fs');
const path = require('path');

const MD_EXTS = new Set(['.md', '.markdown', '.mdx']);
const IMAGE_EXTS = new Set([
  '.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif',
  '.svg', '.bmp', '.ico', '.heic', '.heif', '.jxl', '.apng'
]);
const VIDEO_EXTS = new Set(['.mp4', '.webm', '.mov', '.m4v', '.mkv', '.ogv']);
const AUDIO_EXTS = new Set(['.mp3', '.m4a', '.aac', '.ogg', '.opus', '.wav', '.flac']);

function classifyFile(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (MD_EXTS.has(ext)) return 'markdown';
  if (IMAGE_EXTS.has(ext)) return 'image';
  if (VIDEO_EXTS.has(ext)) return 'video';
  if (AUDIO_EXTS.has(ext)) return 'audio';
  return 'other';
}

/**
 * List one level of a directory.
 * @returns {{path:string, entries: Array<{name, path, kind, fileType?}>}}
 */
function listDir(dirPath) {
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
    if (name.startsWith('.')) continue; // hide dotfiles by default
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

module.exports = { listDir, classifyFile, MD_EXTS, IMAGE_EXTS, VIDEO_EXTS, AUDIO_EXTS };
