'use strict';
/**
 * config.cjs - Three-layer config loader: defaults ← global ← project-local.
 *
 * Local config resolves via git-root (not a literal unexpanded HOME string).
 * paths.umbrella (default null) opts a repo into the .workbench/ layout.
 * Config file: .vd.json only. A lingering legacy .ck.json raises a migration
 * error (run the cktovd skill) — vd no longer reads .ck.json.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execFileSync } = require('child_process');
const { getMainWorktreeRoot, isHomeDir } = require('./paths.cjs');

const DEFAULT_CONFIG = {
  plan: {
    namingFormat: '{date}-{issue}-{slug}',
    dateFormat: 'YYMMDD-HHmm',
    issuePrefix: null,
    ticketPrefixes: ['ELT', 'GH', 'PROJ'],
    reportsDir: 'reports',
    resolution: {
      order: ['session', 'branch'],
      branchPattern: '(?:feat|fix|chore|refactor|docs)/(?:[^/]+/)?(.+)'
    },
    validation: {
      mode: 'prompt',
      minQuestions: 3,
      maxQuestions: 8,
      focusAreas: ['assumptions', 'risks', 'tradeoffs', 'architecture']
    }
  },
  paths: {
    docs: 'docs',
    plans: 'plans',
    // Umbrella: null = legacy CWD-anchored layout.
    // Set to a relative name (e.g. ".workbench") in <git-root>/.vd.json to opt in.
    umbrella: null,
    // Layout: 'type-first' (flat type siblings) | 'feature-first' (per-feature folders).
    // Default 'type-first' → byte-identical to legacy; opt in per-repo via .vd.json.
    layout: 'type-first',
    allowHomeRoot: false,
    visuals: 'visuals',
    journals: 'journals',
    state: 'state'
  },
  locale: { thinkingLanguage: null, responseLanguage: null },
  trust: { passphrase: null, enabled: false },
  project: { type: 'auto', packageManager: 'auto', framework: 'auto' },
  codingLevel: -1,
  assertions: [],
  hooks: {
    'session-init': true,
    'subagent-init': true,
    'dev-rules-reminder': true,
    'session-state': true
  }
};

/**
 * Layer two config objects, with override taking priority.
 *
 * Rules (derived from observed contract behavior):
 *   - Scalar in override → use override value
 *   - Array in override  → replace entirely (never concat)
 *   - Object in override that is empty ({}) → skip; base value wins
 *   - Object in override that is non-empty  → recurse into both
 *   - Key missing in base → copy from override
 */
function layerConfigs(base, override) {
  if (override === null || override === undefined || typeof override !== 'object') return base;
  if (base === null || base === undefined || typeof base !== 'object') return override;

  const out = Object.assign({}, base);
  const keys = Object.keys(override);

  for (let i = 0; i < keys.length; i++) {
    const k = keys[i];
    const ov = override[k];

    if (Array.isArray(ov)) {
      out[k] = ov.slice(); // replace, never merge
    } else if (ov !== null && typeof ov === 'object') {
      // Empty object means "inherit from base" — skip
      if (Object.keys(ov).length === 0) continue;
      out[k] = layerConfigs(base[k] || {}, ov);
    } else {
      out[k] = ov; // scalar: override wins
    }
  }
  return out;
}

function readJson(filePath) {
  try {
    if (!fs.existsSync(filePath)) return null;
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return null;
  }
}

function getGitRoot(cwd) {
  try {
    return execFileSync('git', ['rev-parse', '--show-toplevel'], {
      cwd: cwd || process.cwd(),
      encoding: 'utf8',
      timeout: 5000,
      stdio: ['pipe', 'pipe', 'pipe']
    }).trim();
  } catch {
    return null;
  }
}

/**
 * Sanitize umbrella value: must be a relative, single-segment name that stays inside
 * the repo. Rejects absolute paths, path-traversal sequences, and empty strings.
 * Returns the sanitized string or null (which means "disabled").
 */
