// Custom minimal PDF.js viewer.
// Wires the PDFViewer component to a small toolbar (page nav, zoom, search,
// download). pdfjs-dist does NOT ship a standalone viewer.html, so this
// page is authored by us and copied into assets/pdfjs-viewer/ alongside the
// runtime deps that the postinstall script pulls from node_modules.

import { GlobalWorkerOptions, getDocument } from './build/pdf.mjs';
import {
  EventBus,
  PDFFindController,
  PDFHistory,
  PDFLinkService,
  PDFViewer,
  DownloadManager,
  SpreadMode,
  parseQueryString,
} from './web/pdf_viewer.mjs';

GlobalWorkerOptions.workerSrc = './build/pdf.worker.mjs';

const CMAP_URL = './cmaps/';
const STANDARD_FONT_URL = './standard_fonts/';
const WASM_URL = './wasm/';

const params = parseQueryString(window.location.search.slice(1));
const fileURL = params.get('file');

const errorBanner = document.getElementById('errorBanner');
function showError(msg) {
  errorBanner.textContent = msg;
  errorBanner.hidden = false;
}

if (!fileURL) {
  showError('Missing ?file= parameter');
  throw new Error('viewer: missing file param');
}

const eventBus = new EventBus();
const linkService = new PDFLinkService({ eventBus });
const findController = new PDFFindController({ eventBus, linkService });
const downloadManager = new DownloadManager();

const container = document.getElementById('viewerContainer');
const viewerEl = document.getElementById('viewer');
// pdfjs-dist 5.7.x requires BOTH `container` AND `viewer` options on the
// PDFViewer constructor; passing only container throws "Invalid container
// and/or viewer option" before any document loads.
const viewer = new PDFViewer({
  container,
  viewer: viewerEl,
  eventBus,
  linkService,
  findController,
  downloadManager,
  enableScripting: false,   // sandbox PDF JS (defense-in-depth)
  isEvalSupported: false,   // CVE-2024-4367 guard
  l10n: undefined,          // skip locale layer; en-only chrome
});
linkService.setViewer(viewer);
const pdfHistory = new PDFHistory({ linkService, eventBus });
linkService.setHistory(pdfHistory);

// Toolbar refs
const $prev = document.getElementById('prevPage');
const $next = document.getElementById('nextPage');
const $page = document.getElementById('pageInput');
const $count = document.getElementById('pageCount');
const $zoomIn = document.getElementById('zoomIn');
const $zoomOut = document.getElementById('zoomOut');
const $zoomSelect = document.getElementById('zoomSelect');
const $find = document.getElementById('findInput');
const $findPrev = document.getElementById('findPrev');
const $findNext = document.getElementById('findNext');
const $findStatus = document.getElementById('findStatus');
const $download = document.getElementById('downloadBtn');
const $spread = document.getElementById('spreadSelect');

// Persist spread mode across loads — users who prefer two-page reading
// shouldn't have to re-pick on every PDF.
const SPREAD_KEY = 'fb-pdf-spread-mode';
function loadSpreadMode() {
  try {
    const v = parseInt(localStorage.getItem(SPREAD_KEY) || '', 10);
    if (v === SpreadMode.ODD || v === SpreadMode.EVEN) return v;
  } catch {}
  return SpreadMode.NONE;
}

function basenameFromUrl(u) {
  try {
    const decoded = decodeURIComponent(u.split('?')[0]);
    return decoded.split('/').pop() || 'document.pdf';
  } catch {
    return 'document.pdf';
  }
}

const loadingTask = getDocument({
  url: fileURL,
  cMapUrl: CMAP_URL,
  cMapPacked: true,
  standardFontDataUrl: STANDARD_FONT_URL,
  wasmUrl: WASM_URL,
  enableXfa: true,
});

loadingTask.promise.then((doc) => {
  viewer.setDocument(doc);
  linkService.setDocument(doc, null);
  pdfHistory.initialize({ fingerprint: doc.fingerprints?.[0] || '' });
  $count.textContent = String(doc.numPages);
  $page.max = doc.numPages;
  // Apply persisted spread mode after pages are wired up.
  const initialSpread = loadSpreadMode();
  $spread.value = String(initialSpread);
  if (initialSpread !== SpreadMode.NONE) viewer.spreadMode = initialSpread;
}, (err) => {
  showError(`PDF load error: ${err && err.message ? err.message : String(err)}`);
});

