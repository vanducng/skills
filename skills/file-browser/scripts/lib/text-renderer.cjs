// Code/text/data/pdf/html renderer. Public surface mirrors media-renderer.cjs.

const fs = require('fs');
const path = require('path');
const hljs = require('highlight.js');
const { renderSidebar } = require('./sidebar.cjs');
const { withRoot, ROOT_PERSIST_HEAD_SCRIPT } = require('./url-helpers.cjs');

const LANG_BY_EXT = {
  '.js': 'javascript', '.mjs': 'javascript', '.cjs': 'javascript',
  '.jsx': 'javascript', '.ts': 'typescript', '.tsx': 'typescript',
  '.json': 'json', '.jsonc': 'json',
  '.py': 'python', '.rb': 'ruby', '.go': 'go', '.rs': 'rust',
  '.java': 'java', '.kt': 'kotlin', '.swift': 'swift',
  '.c': 'c', '.h': 'c', '.cpp': 'cpp', '.hpp': 'cpp', '.cc': 'cpp',
  '.cs': 'csharp', '.php': 'php', '.lua': 'lua', '.r': 'r',
  '.sh': 'bash', '.bash': 'bash', '.zsh': 'bash', '.fish': 'bash', '.ps1': 'powershell',
  '.css': 'css', '.scss': 'scss', '.sass': 'scss', '.less': 'less',
  '.html': 'xml', '.htm': 'xml', '.xml': 'xml', '.svg': 'xml',
  '.yaml': 'yaml', '.yml': 'yaml', '.toml': 'ini', '.ini': 'ini', '.conf': 'ini',
  '.sql': 'sql', '.graphql': 'graphql', '.gql': 'graphql',
  '.dockerfile': 'dockerfile', '.makefile': 'makefile',
  '.tf': 'hcl', '.hcl': 'hcl',
  '.diff': 'diff', '.patch': 'diff'
};

const PLAIN_TEXT_EXTS = new Set([
  '.txt', '.log', '.csv', '.tsv', '.env', '.gitignore', '.dockerignore',
  '.editorconfig', '.npmrc', '.nvmrc'
]);

const SPECIAL_BASENAMES = {
  'dockerfile': 'dockerfile',
  'makefile': 'makefile',
  'gemfile': 'ruby',
  'rakefile': 'ruby',
  'license': null,
  'readme': null,
  'authors': null,
  'changelog': null
};

const HTML_EXTS = new Set(['.html', '.htm']);

function classify(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === '.pdf') return 'pdf';
  if (HTML_EXTS.has(ext)) return 'html';
  const base = path.basename(filePath).toLowerCase();
  if (SPECIAL_BASENAMES.hasOwnProperty(base)) return 'code';
  if (LANG_BY_EXT[ext]) return ext === '.json' ? 'data' : 'code';
  if (PLAIN_TEXT_EXTS.has(ext)) return 'text';
  return null;
}

function isText(filePath) {
  const k = classify(filePath);
  return k === 'code' || k === 'text' || k === 'data';
}

function detectLanguage(filePath) {
  const base = path.basename(filePath).toLowerCase();
  if (SPECIAL_BASENAMES[base]) return SPECIAL_BASENAMES[base];
  return LANG_BY_EXT[path.extname(filePath).toLowerCase()] || null;
}

// NUL byte in the first 1KB ≈ binary. Catches unknown extensions a user may click.
function sniffBinary(buf) {
  const n = Math.min(buf.length, 1024);
  for (let i = 0; i < n; i++) if (buf[i] === 0) return true;
  return false;
}

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

const MAX_RENDER_BYTES = 2 * 1024 * 1024;

function readFileForRender(filePath) {
  const buf = fs.readFileSync(filePath);
  if (sniffBinary(buf)) return { binary: true };
  if (buf.length > MAX_RENDER_BYTES) {
    return { tooLarge: true, size: buf.length };
  }
  return { text: buf.toString('utf8') };
}

function highlightSafe(content, lang) {
  if (!lang) return esc(content);
  try {
    return hljs.highlight(content, { language: lang, ignoreIllegals: true }).value;
  } catch {
    return esc(content);
  }
}

function prettyJson(content) {
  try { return JSON.stringify(JSON.parse(content), null, 2); }
  catch { return content; }
}

function renderLineNumbers(highlighted) {
  // hljs spans never contain \n, so a plain split is safe.
  const lines = highlighted.split('\n');
  if (lines.length && lines[lines.length - 1] === '') lines.pop();
  let out = '';
  for (let i = 0; i < lines.length; i++) {
    out += `<span class="ln" data-n="${i + 1}"></span>${lines[i] || ' '}\n`;
  }
  return out;
}

const HEAD_BOOTSTRAP = `
<script>(function(){try{var h=document.documentElement;var t=localStorage.getItem('theme');var dark=t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme:dark)').matches);h.dataset.theme=dark?'dark':'light';h.style.colorScheme=dark?'dark':'light';h.style.background=dark?'#1a1a1a':'#faf8f3';}catch(e){}})();</script>
<style>:root{color-scheme:light dark}@view-transition{navigation:auto}</style>
`;

