// Behavior + vim keybindings live in /assets/sidebar.js.

const path = require('path');

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function renderSidebar({ treeRoot, activePath }) {
  const rootName = path.basename(treeRoot) || treeRoot;
  return `
<aside class="fb-sidebar" data-tree-root="${esc(treeRoot)}" data-active-path="${esc(activePath || '')}">
  <header class="fb-sidebar-header">
    <button class="fb-sidebar-toggle" type="button" title="Toggle sidebar (\\)">≡</button>
    <span class="fb-sidebar-root-label" title="${esc(treeRoot)}">${esc(rootName)}</span>
    <button class="fb-sidebar-help" type="button" title="Keybindings (?)">?</button>
  </header>
  <div class="fb-sidebar-toolbar">
    <div class="fb-sidebar-fontgroup" role="group" aria-label="Font size">
      <button class="fb-sidebar-font" data-size="S" type="button" title="Small">S</button>
      <button class="fb-sidebar-font" data-size="M" type="button" title="Medium">M</button>
      <button class="fb-sidebar-font" data-size="L" type="button" title="Large">L</button>
    </div>
    <button class="fb-sidebar-theme" type="button" title="Toggle dark / light (T)" aria-label="Toggle theme">
      <span class="theme-icon" data-icon="dark">☾</span>
      <span class="theme-icon" data-icon="light">☀</span>
    </button>
  </div>
  <div class="fb-sidebar-filter-row">
    <input class="fb-sidebar-filter" type="text" placeholder="/ to filter" autocomplete="off" spellcheck="false" />
  </div>
  <nav class="fb-sidebar-tree" tabindex="0">
    <ul class="tree" data-path="${esc(treeRoot)}" data-loaded="false"></ul>
  </nav>
  <div class="fb-sidebar-help-overlay" hidden>
    <div class="cheatsheet">
      <h3>Keybindings</h3>
      <table>
        <tr><td><kbd>j</kbd> / <kbd>k</kbd></td><td>down / up</td></tr>
        <tr><td><kbd>h</kbd></td><td>collapse · jump to parent</td></tr>
        <tr><td><kbd>-</kbd></td><td>jump to parent folder</td></tr>
        <tr><td><kbd>l</kbd></td><td>expand folder</td></tr>
        <tr><td><kbd>Enter</kbd> · <kbd>o</kbd></td><td>open file</td></tr>
        <tr><td><kbd>O</kbd></td><td>open in new tab</td></tr>
        <tr><td><kbd>gg</kbd> / <kbd>G</kbd></td><td>top / bottom</td></tr>
        <tr><td><kbd>/</kbd></td><td>filter</td></tr>
        <tr><td><kbd>n</kbd> / <kbd>N</kbd></td><td>next / prev match</td></tr>
        <tr><td><kbd>r</kbd></td><td>reload current folder</td></tr>
        <tr><td><kbd>T</kbd></td><td>toggle dark / light</td></tr>
        <tr><td><kbd>\\</kbd></td><td>toggle sidebar</td></tr>
        <tr><td><kbd>?</kbd></td><td>this help</td></tr>
        <tr><td><kbd>Esc</kbd></td><td>clear filter / close help</td></tr>
      </table>
    </div>
  </div>
</aside>
<script src="/assets/sidebar.js" defer></script>
`;
}

module.exports = { renderSidebar };
