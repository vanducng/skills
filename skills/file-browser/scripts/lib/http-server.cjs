/**
 * HTTP server for file-browser.
 *
 * Routes:
 * - /                  Welcome page
 * - /view?file=<path>  Single media viewer (with prev/next)
 * - /browse?dir=<path> Folder gallery
 * - /file/*            Raw file streaming (Range-aware - critical for video seeking)
 * - /assets/*          Static assets (CSS)
 *
 * Security: paths must resolve under one of the allowedDirs (path-traversal guard).
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const { renderSingleView, renderGallery } = require('./media-renderer.cjs');
const { renderMarkdownPage, isMarkdown } = require('./markdown-page.cjs');

let allowedBaseDirs = [];

function setAllowedDirs(dirs) {
  allowedBaseDirs = dirs.map((d) => path.resolve(d));
}

function isPathSafe(filePath, allowedDirs = allowedBaseDirs) {
  if (typeof filePath !== 'string' || filePath.includes('\0')) return false;
  const resolved = path.resolve(filePath);
  if (allowedDirs.length === 0) return true;
  return allowedDirs.some((dir) => resolved === dir || resolved.startsWith(dir + path.sep));
}

function sanitizeErrorMessage(message) {
  return String(message).replace(/\/[^\s'"<>]+/g, '[path]');
}

// MIME type table - browsers know how to render all of these natively
const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
  // Images
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
  '.avif': 'image/avif',
  '.svg': 'image/svg+xml',
  '.bmp': 'image/bmp',
  '.ico': 'image/x-icon',
  '.heic': 'image/heic',
  '.heif': 'image/heif',
  '.jxl': 'image/jxl',
  '.apng': 'image/apng',
  // Video
  '.mp4': 'video/mp4',
  '.m4v': 'video/mp4',
  '.webm': 'video/webm',
  '.mov': 'video/quicktime',
  '.mkv': 'video/x-matroska',
  '.ogv': 'video/ogg',
  // Audio
  '.mp3': 'audio/mpeg',
  '.m4a': 'audio/mp4',
  '.aac': 'audio/aac',
  '.ogg': 'audio/ogg',
  '.opus': 'audio/ogg',
  '.wav': 'audio/wav',
  '.flac': 'audio/flac'
};

function getMimeType(filePath) {
  return MIME_TYPES[path.extname(filePath).toLowerCase()] || 'application/octet-stream';
}

function sendHtml(res, statusCode, html) {
  res.writeHead(statusCode, { 'Content-Type': 'text/html; charset=utf-8' });
  res.end(html);
}

function sendError(res, statusCode, message) {
  const safe = sanitizeErrorMessage(message);
  sendHtml(res, statusCode, `<!doctype html><meta charset="utf-8">
    <title>Error ${statusCode}</title>
    <body style="font-family:system-ui;padding:2rem;background:#1a1a1a;color:#eee">
    <h1>Error ${statusCode}</h1><p>${safe}</p></body>`);
}

/**
 * Stream a file with HTTP Range support. Required for MP4/MKV seeking — without
 * this, browsers buffer the whole file before allowing the user to scrub, and
 * Safari refuses to play <video> at all unless Range is honored.
 */
function streamFile(req, res, filePath, skipValidation = false) {
  if (!skipValidation && !isPathSafe(filePath)) {
    sendError(res, 403, 'Access denied');
    return;
  }

  let stats;
  try {
    stats = fs.statSync(filePath);
  } catch {
    sendError(res, 404, 'File not found');
    return;
  }
  if (!stats.isFile()) {
    sendError(res, 404, 'Not a file');
    return;
  }

  const total = stats.size;
  const mime = getMimeType(filePath);
  const range = req.headers.range;

  if (range) {
    // bytes=START-END (END optional)
    const match = /^bytes=(\d+)-(\d*)$/.exec(range);
    if (!match) {
      res.writeHead(416, {
        'Content-Range': `bytes */${total}`,
        'Content-Type': 'text/plain'
      });
      res.end('Invalid Range');
      return;
    }
    const start = parseInt(match[1], 10);
    const end = match[2] ? parseInt(match[2], 10) : total - 1;

    if (start >= total || end >= total || start > end) {
      res.writeHead(416, {
        'Content-Range': `bytes */${total}`,
        'Content-Type': 'text/plain'
      });
      res.end('Range Not Satisfiable');
      return;
    }

    res.writeHead(206, {
      'Content-Range': `bytes ${start}-${end}/${total}`,
      'Accept-Ranges': 'bytes',
      'Content-Length': end - start + 1,
      'Content-Type': mime,
      'Cache-Control': 'no-cache'
    });
    fs.createReadStream(filePath, { start, end }).pipe(res);
    return;
  }

  res.writeHead(200, {
    'Content-Length': total,
    'Content-Type': mime,
    'Accept-Ranges': 'bytes',
    'Cache-Control': 'no-cache'
  });
  fs.createReadStream(filePath).pipe(res);
}

