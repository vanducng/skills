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

// Memoize git-root per (cwd, process) — one subprocess call max per hook invocation.
const _gitRootCache = new Map();

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

function getGitBranch(cwd) { return runGit(['branch', '--show-current'], cwd); }

function getGitRoot(cwd) {
  const key = cwd || process.cwd();
  if (_gitRootCache.has(key)) return _gitRootCache.get(key);
  const result = runGit(['rev-parse', '--show-toplevel'], cwd);
  _gitRootCache.set(key, result);
  return result;
}

// The MAIN worktree root — always the first entry of `git worktree list`.
// In a normal checkout this equals getGitRoot (byte-identical behavior); inside
// a LINKED worktree it points back to the main checkout, so agent artifacts
// (the .workbench umbrella) survive `git worktree remove` instead of dying with the tree.
const _mainRootCache = new Map();
function getMainWorktreeRoot(cwd) {
  const key = cwd || process.cwd();
  if (_mainRootCache.has(key)) return _mainRootCache.get(key);
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
  _mainRootCache.set(key, result);
  return result;
}

// ── path helpers ──────────────────────────────────────────────────────────

/** Strip trailing slashes; return null if blank after trim. */
function stripTrailing(p) {
  if (!p || typeof p !== 'string') return null;
  const s = p.trim().replace(/[/\\]+$/, '');
  return s || null;
}

// Public alias used by callers expecting normalizePath
const normalizePath = stripTrailing;

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
  const gitRoot = getMainWorktreeRoot(baseDir) || config._gitRoot || getGitRoot(baseDir);
  if (!gitRoot) return null;
  return path.join(gitRoot, umbrella);
}

/**
 * Compute plans path.
 * Umbrella-on: <gitRoot>/.workbench/plans
 * Umbrella-off: <baseDir>/plans  (legacy, byte-identical)
 */
function getPlansPath(baseDir, config) {
  const umbrellaRoot = resolveUmbrellaRoot(config, baseDir);
  if (umbrellaRoot) {
    return path.join(umbrellaRoot, stripTrailing(config.paths?.plans) || 'plans');
  }
  // Legacy: second arg was pathsConfig in P2 — accept both shapes
  const pathsConfig = config?.paths ? config.paths : config;
  return path.join(baseDir, stripTrailing(pathsConfig?.plans) || 'plans');
}

/**
 * Docs path is ALWAYS repo-root (CWD) anchored — never moves under umbrella.
 */
function getDocsPath(baseDir, config) {
  const pathsConfig = config?.paths ? config.paths : config;
  return path.join(baseDir, stripTrailing(pathsConfig?.docs) || 'docs');
}

function getVisualsPath(baseDir, config) {
  const umbrellaRoot = resolveUmbrellaRoot(config, baseDir);
  const name = stripTrailing(config?.paths?.visuals) || 'visuals';
  return umbrellaRoot
    ? path.join(umbrellaRoot, name)
    : path.join(baseDir, 'plans', name); // legacy fallback mirrors plans/visuals
}

function getJournalsPath(baseDir, config) {
  const umbrellaRoot = resolveUmbrellaRoot(config, baseDir);
  const name = stripTrailing(config?.paths?.journals) || 'journals';
  return umbrellaRoot
    ? path.join(umbrellaRoot, name)
    : path.join(baseDir, 'plans', name); // legacy fallback: plans/journals
}

function getStatePath(baseDir, config) {
  const umbrellaRoot = resolveUmbrellaRoot(config, baseDir);
  const name = stripTrailing(config?.paths?.state) || 'state';
  return umbrellaRoot
    ? path.join(umbrellaRoot, name)
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
function getReportsPath(planPath, resolvedBy, planConfig, pathsConfig, anchor, config) {
  const subdir = stripTrailing(planConfig?.reportsDir) || 'reports';

  // Session-active plan overrides everything
  const activePlan = (planPath && resolvedBy === 'session') ? stripTrailing(planPath) : null;

  let reportsBase;
  if (activePlan) {
    reportsBase = activePlan;
  } else if (config) {
    const umbrellaRoot = resolveUmbrellaRoot(config, anchor || process.cwd());
    if (umbrellaRoot) {
      // Umbrella: reports is a direct sibling of plans under the umbrella root.
      // Return early — no subdir nesting needed, the subdir IS the leaf.
      const reportsLeaf = subdir; // 'reports' by default
      if (!anchor) return `${umbrellaRoot}/${reportsLeaf}/`;
      return path.join(umbrellaRoot, reportsLeaf);
    }
    reportsBase = stripTrailing(pathsConfig?.plans) || 'plans';
  } else {
    reportsBase = stripTrailing(pathsConfig?.plans) || 'plans';
  }

  if (!anchor) {
    // Relative mode: trailing slash
    return `${reportsBase}/${subdir}/`;
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
function resolvePlanPath(sessionId, config, readState) {
  const plansDir = stripTrailing(config?.paths?.plans) || 'plans';
  const resolution = config?.plan?.resolution || {};
  const order = resolution.order || ['session', 'branch'];

  for (const step of order) {
    if (step === 'session') {
      const state = readState ? readState(sessionId) : null;
      if (state?.activePlan) {
        let resolved = state.activePlan;
        if (!path.isAbsolute(resolved) && state.sessionOrigin) {
          resolved = path.join(state.sessionOrigin, resolved);
        }
        return { path: resolved, resolvedBy: 'session' };
      }
    } else if (step === 'branch') {
      try {
        const branch = getGitBranch();
        const slug = slugFromBranch(branch, resolution.branchPattern);
        if (slug && fs.existsSync(plansDir)) {
          const matches = fs.readdirSync(plansDir, { withFileTypes: true })
            .filter(e => e.isDirectory() && e.name.includes(slug));
          if (matches.length > 0) {
            return {
              path: path.join(plansDir, matches[matches.length - 1].name),
              resolvedBy: 'branch'
            };
          }
        }
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
  slugFromBranch,
  extractIssueFromBranch,
  resolveUmbrellaRoot
};
