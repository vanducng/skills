'use strict';
/**
 * paths.cjs - CWD-anchored path resolution, naming pattern, and plan-resolution helpers.
 *
 * P3: when config.paths.umbrella is set, paths.plans/reports/visuals/journals/state
 * anchor to GIT-ROOT/<umbrella>/. Docs always stays repo-root (CWD-anchored).
 * When umbrella is null the behavior is byte-identical to P2.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execFileSync } = require('child_process');

// ── git helpers ───────────────────────────────────────────────────────────

const CACHE_MAX = 1024;
function cacheGet(map, key) {
  if (!map.has(key)) return undefined;
  const value = map.get(key);
  map.delete(key);
  map.set(key, value);
  return value;
}

function cacheSet(map, key, value) {
  if (!map.has(key) && map.size >= CACHE_MAX) {
    const oldest = map.keys().next().value;
    if (oldest !== undefined) map.delete(oldest);
  }
  map.set(key, value);
  return value;
}

// Memoize git lookups per (cwd, process) — one subprocess call max per hook invocation.
const _gitRootCache = new Map();
const _gitBranchCache = new Map();

function runGit(args, cwd) {
  try {
    return execFileSync('git', args, {
      cwd: cwd || process.cwd(),
      encoding: 'utf8',
      timeout: 5000,
      stdio: ['pipe', 'pipe', 'pipe']
    }).trim() || null;
  } catch {
    return null;
  }
}

function getGitBranch(cwd) {
  const key = cwd || process.cwd();
  const cached = cacheGet(_gitBranchCache, key);
  if (cached !== undefined) return cached;
  const result = runGit(['branch', '--show-current'], cwd);
  return cacheSet(_gitBranchCache, key, result);
}

function getGitRoot(cwd) {
  const key = cwd || process.cwd();
  const cached = cacheGet(_gitRootCache, key);
  if (cached !== undefined) return cached;
  const result = runGit(['rev-parse', '--show-toplevel'], cwd);
  return cacheSet(_gitRootCache, key, result);
}

// The MAIN worktree root — always the first entry of `git worktree list`.
// In a normal checkout this equals getGitRoot (byte-identical behavior); inside
// a LINKED worktree it points back to the main checkout, so agent artifacts
// (the .workbench umbrella) survive `git worktree remove` instead of dying with the tree.
const _mainRootCache = new Map();
function getMainWorktreeRoot(cwd) {
  const key = cwd || process.cwd();
  const cached = cacheGet(_mainRootCache, key);
  if (cached !== undefined) return cached;
  let result = null;
  const out = runGit(['worktree', 'list', '--porcelain'], cwd);
  if (out) {
    // Porcelain blocks are blank-line separated; each starts with "worktree <path>".
    // Pick the first NON-bare entry — a bare repo's first block is its .git dir
    // (has a "bare" line) and must not become the artifact anchor.
    for (const block of out.split('\n\n')) {
      const lines = block.split('\n');
      const wl = lines.find(l => l.startsWith('worktree '));
      if (!wl || lines.some(l => l.trim() === 'bare')) continue;
      result = wl.slice('worktree '.length).trim() || null;
      break;
    }
  }
  return cacheSet(_mainRootCache, key, result);
}

// ── path helpers ──────────────────────────────────────────────────────────

/** Resolve symlinks for a stable path comparison; fall back to path.resolve. */
function realpathSafe(p) {
  try { return fs.realpathSync(p); } catch { return path.resolve(p); }
}

let _homeRealpath;
function isHomeDir(p) {
  const home = os.homedir();
  if (!p || !home) return false;
  if (_homeRealpath === undefined) _homeRealpath = realpathSafe(home);
  return realpathSafe(p) === _homeRealpath;
}

/** Strip trailing slashes; return null if blank after trim. */
function stripTrailing(p) {
  if (!p || typeof p !== 'string') return null;
  const s = p.trim().replace(/[/\\]+$/, '');
  return s || null;
}

function withTrailingSlash(p) {
  const s = p.replace(/\\/g, '/');
  return s.endsWith('/') ? s : `${s}/`;
}

