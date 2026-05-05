// Routes: /, /view?file=, /browse?dir=, /file/*, /assets/*, /api/tree?dir=
// Path traversal guard: resolved paths must live under an allowedDir.

const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const { renderSingleView, renderGallery, isMedia } = require('./media-renderer.cjs');
const { renderMarkdownPage, isMarkdown } = require('./markdown-page.cjs');
const { renderTextView, renderPdfView, renderHtmlView, classify: classifyText } = require('./text-renderer.cjs');
const { listDir } = require('./tree-api.cjs');

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

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
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
  '.mp4': 'video/mp4',
  '.m4v': 'video/mp4',
  '.webm': 'video/webm',
  '.mov': 'video/quicktime',
  '.mkv': 'video/x-matroska',
  '.ogv': 'video/ogg',
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
  res.writeHead(statusCode, {
    'Content-Type': 'text/html; charset=utf-8',
    // bfcache-friendly; no-store/no-cache would disqualify the page.
    'Cache-Control': 'max-age=0, must-revalidate'
  });
  res.end(html);
}

function sendError(res, statusCode, message) {
  const safe = sanitizeErrorMessage(message);
  sendHtml(res, statusCode, `<!doctype html><meta charset="utf-8">
    <title>Error ${statusCode}</title>
    <body style="font-family:system-ui;padding:2rem;background:#1a1a1a;color:#eee">
    <h1>Error ${statusCode}</h1><p>${safe}</p></body>`);
}

// HTTP Range support is required for video seeking; Safari refuses <video>
// playback entirely without it.
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

function resolveTreeRoot(query, defaultRoot) {
  const override = query && query.root;
  if (!override || typeof override !== 'string') return defaultRoot;
  if (!isPathSafe(override)) return defaultRoot;
  try {
    if (!fs.statSync(override).isDirectory()) return defaultRoot;
  } catch { return defaultRoot; }
  return override;
}

function createHttpServer(options) {
  const { assetsDir, allowedDirs = [], treeRoot = null } = options;
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

    if (pathname.startsWith('/assets/')) {
      const rel = pathname.slice('/assets/'.length);
      if (rel.includes('..')) return sendError(res, 403, 'Access denied');
      const assetPath = path.join(assetsDir, rel);
      streamFile(req, res, assetPath, true);
      return;
    }

    if (pathname.startsWith('/file/')) {
      // Slice keeps the leading '/' on the absolute path.
      const filePath = pathname.slice('/file'.length);
      if (!isPathSafe(filePath)) return sendError(res, 403, 'Access denied');
      // Top-level navigations (Accept includes text/html) get the wrapped
      // /view page so the sidebar + chrome show up. Embedded media
      // (<img>/<video>/<audio>, fetch) keep raw byte streaming.
      const accept = String(req.headers['accept'] || '');
      const dest = String(req.headers['sec-fetch-dest'] || '');
      const isTopLevelNav = accept.includes('text/html') || dest === 'document';
      if (isTopLevelNav) {
        const target = '/view?file=' + encodeURIComponent(filePath);
        res.writeHead(302, { Location: target });
        res.end();
        return;
      }
      streamFile(req, res, filePath);
      return;
    }

    if (pathname === '/view') {
      const filePath = parsedUrl.query?.file;
      if (!filePath) return sendError(res, 400, 'Missing ?file= parameter');
      if (!isPathSafe(filePath)) return sendError(res, 403, 'Access denied');
      if (!fs.existsSync(filePath)) return sendError(res, 404, 'File not found');
      try {
        const effectiveRoot = resolveTreeRoot(parsedUrl.query, treeRoot);
        const sidebarArg = effectiveRoot ? { treeRoot: effectiveRoot, activePath: filePath } : null;
        const textKind = classifyText(filePath);
        // ?raw=1 forces source view for kinds with a richer renderer (html, pdf).
        const wantRaw = parsedUrl.query?.raw === '1';
        if (isMarkdown(filePath)) {
          sendHtml(res, 200, renderMarkdownPage(filePath, assetsDir, { sidebar: sidebarArg }));
        } else if (isMedia(filePath)) {
          // Media before text: .svg is classifiable as both.
          sendHtml(res, 200, renderSingleView(filePath, cssHref, { sidebar: sidebarArg }));
        } else if (textKind === 'html' && !wantRaw) {
          sendHtml(res, 200, renderHtmlView(filePath, cssHref, { sidebar: sidebarArg }));
        } else if (textKind === 'pdf' && !wantRaw) {
          sendHtml(res, 200, renderPdfView(filePath, cssHref, { sidebar: sidebarArg }));
        } else {
          // Everything else (code/text/data, html|pdf with ?raw=1, unknown ext)
          // routes through the text view; binary sniff inside shows a fallback card.
          sendHtml(res, 200, renderTextView(filePath, cssHref, { sidebar: sidebarArg }));
        }
      } catch (err) {
        console.error('[file-browser] view error:', err.message);
        sendError(res, 500, 'Render error');
      }
      return;
    }

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
        const effectiveRoot = resolveTreeRoot(parsedUrl.query, treeRoot);
        const sidebarArg = effectiveRoot ? { treeRoot: effectiveRoot, activePath: dirPath } : null;
        sendHtml(res, 200, renderGallery(dirPath, cssHref, { sidebar: sidebarArg }));
      } catch (err) {
        console.error('[file-browser] browse error:', err.message);
        sendError(res, 500, 'Render error');
      }
      return;
    }

    if (pathname === '/api/tree') {
      const dirPath = parsedUrl.query?.dir;
      if (!dirPath) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end('{"error":"Missing ?dir= parameter"}');
        return;
      }
      if (!isPathSafe(dirPath)) {
        res.writeHead(403, { 'Content-Type': 'application/json' });
        res.end('{"error":"Access denied"}');
        return;
      }
      try {
        const data = listDir(dirPath);
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify(data));
      } catch (err) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: sanitizeErrorMessage(err.message) }));
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