const TEXT_VIEW_CSS = `
body.single.text { --header-h: 40px; }
body.single.text > .topbar { height: 40px; padding: 0 0.75rem; }
body.single.text > .topbar .title { font-size: 0.85rem; }
/* .stage in styles.css uses flex centering for media. With tall code, the
 * top of the content escapes upward and becomes unreachable by scroll —
 * force block layout here so scroll origin sits at content top. */
body.single.text > main.stage {
  display: block;
  height: 100%;
  min-height: 0;
  overflow: auto;
  padding: 1.25rem 1.5rem 3rem;
}
.text-card {
  background: transparent;
  border: 0;
  max-width: 1200px;
  margin: 0;
}
.text-card pre {
  margin: 0;
  padding: 0;
  overflow-x: auto;
  font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 13px;
  line-height: 1.55;
  counter-reset: line;
}
.text-card code { display: block; padding: 0; background: transparent; }
.text-card .ln {
  display: inline-block;
  width: 3em;
  margin-right: 0.75em;
  color: var(--fg-muted, var(--text-muted, #9b9890));
  text-align: right;
  user-select: none;
}
.text-card .ln::before { content: attr(data-n); }
.text-binary, .text-toolarge {
  max-width: 600px;
  margin: 4rem auto;
  padding: 2rem;
  text-align: center;
  border: 1px dashed var(--border);
  border-radius: 8px;
  color: var(--fg-muted);
}
.text-binary a, .text-toolarge a { color: var(--accent); text-decoration: underline; }
`;