function sanitizeUmbrella(raw, gitRoot) {
  if (!raw || typeof raw !== 'string') return null;
  const trimmed = raw.trim();
  if (!trimmed) return null;
  // Reject absolute paths
  if (path.isAbsolute(trimmed)) return null;
  // Reject any traversal component
  const parts = trimmed.split(/[/\\]/);
  if (parts.some(p => p === '..' || p === '')) return null;
  // Confirm the resolved path stays inside git root
  if (gitRoot) {
    const resolved = path.resolve(gitRoot, trimmed);
    if (!resolved.startsWith(gitRoot + path.sep) && resolved !== gitRoot) return null;
  }
  return trimmed;
}

/**
 * Raise if a legacy .ck.json lingers without its .vd.json. vd no longer reads
 * .ck.json — run the cktovd skill (or rename .ck.json → .vd.json) to migrate.
 */
function assertMigrated(vdPath, ckPath) {
  if (!ckPath) return;
  if (!fs.existsSync(vdPath) && fs.existsSync(ckPath)) {
    throw new Error(
      `Legacy ${path.basename(ckPath)} found at ${ckPath} but no ${path.basename(vdPath)}. ` +
      `vd no longer reads .ck.json — run the cktovd skill, or rename it to ${path.basename(vdPath)}.`
    );
  }
}

/**
 * Read the MAIN worktree's .vd.json (or null). Layout-determining keys come
 * from here so linked worktrees can't disagree about artifact resolution.
 */
function getMainWorktreeConfigDetails(cwd) {
  const mainRoot = getMainWorktreeRoot(cwd);
  if (!mainRoot) return null;
  const config = readJson(path.join(mainRoot, '.vd.json'));
  if (isHomeDir(mainRoot) && config?.paths?.allowHomeRoot !== true) return null;
  return { root: mainRoot, config };
}

/** Public compatibility helper: returns only the main worktree .vd.json payload. */
function getMainWorktreeConfig(cwd) {
  const details = getMainWorktreeConfigDetails(cwd);
  return details ? details.config : null;
}

/** Overlay repo-wide layout/resolution keys from the main worktree config. */
function applyMainWorktreeLayout(merged, mainCfg) {
  if (!mainCfg) return merged;
  const out = Object.assign({}, merged);
  if (mainCfg.paths) {
    out.paths = Object.assign({}, merged.paths);
    if (typeof mainCfg.paths.umbrella === 'string') out.paths.umbrella = mainCfg.paths.umbrella;
    if (typeof mainCfg.paths.layout === 'string') out.paths.layout = mainCfg.paths.layout;
    if (typeof mainCfg.paths.allowHomeRoot === 'boolean') out.paths.allowHomeRoot = mainCfg.paths.allowHomeRoot;
  }
  if (mainCfg.plan) {
    out.plan = Object.assign({}, merged.plan);
    if (Array.isArray(mainCfg.plan.ticketPrefixes)) {
      out.plan.ticketPrefixes = mainCfg.plan.ticketPrefixes.slice();
    }
    if (mainCfg.plan.resolution && typeof mainCfg.plan.resolution === 'object') {
      out.plan.resolution = layerConfigs(merged.plan?.resolution || {}, mainCfg.plan.resolution);
    }
  }
  return out;
}

/**
 * Load config: DEFAULT ← global (~/.claude/.vd.json) ← project (<git-root>/.vd.json),
 * then overlay repo-wide layout/resolution keys from the MAIN worktree.
 * No .ck.json fallback — a lingering legacy file raises a migration error.
 * Falls back to defaults on any error.
 */
