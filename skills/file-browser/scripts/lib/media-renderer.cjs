// Image/video/audio gallery + single-view renderer.

const fs = require('fs');
const path = require('path');
const { renderSidebar } = require('./sidebar.cjs');
const { withRoot, ROOT_PERSIST_HEAD_SCRIPT } = require('./url-helpers.cjs');

const IMAGE_EXTS = new Set([
  '.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif',
  '.svg', '.bmp', '.ico', '.heic', '.heif', '.jxl', '.apng'
]);
const VIDEO_EXTS = new Set([
  '.mp4', '.webm', '.mov', '.m4v', '.mkv', '.ogv'
]);
const AUDIO_EXTS = new Set([
  '.mp3', '.m4a', '.aac', '.ogg', '.opus', '.wav', '.flac'
]);

function classify(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (IMAGE_EXTS.has(ext)) return 'image';
  if (VIDEO_EXTS.has(ext)) return 'video';
  if (AUDIO_EXTS.has(ext)) return 'audio';
  return null;
}

function isMedia(filePath) {
  return classify(filePath) !== null;
}

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function listSiblings(filePath) {
  const dir = path.dirname(filePath);
  let entries;
  try {
    entries = fs.readdirSync(dir);
  } catch {
    return { siblings: [], index: -1 };
  }
  const siblings = entries
    .filter((n) => !n.startsWith('.'))
    .map((n) => path.join(dir, n))
    .filter((p) => {
      try {
        return fs.statSync(p).isFile() && isMedia(p);
      } catch {
        return false;
      }
    })
    .sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));

  const index = siblings.indexOf(filePath);
  return { siblings, index };
}

function renderSingleView(filePath, cssHref, opts = {}) {
  const kind = classify(filePath);
  if (!kind) {
    return `<!doctype html><meta charset="utf-8"><title>Unsupported</title>
      <body style="font-family:system-ui;padding:2rem">
      <h1>Unsupported file type</h1>
      <p>${esc(path.basename(filePath))}</p>
      </body>`;
  }

  const { siblings, index } = listSiblings(filePath);
  const prev = index > 0 ? siblings[index - 1] : null;
  const next = index >= 0 && index < siblings.length - 1 ? siblings[index + 1] : null;
  const parent = path.dirname(filePath);
  const fileUrl = '/file' + filePath;
  const name = path.basename(filePath);

  let media;
  if (kind === 'image') {
    media = `<img class="media" src="${esc(fileUrl)}" alt="${esc(name)}" />`;
  } else if (kind === 'video') {
    media = `<video class="media" src="${esc(fileUrl)}" controls autoplay playsinline preload="metadata"></video>`;
  } else {
    media = `
      <div class="audio-card">
        <div class="audio-icon">♪</div>
        <div class="audio-name">${esc(name)}</div>
        <audio src="${esc(fileUrl)}" controls autoplay preload="metadata"></audio>
      </div>`;
  }

  const counter =
    index >= 0
      ? `<span class="counter">${index + 1} / ${siblings.length}</span>`
      : '';

  const treeRoot = opts.sidebar && opts.sidebar.treeRoot;
  const prevHref = prev ? withRoot(`/view?file=${encodeURIComponent(prev)}`, treeRoot) : '#';
  const nextHref = next ? withRoot(`/view?file=${encodeURIComponent(next)}`, treeRoot) : '#';
  const browseHref = withRoot(`/browse?dir=${encodeURIComponent(parent)}`, treeRoot);
  const rootSuffix = treeRoot ? `&root=${encodeURIComponent(treeRoot)}` : '';

  const sidebarHtml = opts.sidebar ? renderSidebar(opts.sidebar) : '';
  const headPersist = opts.sidebar ? ROOT_PERSIST_HEAD_SCRIPT : '';

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <meta name="color-scheme" content="light dark" />
  ${headPersist}
  <script>(function(){try{var h=document.documentElement;var t=localStorage.getItem('theme');var dark=t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme:dark)').matches);h.dataset.theme=dark?'dark':'light';h.style.colorScheme=dark?'dark':'light';h.style.background=dark?'#1a1a1a':'#faf8f3';}catch(e){}})();</script>
  <title>${esc(name)}</title>
  <link rel="stylesheet" href="${cssHref}" />
  <link rel="stylesheet" href="/assets/sidebar.css" />
</head>
<body class="single">
  ${sidebarHtml}
  <header class="topbar">
    <a class="btn" href="${esc(browseHref)}" title="Folder (Esc)">← Folder</a>
    <h1 class="title" title="${esc(filePath)}">${esc(name)}</h1>
    ${counter}
    <span class="spacer"></span>
    <a class="btn ${prev ? '' : 'disabled'}" href="${esc(prevHref)}" title="Previous (←)">Prev</a>
    <a class="btn ${next ? '' : 'disabled'}" href="${esc(nextHref)}" title="Next (→)">Next</a>
  </header>
  <main class="stage">
    ${media}
  </main>
  <script>
    (function () {
      var prev = ${prev ? `'${encodeURIComponent(prev).replace(/'/g, "\\'")}'` : 'null'};
      var next = ${next ? `'${encodeURIComponent(next).replace(/'/g, "\\'")}'` : 'null'};
      var parent = '${encodeURIComponent(parent).replace(/'/g, "\\'")}';
      var rootSuffix = '${rootSuffix.replace(/'/g, "\\'")}';
      document.addEventListener('keydown', function (e) {
        if (e.target && /^(INPUT|TEXTAREA)$/.test(e.target.tagName)) return;
        if (e.key === 'ArrowLeft' && prev) location.href = '/view?file=' + prev + rootSuffix;
        else if (e.key === 'ArrowRight' && next) location.href = '/view?file=' + next + rootSuffix;
        else if (e.key === 'Escape') location.href = '/browse?dir=' + parent + rootSuffix;
      });
    })();
  </script>