function createHttpServer(options) {
  const { assetsDir, allowedDirs = [] } = options;
  if (allowedDirs.length > 0) setAllowedDirs(allowedDirs);

  const cssHref = '/assets/styles.css';

  const server = http.createServer((req, res) => {
    let parsedUrl;
    try {
      parsedUrl = url.parse(req.url, true);
    } catch {
      sendError(res, 400, 'Bad request');
      return;
    }
    const pathname = decodeURIComponent(parsedUrl.pathname || '/');

    // Static assets
    if (pathname.startsWith('/assets/')) {
      const rel = pathname.slice('/assets/'.length);
      if (rel.includes('..')) return sendError(res, 403, 'Access denied');
      const assetPath = path.join(assetsDir, rel);
      streamFile(req, res, assetPath, true);
      return;
    }

    // Raw file streaming (preserves leading slash from absolute path)
    if (pathname.startsWith('/file/')) {
      const filePath = pathname.slice('/file'.length); // keeps leading '/'
      if (!isPathSafe(filePath)) return sendError(res, 403, 'Access denied');
      streamFile(req, res, filePath);
      return;
    }

    // Unified file viewer — dispatches by extension
    if (pathname === '/view') {
      const filePath = parsedUrl.query?.file;
      if (!filePath) return sendError(res, 400, 'Missing ?file= parameter');
      if (!isPathSafe(filePath)) return sendError(res, 403, 'Access denied');
      if (!fs.existsSync(filePath)) return sendError(res, 404, 'File not found');
      try {
        if (isMarkdown(filePath)) {
          // Markdown → novel-theme reader (Mermaid, plan nav, ToC)
          sendHtml(res, 200, renderMarkdownPage(filePath, assetsDir));
        } else {
          // Image / video / audio → media single-view
          sendHtml(res, 200, renderSingleView(filePath, cssHref));
        }
      } catch (err) {
        console.error('[file-browser] view error:', err.message);
        sendError(res, 500, 'Render error');
      }
      return;
    }

    // Folder gallery
    if (pathname === '/browse') {
      const dirPath = parsedUrl.query?.dir;
      if (!dirPath) return sendError(res, 400, 'Missing ?dir= parameter');
      if (!isPathSafe(dirPath)) return sendError(res, 403, 'Access denied');
      let stats;
      try {
        stats = fs.statSync(dirPath);
      } catch {
        return sendError(res, 404, 'Directory not found');
      }
      if (!stats.isDirectory()) return sendError(res, 404, 'Not a directory');
      try {
        sendHtml(res, 200, renderGallery(dirPath, cssHref));
      } catch (err) {
        console.error('[file-browser] browse error:', err.message);
        sendError(res, 500, 'Render error');
      }
      return;
    }

    // Welcome
    if (pathname === '/') {
      sendHtml(res, 200, `<!doctype html><html><head><meta charset="utf-8">
        <title>file-browser</title>
        <link rel="stylesheet" href="${cssHref}" />
        </head><body class="gallery"><main class="page">
        <h1>file-browser</h1>
        <p>Local HTTP server for images, video, audio.</p>
        <h2 class="section-title">Routes</h2>
        <ul>
          <li><code>/view?file=&lt;path&gt;</code> &mdash; single media viewer</li>
          <li><code>/browse?dir=&lt;path&gt;</code> &mdash; folder gallery</li>
          <li><code>/file/&lt;path&gt;</code> &mdash; raw stream (Range-aware)</li>
        </ul>
        </main></body></html>`);
      return;
    }

    sendError(res, 404, 'Not found');
  });

  return server;
}

module.exports = {
  createHttpServer,
  getMimeType,
  isPathSafe,
  setAllowedDirs,
  sanitizeErrorMessage,
  streamFile,
  MIME_TYPES
};