// Public alias used by callers expecting normalizePath
const normalizePath = stripTrailing;

function sameOrChildPath(child, parent) {
  const c = stripTrailing(child);
  const p = stripTrailing(parent);
  if (!c || !p) return false;
  let cn = c.replace(/\\/g, '/');
  let pn = p.replace(/\\/g, '/');
  if (process.platform === 'win32') {
    cn = cn.toLowerCase();
    pn = pn.toLowerCase();
  }
  return cn === pn || cn.startsWith(`${pn}/`);
}

/**
 * Resolve the umbrella root directory when umbrella is active.
 * Anchored to the MAIN worktree so artifacts written from inside a linked
 * worktree land in the main repo's umbrella (and survive `git worktree remove`).
 * Returns absolute path to <mainRoot>/<umbrella>, or null when umbrella is not set.
 */
function resolveUmbrellaRoot(config, baseDir) {
  const umbrella = config?.paths?.umbrella;
  if (!umbrella) return null;
  // Main worktree == local git-root in a normal checkout (byte-identical), and the
  // main checkout when inside a linked worktree. config._gitRoot (the LOCAL root,
  // used for docs which stay branch-local) is only a last-resort fallback.
  // With NO git root anywhere (brand-new project not yet `git init`'d, or a non-git
  // tool session), anchor at the working dir so artifacts still land in .workbench/
  // instead of silently scattering to the legacy plans/ layout at cwd.
  let gitRoot = getMainWorktreeRoot(baseDir) || config._gitRoot || getGitRoot(baseDir)
    || baseDir || process.cwd();
  // Stray-ancestor guard: a coincidental repo rooted at $HOME (e.g. an accidental
  // `git init ~`) would otherwise swallow every project below it and scatter
  // .workbench into the home dir. When the resolved root is exactly $HOME but the
  // working dir is a real subdir below it, anchor to the working dir so artifacts
  // stay with the project (matches docs, which are always baseDir-anchored).
  if (baseDir && !config?.paths?.allowHomeRoot
      && isHomeDir(gitRoot)
      && !isHomeDir(baseDir)) {
    gitRoot = baseDir;
  }
  return path.join(gitRoot, umbrella);
}

/**
 * Compute plans path.
 * Umbrella-on: <gitRoot>/.workbench/plans
 * Umbrella-off: <baseDir>/plans  (legacy, byte-identical)
 */
function getPlansPath(baseDir, config, sessionId, readState, opts) {
  const featureRoot = resolveFeatureRoot(config, baseDir, sessionId, readState, opts);
  if (featureRoot) {
    return path.join(featureRoot, stripTrailing(config.paths?.plans) || 'plans');
  }
  // Legacy: second arg was pathsConfig in P2 — accept both shapes
  const pathsConfig = config?.paths ? config.paths : config;
  return path.join(baseDir, stripTrailing(pathsConfig?.plans) || 'plans');
}

/**
 * Docs path is ALWAYS repo-root (CWD) anchored — never moves under umbrella
 * or feature-first folders. Docs are source-controlled project material, not
 * generated per-feature workbench artifacts.
 */
function getDocsPath(baseDir, config) {
  const pathsConfig = config?.paths ? config.paths : config;
  return path.join(baseDir, stripTrailing(pathsConfig?.docs) || 'docs');
}

function getVisualsPath(baseDir, config, sessionId, readState, opts) {
  const featureRoot = resolveFeatureRoot(config, baseDir, sessionId, readState, opts);
  const name = stripTrailing(config?.paths?.visuals) || 'visuals';
  return featureRoot
    ? path.join(featureRoot, name)
    : path.join(baseDir, 'plans', name); // legacy fallback mirrors plans/visuals
}

function getJournalsPath(baseDir, config, sessionId, readState, opts) {
  const featureRoot = resolveFeatureRoot(config, baseDir, sessionId, readState, opts);
  const name = stripTrailing(config?.paths?.journals) || 'journals';
  return featureRoot
    ? path.join(featureRoot, name)
    : path.join(baseDir, 'plans', name); // legacy fallback: plans/journals
}

