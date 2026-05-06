// Sidebar tree + vim keybindings. Companion to /scripts/lib/sidebar.cjs.
(function () {
  'use strict';

  const sidebar = document.querySelector('.fb-sidebar');
  if (!sidebar) return;

  const treeRoot = sidebar.dataset.treeRoot;
  const activePath = sidebar.dataset.activePath || '';

  // Persist the sidebar's tree root. The blocking <head> script (see
  // url-helpers.cjs::ROOT_PERSIST_HEAD_SCRIPT) handles URL-less loads via
  // location.replace before paint. Here we only reconcile: write the
  // server-validated treeRoot back so a stale stored value (e.g. one the
  // server rejected as outside allowedDirs) is self-correcting.
  const ROOT_KEY = 'fb-tree-root';
  try {
    if (treeRoot && localStorage.getItem(ROOT_KEY) !== treeRoot) {
      localStorage.setItem(ROOT_KEY, treeRoot);
    }
  } catch {}
  const treeEl = sidebar.querySelector('.tree');
  const filterInput = sidebar.querySelector('.fb-sidebar-filter');
  const treeNav = sidebar.querySelector('.fb-sidebar-tree');
  const toggleBtn = sidebar.querySelector('.fb-sidebar-toggle');
  const upBtn = sidebar.querySelector('.fb-sidebar-up');
  const themeBtn = sidebar.querySelector('.fb-sidebar-theme');
  const hiddenBtn = sidebar.querySelector('.fb-sidebar-hidden');
  const helpBtn = sidebar.querySelector('.fb-sidebar-help');
  const helpOverlay = sidebar.querySelector('.fb-sidebar-help-overlay');
  // Lift to <body> so the overlay's `position: fixed` anchors to the viewport
  // rather than being clipped by the sidebar's `overflow: hidden`.
  if (helpOverlay && helpOverlay.parentElement !== document.body) {
    document.body.appendChild(helpOverlay);
  }
  const fontBtns = sidebar.querySelectorAll('.fb-sidebar-font');
  const STORAGE_KEY = 'fb-sidebar-collapsed';
  const HIDDEN_KEY = 'fb-show-hidden';
  // Shared with reader.js so toggling from either surface stays in sync.
  const THEME_KEY = 'theme';
  const FONT_KEY = 'novel-viewer-font';
  // Per-tab UX state — sessionStorage so it survives nav within a tab
  // but doesn't leak across windows.
  const SS_EXPANDED = 'fb-tree-expanded';
  const SS_SCROLL = 'fb-tree-scroll';
  const SS_FILTER = 'fb-tree-filter';
  const SS_CURSOR = 'fb-tree-cursor';

  // Default to collapsed; user opens explicitly. '0' = open, anything else = collapsed.
  if (localStorage.getItem(STORAGE_KEY) !== '0') {
    document.body.classList.add('sidebar-collapsed');
  }

  function currentTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === 'light' || saved === 'dark') return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  function applyTheme(t) {
    document.documentElement.dataset.theme = t;
  }
  function toggleTheme() {
    // On markdown pages, defer to reader.js's toggle so its mermaid/hljs
    // machinery runs alongside the data-theme swap.
    const readerToggle = document.getElementById('theme-toggle');
    if (readerToggle) {
      readerToggle.click();
      return;
    }
    const next = currentTheme() === 'dark' ? 'light' : 'dark';
    localStorage.setItem(THEME_KEY, next);
    applyTheme(next);
  }
  applyTheme(currentTheme());

  window.addEventListener('storage', (e) => {
    if (e.key === THEME_KEY && (e.newValue === 'dark' || e.newValue === 'light')) {
      applyTheme(e.newValue);
    }
  });

  let showHidden = false;
  try { showHidden = localStorage.getItem(HIDDEN_KEY) === '1'; } catch {}

  function reflectHiddenUI() {
    if (hiddenBtn) hiddenBtn.setAttribute('aria-pressed', showHidden ? 'true' : 'false');
  }
  reflectHiddenUI();

  function hiddenSuffix(prefix) {
    return showHidden ? prefix + 'hidden=1' : '';
  }

  async function fetchDir(dirPath) {
    const res = await fetch('/api/tree?dir=' + encodeURIComponent(dirPath) + hiddenSuffix('&'));
    if (!res.ok) throw new Error('fetch failed: ' + res.status);
    return res.json();
  }

  function iconFor(entry) {
    if (entry.kind === 'dir') return '📁';
    switch (entry.fileType) {
      case 'markdown': return '📄';
      case 'pdf': return '📕';
      case 'image': return '🖼';
      case 'video': return '▶';
      case 'audio': return '♪';
      default: return '·';
    }
  }

  function buildLi(entry, depth) {
    const li = document.createElement('li');
    li.dataset.path = entry.path;
    li.dataset.kind = entry.kind;
    if (entry.fileType) li.dataset.fileType = entry.fileType;
    li.classList.add('node', entry.kind);
    li.dataset.depth = depth;

    const row = document.createElement('span');
    row.className = 'row';
    row.style.paddingLeft = (depth * 14) + 'px';
    row.innerHTML =
      (entry.kind === 'dir' ? '<span class="caret">▸</span>' : '<span class="caret-spacer"></span>') +
      '<span class="icon">' + iconFor(entry) + '</span>' +
      '<span class="label"></span>';
    row.querySelector('.label').textContent = entry.name;
    li.appendChild(row);

    if (entry.kind === 'dir') {
      const childUl = document.createElement('ul');
      childUl.className = 'children';
      childUl.dataset.path = entry.path;
      childUl.dataset.loaded = 'false';
      childUl.hidden = true;
      li.appendChild(childUl);
    }
    return li;
  }

  async function loadInto(ul, depth) {
    if (ul.dataset.loaded === 'true' || ul.dataset.loading === 'true') return;
    ul.dataset.loading = 'true';
    try {
      const data = await fetchDir(ul.dataset.path);
      ul.innerHTML = '';
      for (const entry of data.entries) {
        ul.appendChild(buildLi(entry, depth));
      }
      if (data.entries.length === 0) {
        const empty = document.createElement('li');
        empty.className = 'empty';
        empty.textContent = '(empty)';
        empty.style.paddingLeft = (depth * 14 + 14) + 'px';
        ul.appendChild(empty);
      }
      ul.dataset.loaded = 'true';
    } catch (err) {
      ul.innerHTML = '<li class="error">[' + (err.message || 'error') + ']</li>';
      ul.dataset.loaded = 'true';
    } finally {
      ul.dataset.loading = 'false';
    }
  }

  function loadExpandedSet() {
    try {
      const raw = sessionStorage.getItem(SS_EXPANDED);
      return new Set(raw ? JSON.parse(raw) : []);
    } catch { return new Set(); }
  }
  function saveExpandedSet(set) {
    try { sessionStorage.setItem(SS_EXPANDED, JSON.stringify(Array.from(set))); } catch {}
  }
  const expandedSet = loadExpandedSet();

  async function expand(li, opts = {}) {
    if (li.dataset.kind !== 'dir') return;
    const childUl = li.querySelector(':scope > ul.children');
    if (!childUl) return;
    li.classList.add('open');
    li.querySelector(':scope > .row > .caret').textContent = '▾';
    await loadInto(childUl, parseInt(li.dataset.depth, 10) + 1);
    childUl.hidden = false;
    if (!opts.silent) {
      expandedSet.add(li.dataset.path);
      saveExpandedSet(expandedSet);
    }
  }

  function collapse(li, opts = {}) {
    if (li.dataset.kind !== 'dir') return;
    li.classList.remove('open');
    const caret = li.querySelector(':scope > .row > .caret');
    if (caret) caret.textContent = '▸';
    const childUl = li.querySelector(':scope > ul.children');
    if (childUl) childUl.hidden = true;
    if (!opts.silent) {
      expandedSet.delete(li.dataset.path);
      saveExpandedSet(expandedSet);
    }
  }

  function toggle(li) {
    if (li.classList.contains('open')) collapse(li);
    else expand(li);
  }

  async function revealActivePath() {
    if (!activePath || !activePath.startsWith(treeRoot)) return;
    const rest = activePath.slice(treeRoot.length).replace(/^\//, '');
    if (!rest) return;
    const segments = rest.split('/').filter(Boolean);
    let currentUl = treeEl;
    let acc = treeRoot;
    for (let i = 0; i < segments.length; i++) {
      await loadInto(currentUl, i);
      acc = acc.replace(/\/$/, '') + '/' + segments[i];
      const li = currentUl.querySelector(':scope > li[data-path="' + cssEscape(acc) + '"]');
      if (!li) break;
      if (li.dataset.kind === 'dir' && i < segments.length - 1) {
        await expand(li);
        currentUl = li.querySelector(':scope > ul.children');
        if (!currentUl) break;
      } else {
        li.classList.add('active');
        setCursor(li);
        li.scrollIntoView({ block: 'nearest' });
        break;
      }
    }
  }

  function cssEscape(s) {
    if (window.CSS && CSS.escape) return CSS.escape(s);
    return s.replace(/[\s"\\#.:>~+*?$^=|!,()\[\]{}]/g, '\\$&');
  }

  let cursor = null;
  function setCursor(li) {
    if (cursor) cursor.classList.remove('cursor');
    cursor = li;
    if (li) {
      li.classList.add('cursor');
      li.scrollIntoView({ block: 'nearest' });
    }
  }

  function visibleNodes() {
    // In recursive-search mode, the cursor walks the flat results list.
    if (searchResultsEl && !searchResultsEl.hidden) {
      return Array.from(searchResultsEl.querySelectorAll('li.node'));
    }
    return Array.from(treeEl.querySelectorAll('li.node')).filter((li) => {
      let p = li.parentElement;
      while (p && p !== treeEl) {
        if (p.classList && p.classList.contains('children') && p.hidden) return false;
        p = p.parentElement;
      }
      if (li.classList.contains('filter-hidden')) return false;
      return true;
    });
  }

  function moveCursor(delta) {
    const nodes = visibleNodes();
    if (nodes.length === 0) return;
    let idx = cursor ? nodes.indexOf(cursor) : -1;
    idx = Math.max(0, Math.min(nodes.length - 1, idx + delta));
    setCursor(nodes[idx]);
  }

  function jumpTop() {
    const nodes = visibleNodes();
    if (nodes.length) setCursor(nodes[0]);
  }
  function jumpBottom() {
    const nodes = visibleNodes();
    if (nodes.length) setCursor(nodes[nodes.length - 1]);
  }

  function openCurrent(newTab) {
    if (!cursor) return;
    const rootSuffix = treeRoot ? '&root=' + encodeURIComponent(treeRoot) : '';
    if (cursor.dataset.kind === 'dir') {
      const url = '/browse?dir=' + encodeURIComponent(cursor.dataset.path) + rootSuffix;
      if (newTab) window.open(url, '_blank');
      else location.href = url;
      return;
    }
    const url = '/view?file=' + encodeURIComponent(cursor.dataset.path) + rootSuffix;
    if (newTab) window.open(url, '_blank');
    else location.href = url;
  }

  function jumpToParent() {
    if (!cursor) return;
    const parentLi = cursor.parentElement && cursor.parentElement.closest('li.node');
    if (parentLi) {
      collapse(parentLi);
      setCursor(parentLi);
    }
  }

  let filterMatches = [];
  let filterIdx = -1;
  const searchResultsEl = sidebar.querySelector('.fb-search-results');
  const searchStatusEl = sidebar.querySelector('.fb-search-status');
  let searchSeq = 0;
  let searchTimer = null;
  const SEARCH_MIN = 2;
  const SEARCH_DEBOUNCE = 250;

  function clearLocalFilter() {
    Array.from(treeEl.querySelectorAll('li.node')).forEach((li) => {
      li.classList.remove('filter-hidden', 'filter-match');
    });
  }

  function showTreeMode() {
    treeEl.hidden = false;
    searchResultsEl.hidden = true;
    searchStatusEl.hidden = true;
    searchResultsEl.innerHTML = '';
  }

  function showSearchMode(statusText) {
    treeEl.hidden = true;
    searchResultsEl.hidden = false;
    searchStatusEl.hidden = !statusText;
    if (statusText) searchStatusEl.textContent = statusText;
  }

  function applyFilter(q) {
    const lc = q.toLowerCase().trim();
    filterMatches = [];
    filterIdx = -1;

    if (!lc) {
      // Empty filter — restore tree, clear any prior local-filter classes.
      clearLocalFilter();
      showTreeMode();
      return;
    }

    if (lc.length < SEARCH_MIN) {
      // Too short for recursive search — keep tree visible with local filter only.
      showTreeMode();
      Array.from(treeEl.querySelectorAll('li.node')).forEach((li) => {
        const label = li.querySelector(':scope > .row > .label');
        const name = (label && label.textContent || '').toLowerCase();
        if (name.includes(lc)) {
          li.classList.remove('filter-hidden');
          li.classList.add('filter-match');
          filterMatches.push(li);
        } else {
          li.classList.add('filter-hidden');
          li.classList.remove('filter-match');
        }
      });
      if (filterMatches.length > 0) { filterIdx = 0; setCursor(filterMatches[0]); }
      return;
    }

    // 2+ chars — debounced recursive search via /api/search.
    showSearchMode('Searching…');
    if (searchTimer) clearTimeout(searchTimer);
    const seq = ++searchSeq;
    searchTimer = setTimeout(() => runRecursiveSearch(lc, seq), SEARCH_DEBOUNCE);
  }

  async function runRecursiveSearch(q, seq) {
    try {
      const res = await fetch('/api/search?dir=' + encodeURIComponent(treeRoot)
        + '&q=' + encodeURIComponent(q) + '&limit=200' + hiddenSuffix('&'));
      if (seq !== searchSeq) return; // stale response — newer query in flight
      if (!res.ok) {
        showSearchMode('Search failed (' + res.status + ')');
        return;
      }
      const data = await res.json();
      if (seq !== searchSeq) return;
      renderSearchResults(data);
    } catch (err) {
      if (seq !== searchSeq) return;
      showSearchMode('Search error: ' + (err.message || 'fetch failed'));
    }
  }

  function renderSearchResults(data) {
    const results = data.results || [];
    searchResultsEl.innerHTML = '';
    if (results.length === 0) {
      showSearchMode('No matches');
      return;
    }
    const rootLen = treeRoot.replace(/\/+$/, '').length;
    for (const r of results) {
      const li = document.createElement('li');
      li.className = 'node ' + r.kind + ' search-hit';
      li.dataset.path = r.path;
      li.dataset.kind = r.kind;
      if (r.fileType) li.dataset.fileType = r.fileType;
      const rel = r.path.startsWith(treeRoot) ? r.path.slice(rootLen).replace(/^\//, '') : r.path;
      const dirPart = rel.includes('/') ? rel.slice(0, rel.lastIndexOf('/') + 1) : '';
      const namePart = rel.slice(dirPart.length);
      li.innerHTML =
        '<span class="row">' +
          '<span class="icon">' + iconFor({ kind: r.kind, fileType: r.fileType }) + '</span>' +
          '<span class="label"></span>' +
          '<span class="search-relpath"></span>' +
        '</span>';
      li.querySelector('.label').textContent = namePart;
      li.querySelector('.search-relpath').textContent = dirPart || './';
      searchResultsEl.appendChild(li);
    }
    showSearchMode(data.truncated ? `${results.length}+ matches (truncated)` : `${results.length} matches`);
    filterMatches = Array.from(searchResultsEl.querySelectorAll('li.node'));
    filterIdx = 0;
    if (filterMatches[0]) setCursor(filterMatches[0]);
  }

  function nextMatch(delta) {
    if (filterMatches.length === 0) return;
    filterIdx = (filterIdx + delta + filterMatches.length) % filterMatches.length;
    setCursor(filterMatches[filterIdx]);
  }

  async function reloadCursorFolder() {
    if (!cursor) return;
    const li = cursor.dataset.kind === 'dir' ? cursor : cursor.parentElement.closest('li.dir');
    if (!li) return;
    const ul = li.querySelector(':scope > ul.children');
    if (!ul) return;
    ul.dataset.loaded = 'false';
    ul.innerHTML = '';
    await loadInto(ul, parseInt(li.dataset.depth, 10) + 1);
  }

  treeEl.addEventListener('click', (e) => {
    const li = e.target.closest('li.node');
    if (!li) return;
    setCursor(li);
    if (li.dataset.kind === 'dir') {
      e.preventDefault();
      toggle(li);
    } else {
      e.preventDefault();
      openCurrent(false);
    }
  });

  // Click in recursive-search results — opens directly (no expand on dirs).
  searchResultsEl.addEventListener('click', (e) => {
    const li = e.target.closest('li.node');
    if (!li) return;
    setCursor(li);
    e.preventDefault();
    openCurrent(false);
  });

  toggleBtn.addEventListener('click', () => {
    document.body.classList.toggle('sidebar-collapsed');
    localStorage.setItem(STORAGE_KEY, document.body.classList.contains('sidebar-collapsed') ? '1' : '0');
  });

  if (upBtn) {
    upBtn.addEventListener('click', () => {
      // Rebase to parent of current treeRoot. Server falls back to default
      // root if the parent is outside allowedDirs, which is fine.
      const parent = treeRoot.replace(/\/+$/, '').replace(/\/[^\/]+$/, '') || '/';
      if (parent === treeRoot) return;
      // Tree shape changes; clear stale per-tab state so old expansions don't bleed in.
      try { sessionStorage.removeItem(SS_EXPANDED); } catch {}
      try { sessionStorage.removeItem(SS_SCROLL); } catch {}
      try { sessionStorage.removeItem(SS_FILTER); } catch {}
      const u = new URL(location.href);
      u.searchParams.set('root', parent);
      location.href = u.toString();
    });
  }

  themeBtn.addEventListener('click', toggleTheme);

  async function refreshTree() {
    // Tree shape may change (dot entries appear/disappear) — wipe DOM, rerun
    // the same boot path so expansions/cursor/filter all rehydrate.
    treeEl.innerHTML = '';
    treeEl.dataset.loaded = 'false';
    cursor = null;
    await loadInto(treeEl, 0);
    await rehydrateExpansions();
    await revealActivePath();
    if (filterInput.value) applyFilter(filterInput.value);
    if (!cursor) {
      const nodes = visibleNodes();
      if (nodes.length > 0) setCursor(nodes[0]);
    }
  }

  function toggleHidden() {
    showHidden = !showHidden;
    try { localStorage.setItem(HIDDEN_KEY, showHidden ? '1' : '0'); } catch {}
    reflectHiddenUI();
    refreshTree();
  }
  if (hiddenBtn) hiddenBtn.addEventListener('click', toggleHidden);

  // On markdown pages, defer to reader.js's hidden .font-btn so its
  // mermaid/font machinery runs. Elsewhere, just persist + apply.
  function currentFont() {
    return localStorage.getItem(FONT_KEY) || 'M';
  }
  function reflectFontUI(size) {
    fontBtns.forEach((b) => b.classList.toggle('active', b.dataset.size === size));
  }
  function setFont(size) {
    const readerBtn = document.querySelector('.reader-header .font-btn[data-size="' + size + '"]');
    if (readerBtn) {
      readerBtn.click();
    } else {
      localStorage.setItem(FONT_KEY, size);
      document.documentElement.dataset.fontSize = size;
    }
    reflectFontUI(size);
  }
  reflectFontUI(currentFont());
  fontBtns.forEach((btn) => {
    btn.addEventListener('click', () => setFont(btn.dataset.size));
  });

  helpBtn.addEventListener('click', () => {
    helpOverlay.hidden = !helpOverlay.hidden;
  });
  helpOverlay.addEventListener('click', () => { helpOverlay.hidden = true; });

  // Global keys (\, ?, /, T) always fire. Tree-nav keys only fire when the
  // sidebar owns focus, so reader.js can keep j/k/scroll on markdown pages.
  let lastKey = '';
  let lastKeyAt = 0;
  const TREE_NAV_KEYS = new Set([
    'j', 'k', 'h', 'l', 'g', 'G', 'o', 'O', 'Enter', 'n', 'N', 'r', '-'
  ]);

  function sidebarOwnsTreeKeys() {
    if (!document.body.classList.contains('markdown')) return true;
    return sidebar.contains(document.activeElement);
  }

  // Focus the tree on click so tree-nav keys engage on markdown pages.
  sidebar.addEventListener('mousedown', (e) => {
    if (e.target.closest('.fb-sidebar-filter')) return;
    treeNav.focus();
  });

  document.addEventListener('keydown', (e) => {
    const inInput = e.target && /^(INPUT|TEXTAREA)$/.test(e.target.tagName);
    const inFilter = e.target === filterInput;

    if (inFilter) {
      if (e.key === 'Escape') {
        filterInput.value = '';
        applyFilter('');
        try { sessionStorage.removeItem(SS_FILTER); } catch {}
        filterInput.blur();
        e.preventDefault();
      } else if (e.key === 'Enter') {
        if (filterMatches.length > 0) openCurrent(false);
        e.preventDefault();
      }
      return;
    }

    if (inInput) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;

    if (!helpOverlay.hidden) {
      helpOverlay.hidden = true;
      e.preventDefault();
      return;
    }

    switch (e.key) {
      case '/':
        filterInput.focus(); filterInput.select();
        e.preventDefault(); return;
      case '\\':
        document.body.classList.toggle('sidebar-collapsed');
        localStorage.setItem(STORAGE_KEY, document.body.classList.contains('sidebar-collapsed') ? '1' : '0');
        e.preventDefault(); return;
      case '?':
        // Reader.js has its own shortcuts overlay on markdown pages.
        if (!document.body.classList.contains('markdown')) {
          helpOverlay.hidden = !helpOverlay.hidden;
          e.preventDefault();
        }
        return;
      case 'T':
        // Reader.js owns T on markdown pages.
        if (!document.getElementById('theme-toggle')) {
          toggleTheme();
          e.preventDefault();
        }
        return;
      case '.':
        toggleHidden();
        e.preventDefault();
        return;
    }

    if (TREE_NAV_KEYS.has(e.key) && !sidebarOwnsTreeKeys()) return;

    switch (e.key) {
      case 'j': moveCursor(1); e.preventDefault(); break;
      case 'k': moveCursor(-1); e.preventDefault(); break;
      case 'l':
        if (cursor && cursor.dataset.kind === 'dir') { expand(cursor); }
        e.preventDefault();
        break;
      case 'h':
        if (cursor && cursor.dataset.kind === 'dir' && cursor.classList.contains('open')) {
          collapse(cursor);
        } else {
          jumpToParent();
        }
        e.preventDefault();
        break;
      case '-':
        jumpToParent(); e.preventDefault(); break;
      case 'Enter':
      case 'o':
        openCurrent(false); e.preventDefault(); break;
      case 'O':
        openCurrent(true); e.preventDefault(); break;
      case 'G': jumpBottom(); e.preventDefault(); break;
      case 'g':
        if (lastKey === 'g' && (Date.now() - lastKeyAt) < 500) jumpTop();
        lastKey = 'g'; lastKeyAt = Date.now();
        e.preventDefault(); break;
      case 'n': nextMatch(1); e.preventDefault(); break;
      case 'N': nextMatch(-1); e.preventDefault(); break;
      case 'r': reloadCursorFolder(); e.preventDefault(); break;
      case 'Escape':
        if (filterInput.value) {
          filterInput.value = '';
          applyFilter('');
          try { sessionStorage.removeItem(SS_FILTER); } catch {}
        }
        break;
      default:
        if (e.key !== 'g') { lastKey = ''; }
    }
  });

  filterInput.addEventListener('input', () => applyFilter(filterInput.value));

  // ---- Rehydrate previously-expanded folders, BFS, only ones still in the
  // tree (stale paths are skipped). Runs after boot's initial loadInto. ----
  async function rehydrateExpansions() {
    if (expandedSet.size === 0) return;
    // BFS — depth N must finish before depth N+1 because children are lazy.
    let frontier = [treeEl];
    while (frontier.length > 0) {
      const next = [];
      for (const ul of frontier) {
        const dirLis = Array.from(ul.querySelectorAll(':scope > li.dir'));
        for (const li of dirLis) {
          if (expandedSet.has(li.dataset.path)) {
            await expand(li, { silent: true });
            const childUl = li.querySelector(':scope > ul.children');
            if (childUl) next.push(childUl);
          }
        }
      }
      frontier = next;
    }
  }

  function rehydrateFilter() {
    try {
      const f = sessionStorage.getItem(SS_FILTER) || '';
      if (f) {
        filterInput.value = f;
        applyFilter(f);
      }
    } catch {}
  }

  function rehydrateScroll() {
    try {
      const s = parseInt(sessionStorage.getItem(SS_SCROLL) || '0', 10);
      if (s > 0) treeNav.scrollTop = s;
    } catch {}
  }
  treeNav.addEventListener('scroll', () => {
    try { sessionStorage.setItem(SS_SCROLL, String(treeNav.scrollTop)); } catch {}
  }, { passive: true });

  filterInput.addEventListener('input', () => {
    try { sessionStorage.setItem(SS_FILTER, filterInput.value); } catch {}
  });

  (async function boot() {
    await loadInto(treeEl, 0);
    await rehydrateExpansions();
    await revealActivePath();
    rehydrateFilter();
    if (!cursor) {
      const nodes = visibleNodes();
      if (nodes.length > 0) setCursor(nodes[0]);
    }
    // Defer until layout settles after expansions inject DOM.
    requestAnimationFrame(rehydrateScroll);
  })();

  // bfcache: DOM is intact, just resync theme/font in case another tab changed them.
  window.addEventListener('pageshow', (e) => {
    if (e.persisted) {
      applyTheme(currentTheme());
      reflectFontUI(currentFont());
    }
  });
})();
