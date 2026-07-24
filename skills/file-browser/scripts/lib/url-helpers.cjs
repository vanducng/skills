// Tiny URL utilities shared by every renderer that links to /view, /browse, /file.
// `withRoot` appends ?root=<path> so navigation never loses the sidebar's tree
// root - server keeps using ?root= as the canonical override (resolveTreeRoot
// in http-server.cjs).

/**
 * Append `&root=<root>` to a URL if not already present.
 * Preserves any trailing `#fragment`. Returns the URL unchanged if `root`
 * is empty/null/undefined or the URL already declares root.
 */
function withRoot(url, root) {
  if (!root || typeof root !== 'string') return url;
  const hashIdx = url.indexOf('#');
  const base = hashIdx >= 0 ? url.slice(0, hashIdx) : url;
  const frag = hashIdx >= 0 ? url.slice(hashIdx) : '';
  if (/[?&]root=/.test(base)) return url;
  const sep = base.includes('?') ? '&' : '?';
  return base + sep + 'root=' + encodeURIComponent(root) + frag;
}

/**
 * Inline `<script>` for the page `<head>`. Runs synchronously before body
 * parses, so a redirect (when the URL lacks ?root=) happens before any paint
 * - no flash on click. Resolution preference when ?root= is absent:
 *   1. On reload / back-forward: stored localStorage root (preserve where
 *      the user was - the whole point of persistence).
 *   2. On fresh navigation (typed URL, external launcher, link without
 *      propagated root): derive from URL - dir-as-root, or file's parent.
 *      This anchors the tree at the file the user just opened, even if a
 *      stale localStorage value points elsewhere.
 *   3. Stored value as a last resort.
 * Reconciling localStorage with the server-validated `data-tree-root` lives
 * in assets/sidebar.js because it needs DOM access.
 */
const ROOT_PERSIST_HEAD_SCRIPT = `<script>(function(){try{
var u=new URL(location.href);
if(u.searchParams.get('root')!==null)return;
var nav=(performance.getEntriesByType('navigation')||[])[0];
var preserve=nav&&(nav.type==='reload'||nav.type==='back_forward');
var dir=u.searchParams.get('dir');
var file=u.searchParams.get('file');
var t=dir||file;
var s=null;try{s=localStorage.getItem('fb-tree-root');}catch(e){}
var r=null;
if(preserve&&s)r=s;
else if(t){var p=t.replace(/\\/+$/,'');if(dir){r=p;}else{var i=p.lastIndexOf('/');r=i>0?p.substring(0,i):'/';}}
else if(s)r=s;
if(r){u.searchParams.set('root',r);location.replace(u.toString());}
}catch(e){}})();</script>`;

module.exports = { withRoot, ROOT_PERSIST_HEAD_SCRIPT };