function getStatePath(baseDir, config, sessionId, readState, opts) {
  const featureRoot = resolveFeatureRoot(config, baseDir, sessionId, readState, opts);
  const name = stripTrailing(config?.paths?.state) || 'state';
  return featureRoot
    ? path.join(featureRoot, name)
    : path.join(baseDir, 'plans', 'goals'); // legacy fallback: plans/goals
}

/**
 * Compute the reports directory path.
 *
 * Two modes controlled by `anchor`:
 *   anchor = undefined/null → return a relative string ending with '/'.
 *   anchor = string (absolute dir) → return absolute path, NO trailing slash.
 *     When planPath is already absolute the isAbsolute guard prevents double-anchoring.
 *
 * Umbrella-on: default reports root = <umbrellaRoot>/reports (ignores pathsConfig.plans).
 * Umbrella-off: default = <plansDir>/reports (legacy, byte-identical to P2).
 * Session-active plan always overrides the default.
 */
function getReportsPath(planPath, resolvedBy, planConfig, pathsConfig, anchor, config, sessionId, readState, opts) {
  const subdir = stripTrailing(planConfig?.reportsDir) || 'reports';
  const activePlan = (planPath && resolvedBy === 'session') ? stripTrailing(planPath) : null;

  // Feature-first: reports nest in the FEATURE dir, unless a session-active plan
  // explicitly pins reports to that plan.
  if (!activePlan && config && config.paths?.layout === 'feature-first') {
    const featureRoot = resolveFeatureRoot(config, anchor || process.cwd(), sessionId, readState, opts);
    if (featureRoot) {
      if (!anchor) return withTrailingSlash(path.join(featureRoot, subdir));
      // Callers that append "/" themselves must use absolute mode (anchor set).
      return path.join(featureRoot, subdir);
    }
  }

  // Session-active plan overrides everything
  let reportsBase;
  if (activePlan) {
    reportsBase = activePlan;
  } else if (config) {
    const umbrellaRoot = resolveUmbrellaRoot(config, anchor || process.cwd());
    if (umbrellaRoot) {
      // Umbrella: reports is a direct sibling of plans under the umbrella root.
      // Return early — no subdir nesting needed, the subdir IS the leaf.
      const reportsLeaf = subdir; // 'reports' by default
      if (!anchor) return withTrailingSlash(path.join(umbrellaRoot, reportsLeaf));
      return path.join(umbrellaRoot, reportsLeaf);
    }
    reportsBase = stripTrailing(pathsConfig?.plans) || 'plans';
  } else {
    reportsBase = stripTrailing(pathsConfig?.plans) || 'plans';
  }

  if (!anchor) {
    // Relative mode: trailing slash
    return withTrailingSlash(path.join(reportsBase, subdir));
  }

  // Absolute mode: isAbsolute guard prevents double-anchoring
  const joined = path.isAbsolute(reportsBase)
    ? path.join(reportsBase, subdir)
    : path.join(anchor, reportsBase, subdir);
  return joined;
}

// ── date formatting ───────────────────────────────────────────────────────

/**
 * Expand date-format tokens into a timestamp string.
 * Uses global replacement so repeated tokens all expand correctly.
 */
function formatDate(fmt) {
  const now = new Date();
  const pad2 = n => String(n).padStart(2, '0');

  const substitutions = [
    // Longest tokens first so YYYY isn't partially consumed by YY
    ['YYYY', String(now.getFullYear())],
    ['YY',   String(now.getFullYear()).slice(-2)],
    ['MM',   pad2(now.getMonth() + 1)],
    ['DD',   pad2(now.getDate())],
    ['HH',   pad2(now.getHours())],
    ['mm',   pad2(now.getMinutes())],
    ['ss',   pad2(now.getSeconds())]
  ];

  let result = fmt;
  for (const [tok, val] of substitutions) {
    result = result.split(tok).join(val);
  }
  return result;
}

// ── naming pattern ────────────────────────────────────────────────────────

/** Extract a numeric issue ID from a branch name using common conventions. */
function extractIssueFromBranch(branch) {
  if (!branch) return null;
  const attempts = [
    /(?:issue|gh|fix|feat|bug)[/-]?(\d+)/i,
    /[/-](\d+)[/-]/,
    /#(\d+)/
  ];
  for (const re of attempts) {
    const hit = branch.match(re);
    if (hit) return hit[1];
  }
  return null;
}