function buildPage(name, filePath, cssHref, body, opts = {}) {
  const sidebarHtml = opts.sidebar ? renderSidebar(opts.sidebar) : '';
  const treeRoot = opts.sidebar && opts.sidebar.treeRoot;
  const headPersist = opts.sidebar ? ROOT_PERSIST_HEAD_SCRIPT : '';
  const folderHref = withRoot(`/browse?dir=${encodeURIComponent(path.dirname(filePath))}`, treeRoot);
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <meta name="color-scheme" content="light dark" />
  ${headPersist}
  ${HEAD_BOOTSTRAP}
  <title>${esc(name)}</title>
  <link rel="stylesheet" href="${cssHref}" />
  <link rel="stylesheet" href="/assets/highlight-github.css" id="hljs-light" />
  <link rel="stylesheet" href="/assets/highlight-github-dark.css" id="hljs-dark" disabled />
  <link rel="stylesheet" href="/assets/sidebar.css" />
  <style>${TEXT_VIEW_CSS}</style>
</head>
<body class="single text">
  ${sidebarHtml}
  <header class="topbar">
    <a class="btn" href="${esc(folderHref)}" title="Folder (Esc)">← Folder</a>
    <h1 class="title" title="${esc(filePath)}">${esc(name)}</h1>
    <span class="spacer"></span>
    <button class="btn" id="copy-btn" type="button" title="Copy file contents">Copy</button>
    <a class="btn" href="/file${esc(filePath)}" target="_blank" title="Open raw">Raw</a>
  </header>
  <main class="stage text-stage">${body}</main>
  <script>
    (function(){
      var btn=document.getElementById('copy-btn');
      if(!btn) return;
      btn.addEventListener('click',function(){
        var code=document.querySelector('.text-card code');
        if(!code) return;
        var prev=btn.textContent;
        function flash(msg){btn.textContent=msg;setTimeout(function(){btn.textContent=prev;},1500);}
        function legacy(){
          try{var r=document.createRange();r.selectNodeContents(code);
            var s=window.getSelection();s.removeAllRanges();s.addRange(r);
            document.execCommand('copy');s.removeAllRanges();flash('Copied');}
          catch(e){flash('Copy failed');}
        }
        if(navigator.clipboard&&navigator.clipboard.writeText){
          navigator.clipboard.writeText(code.innerText).then(function(){flash('Copied');},legacy);
        }else{legacy();}
      });
      var light=document.getElementById('hljs-light');
      var dark=document.getElementById('hljs-dark');
      function syncHljs(){var d=document.documentElement.dataset.theme==='dark';if(light)light.disabled=d;if(dark)dark.disabled=!d;}
      syncHljs();
      new MutationObserver(syncHljs).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
    })();
  </script>
</body>
</html>`;
}

function renderTextView(filePath, cssHref, opts = {}) {
  const name = path.basename(filePath);
  const kind = classify(filePath);
  const r = readFileForRender(filePath);

  if (r.binary) {
    const body = `<div class="text-binary">
      <p><strong>${esc(name)}</strong> looks binary.</p>
      <p><a href="/file${esc(filePath)}" target="_blank">Open raw</a></p>
    </div>`;
    return buildPage(name, filePath, cssHref, body, opts);
  }
  if (r.tooLarge) {
    const mb = (r.size / 1024 / 1024).toFixed(1);
    const body = `<div class="text-toolarge">
      <p><strong>${esc(name)}</strong> is ${mb} MB — too large to render.</p>
      <p><a href="/file${esc(filePath)}" target="_blank">Open raw</a></p>
    </div>`;
    return buildPage(name, filePath, cssHref, body, opts);
  }

  let content = r.text;
  if (kind === 'data' && path.extname(filePath).toLowerCase() === '.json') {
    content = prettyJson(content);
  }
  const lang = detectLanguage(filePath);
  const highlighted = highlightSafe(content, lang);
  const withLines = renderLineNumbers(highlighted);
  const langClass = lang ? `language-${lang}` : 'language-plaintext';
  const body = `<div class="text-card">
    <pre><code class="${langClass} hljs">${withLines}</code></pre>
  </div>`;
  return buildPage(name, filePath, cssHref, body, opts);
}

// Sandboxed iframe so the page's scripts/styles can't reach the chrome.
// `?raw=1` (handled by the dispatcher) opens the source view instead.
function renderHtmlView(filePath, cssHref, opts = {}) {
  const name = path.basename(filePath);
  const sidebarHtml = opts.sidebar ? renderSidebar(opts.sidebar) : '';
  const treeRoot = opts.sidebar && opts.sidebar.treeRoot;
  const headPersist = opts.sidebar ? ROOT_PERSIST_HEAD_SCRIPT : '';
  const fileUrl = '/file' + filePath;
  const sourceUrl = withRoot(`/view?file=${encodeURIComponent(filePath)}&raw=1`, treeRoot);
  const folderHref = withRoot(`/browse?dir=${encodeURIComponent(path.dirname(filePath))}`, treeRoot);
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <meta name="color-scheme" content="light dark" />
  ${headPersist}
  ${HEAD_BOOTSTRAP}
  <title>${esc(name)}</title>
  <link rel="stylesheet" href="${cssHref}" />
  <link rel="stylesheet" href="/assets/sidebar.css" />
  <style>
    body.single.html-view { --header-h: 40px; }
    body.single.html-view > .topbar { height: 40px; padding: 0 0.75rem; }
    body.single.html-view > main.stage {
      display: block;
      height: 100%;
      overflow: hidden;
      padding: 0;
    }
    .html-frame { width: 100%; height: 100%; border: 0; background: #fff; }
  </style>
</head>
<body class="single html-view">
  ${sidebarHtml}
  <header class="topbar">
    <a class="btn" href="${esc(folderHref)}" title="Folder (Esc)">← Folder</a>
    <h1 class="title" title="${esc(filePath)}">${esc(name)}</h1>
    <span class="spacer"></span>
    <a class="btn" href="${esc(sourceUrl)}" title="Show HTML source">Source</a>
    <a class="btn" href="${esc(fileUrl)}" target="_blank">Open raw</a>
  </header>
  <main class="stage">
    <iframe class="html-frame" src="${esc(fileUrl)}" sandbox="allow-same-origin allow-scripts allow-popups allow-forms"></iframe>
  </main>
</body>
</html>`;
}

function renderPdfView(filePath, cssHref, opts = {}) {
  const name = path.basename(filePath);
  const sidebarHtml = opts.sidebar ? renderSidebar(opts.sidebar) : '';
  const treeRoot = opts.sidebar && opts.sidebar.treeRoot;
  const headPersist = opts.sidebar ? ROOT_PERSIST_HEAD_SCRIPT : '';
  const fileUrl = '/file' + filePath;
  const folderHref = withRoot(`/browse?dir=${encodeURIComponent(path.dirname(filePath))}`, treeRoot);
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <meta name="color-scheme" content="light dark" />
  ${headPersist}
  ${HEAD_BOOTSTRAP}
  <title>${esc(name)}</title>
  <link rel="stylesheet" href="${cssHref}" />
  <link rel="stylesheet" href="/assets/sidebar.css" />
</head>
<body class="single">
  ${sidebarHtml}
  <header class="topbar">
    <a class="btn" href="${esc(folderHref)}" title="Folder (Esc)">← Folder</a>
    <h1 class="title" title="${esc(filePath)}">${esc(name)}</h1>
    <span class="spacer"></span>
    <a class="btn" href="${esc(fileUrl)}" target="_blank">Open raw</a>
  </header>
  <main class="stage" style="overflow:hidden;padding:0">
    <embed src="${esc(fileUrl)}" type="application/pdf" style="width:100%;height:100%;border:0" />
  </main>
</body>
</html>`;
}

module.exports = {
  classify,
  isText,
  detectLanguage,
  sniffBinary,
  renderTextView,
  renderPdfView,
  renderHtmlView,
  LANG_BY_EXT,
  PLAIN_TEXT_EXTS,
  HTML_EXTS
};