// Page navigation
$prev.addEventListener('click', () => { if (viewer.currentPageNumber > 1) viewer.currentPageNumber -= 1; });
$next.addEventListener('click', () => { if (viewer.currentPageNumber < viewer.pagesCount) viewer.currentPageNumber += 1; });
$page.addEventListener('change', () => {
  const n = parseInt($page.value, 10);
  if (Number.isFinite(n) && n >= 1 && n <= viewer.pagesCount) viewer.currentPageNumber = n;
  else $page.value = String(viewer.currentPageNumber);
});

eventBus.on('pagechanging', (e) => { $page.value = String(e.pageNumber); });

// Zoom
$zoomIn.addEventListener('click', () => viewer.increaseScale());
$zoomOut.addEventListener('click', () => viewer.decreaseScale());
$zoomSelect.addEventListener('change', () => {
  const v = $zoomSelect.value;
  viewer.currentScaleValue = /^[\d.]+$/.test(v) ? parseFloat(v) : v;
});
eventBus.on('scalechanging', (e) => {
  // Reflect current scale in the select if it matches a known option.
  const value = e.presetValue || (typeof e.scale === 'number' ? String(e.scale) : '');
  for (const opt of $zoomSelect.options) {
    if (opt.value === value || opt.value === e.presetValue) { $zoomSelect.value = opt.value; return; }
  }
});

// Search — pdfjs uses an internal "find" event bus message.
function dispatchFind(type) {
  const query = $find.value;
  eventBus.dispatch('find', {
    source: window,
    type,
    query,
    caseSensitive: false,
    entireWord: false,
    highlightAll: true,
    findPrevious: type === 'again' ? false : undefined,
  });
}

let findDebounce;
$find.addEventListener('input', () => {
  clearTimeout(findDebounce);
  findDebounce = setTimeout(() => dispatchFind(''), 150);
});
$find.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    eventBus.dispatch('find', {
      source: window,
      type: 'again',
      query: $find.value,
      caseSensitive: false,
      entireWord: false,
      highlightAll: true,
      findPrevious: e.shiftKey,
    });
  }
});
$findPrev.addEventListener('click', () => {
  eventBus.dispatch('find', {
    source: window,
    type: 'again',
    query: $find.value,
    caseSensitive: false,
    entireWord: false,
    highlightAll: true,
    findPrevious: true,
  });
});
$findNext.addEventListener('click', () => {
  eventBus.dispatch('find', {
    source: window,
    type: 'again',
    query: $find.value,
    caseSensitive: false,
    entireWord: false,
    highlightAll: true,
    findPrevious: false,
  });
});

eventBus.on('updatefindmatchescount', (e) => {
  if (!e || !e.matchesCount) { $findStatus.textContent = ''; return; }
  const { current, total } = e.matchesCount;
  $findStatus.textContent = total > 0 ? `${current}/${total}` : '';
});
eventBus.on('updatefindcontrolstate', (e) => {
  if (!e) return;
  if (e.state === 2 /* NOT_FOUND */) $findStatus.textContent = 'no match';
  else if (e.matchesCount && e.matchesCount.total > 0) {
    $findStatus.textContent = `${e.matchesCount.current}/${e.matchesCount.total}`;
  }
});

// Spread mode (single / two-pages odd / two-pages even)
$spread.addEventListener('change', () => {
  const mode = parseInt($spread.value, 10);
  viewer.spreadMode = mode;
  try { localStorage.setItem(SPREAD_KEY, String(mode)); } catch {}
});

// Download — fetch the bytes, hand to DownloadManager so the user gets a
// real Save dialog instead of a navigation away from the viewer.
$download.addEventListener('click', async () => {
  try {
    const filename = basenameFromUrl(fileURL);
    const resp = await fetch(fileURL);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const buf = new Uint8Array(await resp.arrayBuffer());
    downloadManager.download(buf, fileURL, filename);
  } catch (err) {
    showError(`Download failed: ${err && err.message ? err.message : String(err)}`);
  }
});

// Keyboard shortcuts inside the viewer iframe.
window.addEventListener('keydown', (e) => {
  // Avoid hijacking when typing in inputs.
  if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;
  if (e.key === 'ArrowRight' || e.key === 'PageDown') { $next.click(); e.preventDefault(); }
  else if (e.key === 'ArrowLeft' || e.key === 'PageUp') { $prev.click(); e.preventDefault(); }
  else if ((e.metaKey || e.ctrlKey) && e.key === 'f') { $find.focus(); $find.select(); e.preventDefault(); }
});