/**
 * Resolve naming pattern: substitutes {date} and {issue}, keeps {slug} as literal placeholder.
 */
function resolveNamingPattern(planConfig, gitBranch) {
  const formattedDate = formatDate(planConfig.dateFormat);
  const issueNum = extractIssueFromBranch(gitBranch);
  const qualifiedIssue = (issueNum && planConfig.issuePrefix)
    ? `${planConfig.issuePrefix}${issueNum}`
    : null;

  let pat = planConfig.namingFormat.split('{date}').join(formattedDate);

  if (qualifiedIssue) {
    pat = pat.split('{issue}').join(qualifiedIssue);
  } else {
    pat = pat.replace(/-?\{issue\}-?/, '-').replace(/--+/g, '-');
  }

  pat = pat
    .replace(/^-+/, '')
    .replace(/-+$/, '')
    .replace(/-+(\{slug\})/g, '-$1')
    .replace(/(\{slug\})-+/g, '$1-')
    .replace(/--+/g, '-');

  return pat;
}

// ── plan resolution ───────────────────────────────────────────────────────

function cleanSlug(raw) {
  if (!raw) return '';
  return raw
    .replace(/[<>:"/\\|?*\x00-\x1f\x7f]/g, '')
    .replace(/[^a-z0-9-]/gi, '-')
    .replace(/-+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 100);
}

function escapeRe(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function slugFromBranch(branch, pattern) {
  if (!branch) return null;
  const re = pattern
    ? new RegExp(pattern)
    : /(?:feat|fix|chore|refactor|docs)\/(?:[^/]+\/)?(.+)/;
  const m = branch.match(re);
  return m ? cleanSlug(m[1]) : null;
}

/**
 * Walk the resolution order to find an active or suggested plan.
 * `readState` is injected to avoid circular deps and enable testing.
 * Returns { path, resolvedBy } where resolvedBy is 'session'|'branch'|null.
 */
/** Strip a leading `YYYYMMDD-HHMM-` or `YYMMDD-HHMM-` date prefix from a plan dir name. */
function planDirSlug(name) {
  return name.replace(/^\d{6,8}-\d{4}-/, '');
}

function resolvePlanPath(sessionId, config, readState, baseDir) {
  baseDir = baseDir || process.cwd();
  const resolution = config?.plan?.resolution || {};
  const order = resolution.order || ['session', 'branch'];
  let stateLoaded = false;
  let stateCache = null;
  const getState = () => {
    if (!stateLoaded) {
      stateCache = readState ? readState(sessionId) : null;
      stateLoaded = true;
    }
    return stateCache;
  };
  const readStateOnce = readState ? ((_sid) => getState()) : null;

  for (const step of order) {
    if (step === 'session') {
      const state = getState();
      if (state?.activePlan) {
        let resolved = state.activePlan;
        if (!path.isAbsolute(resolved) && state.sessionOrigin) {
          resolved = path.join(state.sessionOrigin, resolved);
        }
        return { path: resolved, resolvedBy: 'session' };
      }
    } else if (step === 'branch') {
      try {
        const branch = getGitBranch(baseDir);
        const slug = slugFromBranch(branch, resolution.branchPattern);
        if (!slug) continue;
        // Anchor to the umbrella/main-worktree plans dir — the old cwd-relative
        // `plansDir` silently no-op'd inside linked worktrees.
        // readOnly=true prevents ensureFeatureMeta writes during plan resolution.
        // Ensure readState stays a pure reader; if it called resolvePlanPath
        // lazily this chain could recurse.
        const plansDir = getPlansPath(baseDir, config, sessionId, readStateOnce, { readOnly: true });
        if (!fs.existsSync(plansDir)) continue;
        const dirs = fs.readdirSync(plansDir, { withFileTypes: true })
          .filter(e => e.isDirectory());
        // Prefer an EXACT slug match; fall back to substring only when unambiguous.
        // On >1 candidate, REFUSE — the old `matches[last]` silently mis-converged.
        const exact = dirs.filter(e => planDirSlug(e.name) === slug);
        const substr = dirs.filter(e => e.name.includes(slug));
        const ambiguous = exact.length > 1 || (exact.length === 0 && substr.length > 1);
        if (ambiguous) {
          process.stderr.write(`[paths] ambiguous branch plan resolution for slug "${slug}" in ${plansDir}; skipping branch fallback\n`);
          continue;
        }
        const pick = exact.length === 1 ? exact[0]
          : substr.length === 1 ? substr[0]
          : null;
        if (pick) return { path: path.join(plansDir, pick.name), resolvedBy: 'branch' };
      } catch { /* ignore fs errors */ }
    }
  }
  return { path: null, resolvedBy: null };
}

/** Task list ID = plan dir basename, only for session-active plans. */
function extractTaskListId(resolved) {
  if (!resolved || resolved.resolvedBy !== 'session' || !resolved.path) return null;
  return path.basename(resolved.path);
}

// ── feature-first resolution (gated on config.paths.layout === 'feature-first') ──

/** Prefix-preserving ticket extractor: `feat/ELT-3316-x` → `ELT-3316`; `gh3251` → `GH-3251`. */
function extractTicketFromBranch(branch, prefixes) {
  if (!branch) return null;
  const list = (Array.isArray(prefixes) && prefixes.length) ? prefixes : ['ELT', 'GH', 'PROJ'];
  const re = new RegExp(`\\b(${list.map(escapeRe).join('|')})-?(\\d+)\\b`, 'i');
  const m = branch.match(re);
  return m ? `${m[1].toUpperCase()}-${m[2]}` : null;
}

/** Feature id from `{ticket}-{slug}` or `{slug}` (lowercased, cleaned).
 *  Strips a leading duplicate ticket from slug so `feat/ELT-3316-manual-upload`
 *  → `elt-3316-manual-upload`, not `elt-3316-elt-3316-manual-upload`. */
function computeFeatureId(ticket, slug) {
  if (ticket) {
    const dashIdx = ticket.lastIndexOf('-');
    const pre = dashIdx >= 0 ? ticket.slice(0, dashIdx) : ticket;
    const num = dashIdx >= 0 ? ticket.slice(dashIdx + 1) : '';
    const ticketPrefix = num
      ? `^(?:${escapeRe(pre)}-?)?${escapeRe(num)}-?`
      : `^${escapeRe(pre)}-?`;
    const desc = slug ? slug.replace(new RegExp(ticketPrefix, 'i'), '') : '';
    return cleanSlug((desc ? `${ticket}-${desc}` : ticket).toLowerCase());
  }
  if (slug) return cleanSlug(slug.toLowerCase()); // lowercase for parity with the ticket branch
  return null;
}

const _featureFindCache = new Map();

/** Scan features/<id>/feature.json once; return a unique ticket match, then unique slug match. */
function findFeature(featuresDir, ticket, slug) {
  let dirStamp;
  try {
    const st = fs.statSync(featuresDir);
    dirStamp = `${st.mtimeMs}:${st.size}`;
  } catch { return null; }
  const cacheKey = `${featuresDir}|${dirStamp}|${ticket || ''}|${slug || ''}`;
  const cached = cacheGet(_featureFindCache, cacheKey);
  if (cached !== undefined) return cached;

  let dirs;
  try { dirs = fs.readdirSync(featuresDir, { withFileTypes: true }).filter(e => e.isDirectory()); }
  catch { return null; }

  const ticketHits = [];
  const slugHits = [];
  for (const d of dirs) {
    try {
      const meta = JSON.parse(fs.readFileSync(path.join(featuresDir, d.name, 'feature.json'), 'utf8'));
      if (ticket && meta && meta.ticket === ticket) ticketHits.push(d.name);
      if (slug && meta && meta.slug === slug) slugHits.push(d.name);
    } catch { /* missing/invalid feature.json — skip */ }
  }
  const found = ticketHits.length === 1 ? ticketHits[0]
    : slugHits.length === 1 ? slugHits[0]
    : null;
  return cacheSet(_featureFindCache, cacheKey, found);
}

/** Remove orphaned feature.json temp files from interrupted metadata writes. */
function cleanupStaleFeatureTemps(dir, olderThanMs) {
  let entries;
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
  const cutoff = Date.now() - olderThanMs;
  for (const e of entries) {
    if (!e.isFile() || !e.name.startsWith('feature.json.') || !e.name.endsWith('.tmp')) continue;
    const p = path.join(dir, e.name);
    try {
      const st = fs.statSync(p);
      if (st.mtimeMs < cutoff) fs.unlinkSync(p);
    } catch { /* ignore stale temp cleanup failures */ }
  }
}

/** Create features/<id>/feature.json if absent. Idempotent, atomic (rename), best-effort. */
function ensureFeatureMeta(featuresDir, id, meta) {
  const dir = path.join(featuresDir, id);
  const metaPath = path.join(dir, 'feature.json');
  if (fs.existsSync(metaPath)) return;
  let tmp = null;
  try {
    fs.mkdirSync(dir, { recursive: true });
    cleanupStaleFeatureTemps(dir, 60 * 60 * 1000);
    tmp = `${metaPath}.${process.pid}.${Date.now()}.${Math.random().toString(36).slice(2)}.tmp`;
    fs.writeFileSync(tmp, JSON.stringify(meta, null, 2));
    // POSIX can atomically replace; Windows throws if the destination appears in
    // a race. Either way, the first committed writer wins and losers are ignored.
    fs.renameSync(tmp, metaPath);
    tmp = null;
  } catch (e) {
    // Never block resolution on a write failure.
    if (process.env.VD_DEBUG_PATHS) {
      process.stderr.write(`[paths] ensureFeatureMeta failed for ${id}: ${e?.message || e}\n`);
    }
  } finally {
    try { if (tmp && fs.existsSync(tmp)) fs.unlinkSync(tmp); } catch { /* ignore cleanup failure */ }
  }
}

// NOTE: per-process cache, keyed by session and branch, with a soft cap for long-lived hosts.
const _featureIdCache = new Map();
const _featureStateCache = new WeakMap();

function readFeatureState(readState, sessionId) {
  if (!readState) return null;
  let bySession = _featureStateCache.get(readState);
  if (!bySession) {
    bySession = new Map();
    _featureStateCache.set(readState, bySession);
  }
  const key = sessionId || '';
  if (bySession.has(key)) return bySession.get(key);
  const state = readState(sessionId);
  cacheSet(bySession, key, state);
  return state;
}

/**
 * Resolve the feature id for the current context. Pure read except a one-time idempotent
 * feature.json create on first strong-signal resolution. First hit wins; no call-time date,
 * no LLM slug. Returns null on no signal (caller routes to _global/scratch).
 * Read-only by default; lifecycle commands that intentionally create metadata pass
 * { readOnly: false } explicitly.
 */
function resolveFeatureId(config, baseDir, sessionId, readState, opts) {
  baseDir = baseDir || process.cwd();
  const umbrellaRoot = resolveUmbrellaRoot(config, baseDir);
  if (!umbrellaRoot) return null;
  const state = readFeatureState(readState, sessionId);
  const readOnly = opts?.readOnly !== false;

  if (state && typeof state.featureId === 'string' && state.featureId) {
    const stateKey = `${umbrellaRoot}|${sessionId || ''}|${state.featureId}|state|${state?.activePlan || ''}|ro:${readOnly ? '1' : '0'}`;
    const cached = cacheGet(_featureIdCache, stateKey);
    if (cached !== undefined) return cached;
    return cacheSet(_featureIdCache, stateKey, state.featureId);
  }

  const branch = getGitBranch(baseDir);
  const cacheKey = `${umbrellaRoot}|${sessionId || ''}|${state?.featureId || ''}|${branch || ''}|${state?.activePlan || ''}|ro:${readOnly ? '1' : '0'}`;
  const cached = cacheGet(_featureIdCache, cacheKey);
  if (cached !== undefined) return cached;

  const featuresDir = path.join(umbrellaRoot, 'features');
  const remember = (id) => cacheSet(_featureIdCache, cacheKey, id);

  // branch signals
  const ticket = extractTicketFromBranch(branch, config?.plan?.ticketPrefixes);
  const slug = slugFromBranch(branch, config?.plan?.resolution?.branchPattern);

  // 2-3. match an EXISTING feature (survives slug drift / relabel)
  const existing = findFeature(featuresDir, ticket, slug);
  if (existing) return remember(existing);

  // 4. strong branch signal, no existing match → compute id + create the anchor (idempotent)
  const computed = computeFeatureId(ticket, slug);
  if (computed) {
    if (!readOnly) {
      ensureFeatureMeta(featuresDir, computed, {
        id: computed, ticket: ticket || null, slug: slug || null, label: slug || computed,
        status: 'active', created: new Date().toISOString(), parentId: null,
        supersededBy: null, relatedDocs: [], branches: branch ? [branch] : []
      });
    }
    return remember(computed);
  }

  // 5. session-active plan → its parent feature (plan path stored absolute in state)
  if (state && state.activePlan) {
    let p = state.activePlan;
    if (!path.isAbsolute(p) && state.sessionOrigin) p = path.join(state.sessionOrigin, p);
    const seg = path.relative(featuresDir, p).split(path.sep);
    if (seg[0] && !seg[0].startsWith('..')) return remember(seg[0]);
  }

  // 6. no signal
  return remember(null);
}

/** Feature root: umbrella root verbatim when not feature-first (byte-identical); else features/<id> or _global/scratch. */
function resolveFeatureRoot(config, baseDir, sessionId, readState, opts) {
  baseDir = baseDir || process.cwd();
  const u = resolveUmbrellaRoot(config, baseDir);
  if (!u || config?.paths?.layout !== 'feature-first') return u;
  const id = resolveFeatureId(config, baseDir, sessionId, readState, opts);
  // No feature signal: use the documented scratch staging area. Hook context
  // surfaces this path, and `workbench new --from-scratch` can promote it later.
  return id ? path.join(u, 'features', id) : path.join(u, '_global', 'scratch');
}

/** Root-level cross-feature zones (umbrella only). */
function getGlobalPath(baseDir, config) {
  const u = resolveUmbrellaRoot(config, baseDir);
  return u ? path.join(u, '_global') : null;
}
function getArchivePath(baseDir, config) {
  const u = resolveUmbrellaRoot(config, baseDir);
  return u ? path.join(u, '_archive') : null;
}

function isGlobalScratchPath(candidate, baseDir, config) {
  const globalRoot = getGlobalPath(baseDir, config);
  return !!(globalRoot && sameOrChildPath(candidate, path.join(globalRoot, 'scratch')));
}

// ── venv resolution ───────────────────────────────────────────────────────

/** Check project-local then global ~/.claude for a skills venv python binary. */
function resolveSkillsVenv(effectiveCwd) {
  const cfgDir = '.claude';
  const localBin = path.join(effectiveCwd || process.cwd(), cfgDir, 'skills', '.venv', 'bin', 'python3');
  const globalBin = path.join(os.homedir(), '.claude', 'skills', '.venv', 'bin', 'python3');
  if (fs.existsSync(localBin)) return `${cfgDir}/skills/.venv/bin/python3`;
  if (fs.existsSync(globalBin)) return '~/.claude/skills/.venv/bin/python3';
  return null;
}

module.exports = {
  normalizePath,
  stripTrailing,
  getReportsPath,
  getPlansPath,
  getDocsPath,
  getVisualsPath,
  getJournalsPath,
  getStatePath,
  formatDate,
  resolveNamingPattern,
  resolvePlanPath,
  extractTaskListId,
  resolveSkillsVenv,
  getGitBranch,
  getGitRoot,
  getMainWorktreeRoot,
  realpathSafe,
  isHomeDir,
  slugFromBranch,
  extractIssueFromBranch,
  resolveUmbrellaRoot,
  cleanSlug,
  extractTicketFromBranch,
  computeFeatureId,
  resolveFeatureId,
  resolveFeatureRoot,
  getGlobalPath,
  getArchivePath,
  isGlobalScratchPath
};
