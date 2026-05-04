/**
 * Compose a full markdown viewer HTML page using the novel-theme template.
 * Extracted from markdown-render's server.cjs so http-server can dispatch
 * directly without dragging the whole boot sequence.
 */

const fs = require('fs');
const path = require('path');

const { renderMarkdownFile, renderTOCHtml } = require('./markdown-renderer.cjs');
const { generateNavSidebar, generateNavFooter, detectPlan, getNavigationContext } = require('./plan-navigator.cjs');

function renderMarkdownPage(filePath, assetsDir) {
  const { html, toc, frontmatter, title } = renderMarkdownFile(filePath);
  const tocHtml = renderTOCHtml(toc);
  const navSidebar = generateNavSidebar(filePath);
  const navFooter = generateNavFooter(filePath);
  const planInfo = detectPlan(filePath);
  const navContext = getNavigationContext(filePath);

  const templatePath = path.join(assetsDir, 'template.html');
  let template = fs.readFileSync(templatePath, 'utf8');

  // "Back to folder" button (top-left of header)
  const parentDir = path.dirname(filePath);
  const backButton = `
    <a href="/browse?dir=${encodeURIComponent(parentDir)}" class="icon-btn back-btn" title="Back to folder">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M19 12H5M12 19l-7-7 7-7"/>
      </svg>
    </a>`;

  // Header prev/next for plan phase files
  let headerNav = '';
  if (navContext.prev || navContext.next) {
    const prevBtn = navContext.prev && fs.existsSync(navContext.prev.file)
      ? `<a href="/view?file=${encodeURIComponent(navContext.prev.file)}" class="header-nav-btn prev" title="${navContext.prev.name}">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
          <span>Prev</span>
        </a>`
      : '';
    const nextBtn = navContext.next && fs.existsSync(navContext.next.file)
      ? `<a href="/view?file=${encodeURIComponent(navContext.next.file)}" class="header-nav-btn next" title="${navContext.next.name}">
          <span>Next</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
        </a>`
      : '';
    headerNav = `<div class="header-nav">${prevBtn}${nextBtn}</div>`;
  }

  return template
    .replace(/\{\{title\}\}/g, title)
    .replace('{{toc}}', tocHtml)
    .replace('{{nav-sidebar}}', navSidebar)
    .replace('{{nav-footer}}', navFooter)
    .replace('{{content}}', html)
    .replace('{{has-plan}}', planInfo.isPlan ? 'has-plan' : '')
    .replace('{{frontmatter}}', JSON.stringify(frontmatter || {}))
    .replace('{{back-button}}', backButton)
    .replace('{{header-nav}}', headerNav);
}

const MARKDOWN_EXTS = new Set(['.md', '.markdown', '.mdx']);

function isMarkdown(filePath) {
  return MARKDOWN_EXTS.has(path.extname(filePath).toLowerCase());
}

module.exports = {
  renderMarkdownPage,
  isMarkdown,
  MARKDOWN_EXTS
};