</body>
</html>`;
}

/**
 * Build gallery grid HTML for a directory.
 */
function renderGallery(dirPath, cssHref, opts = {}) {
  let entries;
  try {
    entries = fs.readdirSync(dirPath);
  } catch (err) {
    return `<!doctype html><body style="font-family:system-ui;padding:2rem">
      <h1>Cannot read directory</h1><p>${esc(err.message)}</p></body>`;
  }

  // Documents lane includes markdown + PDF. (Duplicates tree-api's MD_EXTS;
  // kept inline to avoid a circular-ish refactor for one extra extension.)
  const DOC_EXTS = new Set(['.md', '.markdown', '.mdx', '.pdf']);
  const isDoc = (p) => DOC_EXTS.has(path.extname(p).toLowerCase());

  const dirs = [];
  const media = [];
  const docs = [];
  const others = [];

  for (const name of entries) {
    if (name.startsWith('.')) continue;
    const fullPath = path.join(dirPath, name);
    let stats;
    try {
      stats = fs.statSync(fullPath);
    } catch {
      continue;
    }
    if (stats.isDirectory()) {
      dirs.push({ name, path: fullPath });
    } else if (stats.isFile()) {
      if (isDoc(fullPath)) {
        docs.push({ name, path: fullPath });
      } else {
        const kind = classify(fullPath);
        if (kind) media.push({ name, path: fullPath, kind });
        else others.push({ name, path: fullPath });
      }
    }
  }

  const sortByName = (a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase());
  dirs.sort(sortByName);
  media.sort(sortByName);
  docs.sort(sortByName);
  others.sort(sortByName);

  const treeRoot = opts.sidebar && opts.sidebar.treeRoot;
  const parentDir = path.dirname(dirPath);
  const showParent = parentDir !== dirPath;

  let folderHtml = '';
  if (showParent || dirs.length > 0) {
    folderHtml += '<section class="folders"><h2 class="section-title">Folders</h2><div class="folder-grid">';
    if (showParent) {
      folderHtml += `<a class="folder" href="${esc(withRoot(`/browse?dir=${encodeURIComponent(parentDir)}`, treeRoot))}">
        <div class="folder-icon">↩</div><div class="folder-name">..</div></a>`;
    }
    for (const d of dirs) {
      folderHtml += `<a class="folder" href="${esc(withRoot(`/browse?dir=${encodeURIComponent(d.path)}`, treeRoot))}">
        <div class="folder-icon">📁</div><div class="folder-name">${esc(d.name)}</div></a>`;
    }
    folderHtml += '</div></section>';
  }

  let docsHtml = '';
  if (docs.length > 0) {
    docsHtml += '<section class="docs"><h2 class="section-title">Documents (' + docs.length + ')</h2><ul class="other-list">';
    for (const d of docs) {
      const viewUrl = withRoot(`/view?file=${encodeURIComponent(d.path)}`, treeRoot);
      const icon = d.name.toLowerCase().endsWith('.pdf') ? '📕' : '📄';
      docsHtml += `<li><a href="${esc(viewUrl)}">${icon} ${esc(d.name)}</a></li>`;
    }
    docsHtml += '</ul></section>';
  }

  let mediaHtml = '';
  if (media.length > 0) {
    // 16+ items: switch to dense tiles so the user isn't forced to scroll
    // through a near-full-screen of 220px tiles before seeing folder peers.
    const denseClass = media.length > 16 ? ' dense' : '';
    mediaHtml += '<section class="media"><h2 class="section-title">Media (' + media.length + ')</h2><div class="media-grid' + denseClass + '">';
    for (const m of media) {
      const fileUrl = '/file' + m.path;
      const viewUrl = withRoot(`/view?file=${encodeURIComponent(m.path)}`, treeRoot);
      let thumb;
      if (m.kind === 'image') {
        thumb = `<img loading="lazy" decoding="async" src="${esc(fileUrl)}" alt="${esc(m.name)}" />`;
      } else if (m.kind === 'video') {
        // muted + preload=metadata renders a poster frame without autoplay.
        thumb = `<video preload="metadata" muted playsinline src="${esc(fileUrl)}#t=0.1"></video>
          <span class="kind-badge">▶</span>`;
      } else {
        thumb = `<div class="audio-thumb">♪</div><span class="kind-badge">${esc(path.extname(m.name).slice(1))}</span>`;
      }
      mediaHtml += `<a class="tile ${m.kind}" href="${esc(viewUrl)}" title="${esc(m.name)}">
        <div class="tile-media">${thumb}</div>
        <div class="tile-name">${esc(m.name)}</div>
      </a>`;
    }
    mediaHtml += '</div></section>';
  }

  // Route through /view so the dispatcher picks the right renderer; linking
  // to /file directly would trigger a download for unrecognized MIME types.
  let otherHtml = '';
  if (others.length > 0) {
    otherHtml += '<section class="others"><h2 class="section-title">Other files</h2><ul class="other-list">';
    for (const o of others) {
      const viewUrl = withRoot(`/view?file=${encodeURIComponent(o.path)}`, treeRoot);
      otherHtml += `<li><a href="${esc(viewUrl)}">${esc(o.name)}</a></li>`;
    }
    otherHtml += '</ul></section>';
  }

  const empty =
    dirs.length === 0 && media.length === 0 && docs.length === 0 && others.length === 0
      ? '<p class="empty">Empty directory.</p>'
      : '';

  const sidebarHtml = opts.sidebar ? renderSidebar(opts.sidebar) : '';
  const headPersist = opts.sidebar ? ROOT_PERSIST_HEAD_SCRIPT : '';

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <meta name="color-scheme" content="light dark" />
  ${headPersist}
  <script>(function(){try{var h=document.documentElement;var t=localStorage.getItem('theme');var dark=t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme:dark)').matches);h.dataset.theme=dark?'dark':'light';h.style.colorScheme=dark?'dark':'light';h.style.background=dark?'#1a1a1a':'#faf8f3';}catch(e){}})();</script>
  <title>📁 ${esc(path.basename(dirPath) || dirPath)}</title>
  <link rel="stylesheet" href="${cssHref}" />
  <link rel="stylesheet" href="/assets/sidebar.css" />
</head>
<body class="gallery">
  ${sidebarHtml}
  <header class="topbar">
    <h1 class="title" title="${esc(dirPath)}">📁 ${esc(path.basename(dirPath) || dirPath)}</h1>
    <span class="path">${esc(dirPath)}</span>
  </header>
  <main class="page">
    ${folderHtml}
    ${docsHtml}
    ${mediaHtml}
    ${otherHtml}
    ${empty}
  </main>
</body>
</html>`;
}

module.exports = {
  classify,
  isMedia,
  listSiblings,
  renderSingleView,
  renderGallery,
  IMAGE_EXTS,
  VIDEO_EXTS,
  AUDIO_EXTS
};