function loadConfig() {
  const globalPath = path.join(os.homedir(), '.claude', '.vd.json');
  const gitRoot = getGitRoot(process.cwd());
  const localPath = gitRoot ? path.join(gitRoot, '.vd.json') : null;

  // No silent .ck.json fallback — raise a migration error if a legacy file lingers.
  assertMigrated(globalPath, path.join(os.homedir(), '.claude', '.ck.json'));
  if (gitRoot) assertMigrated(localPath, path.join(gitRoot, '.ck.json'));

  const globalCfg = readJson(globalPath);
  const localCfg = localPath ? readJson(localPath) : null;
  const gitMetadata = gitRoot ? path.join(gitRoot, '.git') : null;
  let gitDirIsFile = false;
  try {
    gitDirIsFile = !!(gitMetadata && fs.existsSync(gitMetadata) && !fs.statSync(gitMetadata).isDirectory());
  } catch { /* ignore */ }

  try {
    let merged = layerConfigs({}, DEFAULT_CONFIG);
    let umbrellaGitRoot = gitRoot;
    if (globalCfg) merged = layerConfigs(merged, globalCfg);
    if (localCfg) merged = layerConfigs(merged, localCfg);
    // Keep this merge path even when global/local configs are absent: linked
    // worktrees still need the main checkout's layout overlay.
    if (gitDirIsFile) {
      const mainWorktree = getMainWorktreeConfigDetails(process.cwd());
      merged = applyMainWorktreeLayout(merged, mainWorktree ? mainWorktree.config : null);
      if (mainWorktree) {
        umbrellaGitRoot = mainWorktree.root;
      }
      // If mainWorktree is null, no safe main root exists (for example, a
      // stray HOME repo). Keep the local root so sanitizeUmbrella preserves
      // the same guard.
      // NOTE: that fallback makes artifacts worktree-local instead of shared;
      // fixing the unsafe main root or enabling allowHomeRoot is required to share.
    }
    return buildResult(merged, gitRoot, umbrellaGitRoot);
  } catch {
    // DEFAULT_CONFIG has umbrella: null, so umbrellaGitRoot is irrelevant here.
    // Keep gitRoot for both to avoid another worktree lookup on the error path.
    return buildResult(layerConfigs({}, DEFAULT_CONFIG), gitRoot, gitRoot);
  }
}

function buildResult(merged, gitRoot, umbrellaGitRoot) {
  const rawPaths = merged.paths || DEFAULT_CONFIG.paths;
  // Sanitize umbrella: coerce to null if invalid; needs gitRoot to check confinement
  const umbrella = sanitizeUmbrella(rawPaths.umbrella, umbrellaGitRoot || gitRoot || null);

  return {
    plan: merged.plan || DEFAULT_CONFIG.plan,
    paths: {
      docs:     rawPaths.docs     || DEFAULT_CONFIG.paths.docs,
      plans:    rawPaths.plans    || DEFAULT_CONFIG.paths.plans,
      umbrella,
      layout:   rawPaths.layout === 'feature-first' ? 'feature-first' : 'type-first',
      allowHomeRoot: rawPaths.allowHomeRoot === true,
      visuals:  rawPaths.visuals  || DEFAULT_CONFIG.paths.visuals,
      journals: rawPaths.journals || DEFAULT_CONFIG.paths.journals,
      state:    rawPaths.state    || DEFAULT_CONFIG.paths.state
    },
    locale: merged.locale || DEFAULT_CONFIG.locale,
    trust: merged.trust || DEFAULT_CONFIG.trust,
    project: merged.project || DEFAULT_CONFIG.project,
    codingLevel: merged.codingLevel ?? -1,
    assertions: merged.assertions || [],
    hooks: merged.hooks || DEFAULT_CONFIG.hooks,
    subagent: merged.subagent || null,
    // Expose resolved gitRoot so hooks don't need to re-run git
    _gitRoot: gitRoot || null
  };
}

module.exports = { DEFAULT_CONFIG, layerConfigs, loadConfig, getGitRoot, sanitizeUmbrella, assertMigrated, getMainWorktreeConfig, applyMainWorktreeLayout };
