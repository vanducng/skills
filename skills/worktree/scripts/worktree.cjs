#!/usr/bin/env node
/**
 * Git Worktree Manager
 * Cross-platform Node.js script for creating isolated git worktrees.
 * Runtime-agnostic: works with Claude Code, Codex CLI, or plain shell.
 *
 * Usage: node worktree.cjs <command> [options]
 * Commands:
 *   create <project> <feature>  Create a new worktree (project optional for standalone)
 *   remove <name-or-path>       Remove a worktree and its branch (runs pre-remove hook)
 *   info                        Get repo info (type, projects, env files)
 *   list                        List existing worktrees
 *   status                      Show worktree health and branch status
 *   clean                       Bulk-remove merged/stale worktrees + prune metadata to free disk (dry-run; --yes to execute)
 *   repair                      Relocate worktrees nested inside another worktree to the main root + fix admin links (dry-run; --yes to execute)
 *   ports                       Show per-worktree port block assignments
 *
 * Options:
 *   --prefix <type>        Branch prefix (feat|fix|refactor|docs|test|chore|perf)
 *   --base <branch>        Override auto-detected base branch (default: dev→develop→main→master)
 *   --checkout-submodules  Initialize submodules in the new worktree after create
 *   --worktree-root <path> Explicit worktree directory (default: <git-root>/.worktrees)
 *   --json                 Output in JSON format for LLM consumption
 *   --env <files>          Comma-separated list of .env files to copy (legacy)
 *   --no-copy-env          Skip auto-copy of untracked .env* files
 *   --no-enter             Don't switch the agent session into the new worktree (default: enter)
 *   --no-pre-remove-hook   Skip .worktree/hooks/pre-remove on remove
 *   --dry-run              Show what would be done without executing
 *   --no-prefix            Skip branch prefix and preserve original case
 */

const { execSync, execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

function sanitizeBranchPrefix(value) {
  const raw = String(value || '').trim().toLowerCase();
  if (!raw) return 'feat';
  const safe = raw
    .replace(/[^a-z0-9-]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 20);
  return safe || 'feat';
}

function extractIssueKey(value) {
  const raw = String(value || '').trim();
  if (!raw) return null;

  const urlMatch = raw.match(/(?:browse\/|issues?\/|ticket\/)([A-Z][A-Z0-9]+-\d+)\b/i);
  if (urlMatch) return urlMatch[1].toUpperCase();

  const keyMatch = raw.match(/\b([A-Z][A-Z0-9]+-\d+)\b/i);
  if (!keyMatch) return null;

  return keyMatch[1].toUpperCase();
}

function shouldUseIssueKeyAsBranchName(rawFeature, issueKey) {
  if (!issueKey) return false;
  const raw = String(rawFeature || '').trim();
  if (!raw) return false;

  if (raw.toUpperCase() === issueKey) return true;
  if (/https?:\/\//i.test(raw)) return true;
  if (/\s/.test(raw)) return true;

  return false;
}

function isSafeEnvFileName(fileName) {
  if (!fileName || typeof fileName !== 'string') return false;
  if (fileName.includes('\0')) return false;
  if (path.isAbsolute(fileName)) return false;
  const normalized = path.normalize(fileName.trim());
  if (normalized.startsWith('..') || normalized.includes(`..${path.sep}`)) return false;
  if (normalized.includes(path.sep)) return false;
  return /^\.env[\w.-]*$/.test(normalized);
}

// Sanitize and validate base branch name to prevent command injection
// Returns null if invalid (caller should fall back to auto-detection or error)
function sanitizeBaseBranch(value) {
  if (!value || typeof value !== 'string') return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  // Reject values that look like flags (start with -)
  if (trimmed.startsWith('-')) return { error: 'LOOKS_LIKE_FLAG', value: trimmed };
  // Reject shell metacharacters that could enable command injection
  if (/[;|&$`()\n\r\0\\'"<>]/.test(trimmed)) return { error: 'SHELL_CHARS', value: trimmed };
  // Allow valid git ref characters: alphanumeric, dash, underscore, slash, dot, tilde, caret, at, colon
  // This covers: branch names, remote refs (origin/main), HEAD~N, HEAD^, tags, etc.
  if (!/^[a-zA-Z0-9_./:~^@-]+$/.test(trimmed)) return { error: 'INVALID_CHARS', value: trimmed };
  return trimmed;
}

// Minimum Node.js version check
const MIN_NODE_VERSION = 18;
const nodeVersion = parseInt(process.version.slice(1).split('.')[0], 10);
if (nodeVersion < MIN_NODE_VERSION) {
  outputError('NODE_VERSION_ERROR', `Node.js ${MIN_NODE_VERSION}+ required. Current: ${process.version}`);
  process.exit(1);
}

// Parse arguments
const args = process.argv.slice(2);
const jsonOutput = args.includes('--json');
const jsonIndex = args.indexOf('--json');
if (jsonIndex > -1) args.splice(jsonIndex, 1);

const prefixIndex = args.indexOf('--prefix');
let branchPrefix = 'feat';
let branchPrefixWarning = null;
if (prefixIndex > -1) {
  const rawPrefix = args[prefixIndex + 1] || 'feat';
  branchPrefix = sanitizeBranchPrefix(rawPrefix);
  if (branchPrefix !== rawPrefix.toLowerCase()) {
    branchPrefixWarning = `Branch prefix sanitized: "${rawPrefix}" → "${branchPrefix}"`;
  }
  args.splice(prefixIndex, 2);
}

const envIndex = args.indexOf('--env');
let envFilesToCopy = [];
if (envIndex > -1) {
  envFilesToCopy = (args[envIndex + 1] || '').split(',').map(v => v.trim()).filter(Boolean);
  args.splice(envIndex, 2);
}

const dryRunIndex = args.indexOf('--dry-run');
const dryRun = dryRunIndex > -1;
if (dryRunIndex > -1) args.splice(dryRunIndex, 1);

// --no-prefix: skip branch prefix and preserve original case in feature name
const noPrefixIndex = args.indexOf('--no-prefix');
const noPrefix = noPrefixIndex > -1;
if (noPrefixIndex > -1) args.splice(noPrefixIndex, 1);

// --worktree-root: explicit override for worktree location (Claude's decision)
const worktreeRootIndex = args.indexOf('--worktree-root');
let explicitWorktreeRoot = null;
if (worktreeRootIndex > -1) {
  explicitWorktreeRoot = args[worktreeRootIndex + 1];
  args.splice(worktreeRootIndex, 2);
}

// --base: explicit override for base branch (skip auto-detection)
const baseIndex = args.indexOf('--base');
let explicitBase = null;
let explicitBaseError = null;
if (baseIndex > -1) {
  const rawBase = args[baseIndex + 1];
  const sanitized = sanitizeBaseBranch(rawBase);
  if (sanitized && typeof sanitized === 'object' && sanitized.error) {
    // Store error for later - will be reported during cmdCreate
    explicitBaseError = sanitized;
  } else {
    explicitBase = sanitized; // null if empty/invalid, string if valid
  }
  args.splice(baseIndex, 2);
}

const checkoutSubmodulesIndex = args.indexOf('--checkout-submodules');
const checkoutSubmodules = checkoutSubmodulesIndex > -1;
if (checkoutSubmodulesIndex > -1) args.splice(checkoutSubmodulesIndex, 1);

// --post-create-hook <path|command>: run after worktree creation in the new
// worktree dir. If absent, auto-detect (.worktree/hooks/post-create or
// scripts/setup-worktree). Use --no-post-create-hook to disable detection.
const postCreateHookIndex = args.indexOf('--post-create-hook');
let postCreateHook = null;
if (postCreateHookIndex > -1) {
  postCreateHook = args[postCreateHookIndex + 1];
  args.splice(postCreateHookIndex, 2);
}
const noPostCreateHookIndex = args.indexOf('--no-post-create-hook');
const noPostCreateHook = noPostCreateHookIndex > -1;
if (noPostCreateHookIndex > -1) args.splice(noPostCreateHookIndex, 1);

// --no-copy-env: skip copying untracked .env* files from the source checkout
const noCopyEnvIndex = args.indexOf('--no-copy-env');
const noCopyEnv = noCopyEnvIndex > -1;
if (noCopyEnvIndex > -1) args.splice(noCopyEnvIndex, 1);

// --no-enter: stay in the current directory instead of switching the agent
// session into the new worktree. Default is to enter (WORKTREE_NO_ENTER=1 also opts out).
const noEnterIndex = args.indexOf('--no-enter');
const noEnter = noEnterIndex > -1 || process.env.WORKTREE_NO_ENTER === '1';
if (noEnterIndex > -1) args.splice(noEnterIndex, 1);

// --no-pre-remove-hook: skip .worktree/hooks/pre-remove on remove
const noPreRemoveHookIndex = args.indexOf('--no-pre-remove-hook');
const noPreRemoveHook = noPreRemoveHookIndex > -1;
if (noPreRemoveHookIndex > -1) args.splice(noPreRemoveHookIndex, 1);

// --yes: confirm a destructive bulk op (clean executes; default is dry-run)
const yesIndex = args.indexOf('--yes');
const confirmYes = yesIndex > -1;
if (yesIndex > -1) args.splice(yesIndex, 1);

// clean scope: --merged (branch merged into base), --stale (gone-from-remote
// or prunable). Neither flag = both. --force includes dirty worktrees.
const cleanMerged = args.includes('--merged');
[args.indexOf('--merged')].filter(i => i > -1).forEach(i => args.splice(i, 1));
const cleanStale = args.includes('--stale');
[args.indexOf('--stale')].filter(i => i > -1).forEach(i => args.splice(i, 1));
const forceIndex = args.indexOf('--force');
const cleanForce = forceIndex > -1;
if (forceIndex > -1) args.splice(forceIndex, 1);

const command = args[0];
// For create: args[1] is project (or feature for standalone), args[2] is feature
// For remove: args[1] is worktree name or path
const arg1 = args[1];
const arg2 = args[2];

// Detect which AI agent runtime is invoking the script so suggested
// next-steps and "open in agent" hints stay accurate.
// Override with WORKTREE_AGENT_CMD=<your-cli> for unknown runtimes.
function detectAgentRuntime() {
  if (process.env.WORKTREE_AGENT_CMD) {
    return { name: 'custom', openCmd: process.env.WORKTREE_AGENT_CMD };
  }
  if (process.env.CLAUDECODE === '1' || (process.env.AI_AGENT || '').startsWith('claude')) {
    return { name: 'claude-code', openCmd: 'claude' };
  }
  if (process.env.CODEX_SANDBOX || process.env.CODEX_HOME || process.env.OPENAI_CODEX) {
    return { name: 'codex', openCmd: 'codex' };
  }
  return { name: 'unknown', openCmd: 'claude  # or: codex' };
}

// After create, the new worktree becomes the working session by default. The
// script can't switch a parent session itself, so it emits a machine-readable
// signal telling the caller HOW: Claude Code switches in-session via the
// EnterWorktree tool; Codex has no in-session cwd switch, so it relaunches
// rooted there (codex --cd) or runs subsequent commands from the worktree.
function buildSessionSwitch(worktreePath, enter) {
  const runtime = detectAgentRuntime();
  const sw = { enter, path: worktreePath, runtime: runtime.name };
  if (!enter) return sw;
  if (runtime.name === 'claude-code') {
    sw.action = `EnterWorktree({ path: "${worktreePath}" })`;
    sw.exit = 'ExitWorktree({ action: "keep" })';
  } else if (runtime.name === 'codex') {
    sw.action = `codex --cd "${worktreePath}"`;
    sw.note = 'Codex has no in-session cwd switch: relaunch rooted at the worktree, or run subsequent commands from it.';
  } else {
    sw.action = `cd "${worktreePath}"`;
  }
  return sw;
}

// Output helpers
function output(data) {
  if (jsonOutput) {
    console.log(JSON.stringify(data, null, 2));
  } else {
    if (data.success) {
      console.log(`\n✅ ${data.message}`);
      if (data.worktreePath) {
        const sw = data.sessionSwitch;
        console.log(`\n📋 Next Steps:`);
        if (sw && sw.enter) {
          console.log(`   → ${sw.action}`);
          if (sw.runtime === 'claude-code') {
            console.log(`     (session switches into the worktree; ${sw.exit} to leave)`);
          } else if (sw.note) {
            console.log(`     (${sw.note})`);
          }
          console.log(`   Then start working. Pass --no-enter to stay in the current dir.`);
        } else {
          const runtime = detectAgentRuntime();
          console.log(`   1. cd ${data.worktreePath}`);
          console.log(`   2. ${runtime.openCmd}`);
          console.log(`   3. Start working on your feature`);
        }
        console.log(`\n🧹 Cleanup when done:`);
        console.log(`   node ${path.relative(process.cwd(), __filename) || __filename} remove ${data.worktreePath}`);
        console.log(`   # or manually:`);
        console.log(`   git worktree remove ${data.worktreePath} && git branch -d ${data.branch}`);
      }
      if (data.envFilesCopied && data.envFilesCopied.length > 0) {
        console.log(`\n📄 Environment files copied:`);
        data.envFilesCopied.forEach(f => console.log(`   ✓ ${f}`));
      }
      if (data.includeCopied && data.includeCopied.length > 0) {
        console.log(`\n📄 .worktreeinclude entries copied:`);
        data.includeCopied.forEach(f => console.log(`   ✓ ${f}`));
      }
      if (data.portBase) {
        console.log(`\n🔌 Ports: ${data.portBase}-${data.portBase + 9} (PORT=${data.portBase}, in ${data.envWorktreeFile})`);
      }
      if (data.suggestedInstalls && data.suggestedInstalls.length > 0) {
        console.log(`\n📦 Install dependencies:`);
        data.suggestedInstalls.forEach(s => console.log(`   ${s.dir === '.' ? '' : `cd ${s.dir} && `}${s.command}`));
      }
      if (data.envBackup) {
        console.log(`\n💾 Env files backed up: ${data.envBackup.dir}`);
      }
      if (data.warnings && data.warnings.length > 0) {
        console.log(`\n⚠️  Warnings:`);
        data.warnings.forEach(w => console.log(`   ${w}`));
      }
    } else if (data.info) {
      // Info output
      console.log(`\n📦 Repository Info:`);
      console.log(`   Type: ${data.repoType}`);
      console.log(`   Base branch: ${data.baseBranch}`);
      if (data.worktreeRoot) {
        console.log(`\n📂 Worktree location:`);
        console.log(`   Path: ${data.worktreeRoot}`);
        console.log(`   Source: ${data.worktreeRootSource}`);
      }
      if (data.projects && data.projects.length > 0) {
        console.log(`\n📁 Available projects:`);
        data.projects.forEach(p => console.log(`   - ${p.name} (${p.path})`));
      }
      if (data.envFiles && data.envFiles.length > 0) {
        console.log(`\n🔐 Environment files found:`);
        data.envFiles.forEach(f => console.log(`   - ${f}`));
      }
      if (data.dirtyState) {
        console.log(`\n⚠️  Working directory has uncommitted changes`);
      }
    }
  }
}

// Structured exit codes - lets Codex / shell loops distinguish retry-able from fatal.
// Mapping is conservative (GNU-ish): 2 = bad input, 10–17 = git/state, 13 = perms,
// 28 = disk, 68 = network. Anything unrecognised → 1.
const EXIT_CODES = {
  OK: 0,
  FATAL_ARG: 2,            // bad CLI input - don't retry
  ERROR_GIT: 10,           // git command failed - may be transient
  ERROR_CONFLICT: 17,      // worktree/branch already exists
  ERROR_PERM: 13,          // permission denied
  ERROR_DISK: 28,          // disk / mkdir failed
  ERROR_NET: 68,           // network (fetch) failed
  ERROR_RUNTIME: 70,       // node version, internal error
  ERROR_HOOK: 75,          // post-create hook failed
};

const ERROR_CODE_MAP = {
  MISSING_ARGS: 'FATAL_ARG',
  MISSING_FEATURE: 'FATAL_ARG',
  MISSING_WORKTREE: 'FATAL_ARG',
  UNKNOWN_COMMAND: 'FATAL_ARG',
  INVALID_FEATURE_NAME: 'FATAL_ARG',
  INVALID_BASE_BRANCH: 'FATAL_ARG',
  INVALID_WORKTREE_ROOT: 'FATAL_ARG',
  BASE_BRANCH_NOT_FOUND: 'FATAL_ARG',
  PROJECT_NOT_FOUND: 'FATAL_ARG',
  PROJECT_DIR_NOT_FOUND: 'FATAL_ARG',
  MULTIPLE_PROJECTS_MATCH: 'FATAL_ARG',
  MULTIPLE_WORKTREES_MATCH: 'FATAL_ARG',
  NOT_GIT_REPO: 'FATAL_ARG',
  WORKTREE_NOT_FOUND: 'FATAL_ARG',
  NODE_VERSION_ERROR: 'ERROR_RUNTIME',
  GIT_VERSION_ERROR: 'ERROR_RUNTIME',
  WORKTREE_EXISTS: 'ERROR_CONFLICT',
  BRANCH_CHECKED_OUT: 'ERROR_CONFLICT',
  WORKTREE_CREATE_FAILED: 'ERROR_GIT',
  BRANCH_MISMATCH: 'ERROR_GIT',
  WORKTREE_LIST_ERROR: 'ERROR_GIT',
  WORKTREE_REMOVE_FAILED: 'ERROR_GIT',
  WORKTREE_PRUNE_FAILED: 'ERROR_GIT',
  SUBMODULE_CHECKOUT_FAILED: 'ERROR_GIT',
  MKDIR_FAILED: 'ERROR_DISK',
  FETCH_FAILED: 'ERROR_NET',
  POST_CREATE_HOOK_FAILED: 'ERROR_HOOK',
};

function exitCodeFor(errorCode) {
  const category = ERROR_CODE_MAP[errorCode];
  if (category && EXIT_CODES[category] !== undefined) return EXIT_CODES[category];
  return 1;
}

function outputError(code, message, details = {}) {
  const exitCode = exitCodeFor(code);
  const errorData = {
    success: false,
    error: { code, message, exitCode, ...details }
  };
  if (jsonOutput) {
    console.log(JSON.stringify(errorData, null, 2));
  } else {
    console.error(`\n❌ Error [${code}:${exitCode}]: ${message}`);
    if (details.suggestion) {
      console.error(`   💡 ${details.suggestion}`);
    }
    if (details.availableProjects) {
      console.error(`\n   Available projects:`);
      details.availableProjects.forEach(p => console.error(`     - ${p}`));
    }
  }
  process.exit(exitCode);
}

// Git command wrapper with error handling
function git(command, options = {}) {
  try {
    const result = execSync(`git ${command}`, {
      encoding: 'utf-8',
      stdio: options.silent ? 'pipe' : ['pipe', 'pipe', 'pipe'],
      cwd: options.cwd || process.cwd()
    });
    return { success: true, output: result.trim() };
  } catch (error) {
    return {
      success: false,
      error: error.message,
      stderr: error.stderr?.toString().trim() || '',
      code: error.status
    };
  }
}

// Non-shell git for commands that interpolate disk-derived names - filenames
// found in a cloned repo are attacker-controlled and must never hit a shell.
function gitArgs(argv, options = {}) {
  try {
    const result = execFileSync('git', argv, {
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: options.cwd || process.cwd()
    });
    return { success: true, output: result.trim() };
  } catch (error) {
    return {
      success: false,
      error: error.message,
      stderr: error.stderr?.toString().trim() || '',
      code: error.status
    };
  }
}

// Check if in git repo
function checkGitRepo() {
  const result = git('rev-parse --show-toplevel', { silent: true });
  if (!result.success) {
    outputError('NOT_GIT_REPO', 'Not in a git repository', {
      suggestion: 'Run this command from within a git repository'
    });
  }
  return result.output;
}

// Check git version supports worktree
function checkGitVersion() {
  const result = git('worktree list', { silent: true });
  if (!result.success && result.stderr.includes('not a git command')) {
    outputError('GIT_VERSION_ERROR', 'Git version too old (worktree requires git 2.5+)', {
      suggestion: 'Upgrade git to version 2.5 or newer'
    });
  }
}

// Detect base branch
function detectBaseBranch(cwd) {
  const branches = ['dev', 'develop', 'main', 'master'];
  for (const branch of branches) {
    const local = git(`show-ref --verify --quiet refs/heads/${branch}`, { silent: true, cwd });
    if (local.success) return branch;
    const remote = git(`show-ref --verify --quiet refs/remotes/origin/${branch}`, { silent: true, cwd });
    if (remote.success) return branch;
  }
  return 'main'; // fallback
}

// Find the topmost superproject by walking up the directory tree
// This handles submodules within monorepos - worktrees go to the root monorepo
// Safety limit prevents infinite loops in edge cases (max 10 levels deep)
const MAX_SUPERPROJECT_DEPTH = 10;

function findTopmostSuperproject(gitRoot) {
  let current = gitRoot;
  let topmost = gitRoot;
  let depth = 0;

  // Keep walking up while we find superprojects (with safety limit)
  while (depth < MAX_SUPERPROJECT_DEPTH) {
    const result = git('rev-parse --show-superproject-working-tree', { silent: true, cwd: current });
    if (!result.success || !result.output) {
      break; // No more superprojects above
    }
    topmost = result.output;
    current = result.output;
    depth++;
  }

  return topmost;
}

// Resolve the MAIN worktree (primary checkout) from wherever we're invoked.
// Running `create` from INSIDE a linked worktree would otherwise nest a new
// .worktrees under that worktree, because `git rev-parse --show-toplevel`
// returns the LINKED worktree's path. A linked worktree is detected by its
// per-worktree git dir (.git/worktrees/<name>) differing from the shared
// common dir; the main worktree is the first entry of `worktree list`.
function resolveMainWorktree(currentToplevel) {
  const resolveDir = (out) => {
    if (!out) return null;
    const abs = path.resolve(process.cwd(), out);
    try { return fs.realpathSync(abs); } catch { return abs; }
  };
  const gitDir = git('rev-parse --git-dir', { silent: true });
  const commonDir = git('rev-parse --git-common-dir', { silent: true });
  const linked = gitDir.success && commonDir.success &&
    resolveDir(gitDir.output) !== resolveDir(commonDir.output);
  if (!linked) {
    return { main: currentToplevel, insideLinkedWorktree: false };
  }

  // Inside a linked worktree: the main worktree is the first porcelain entry.
  const list = git('worktree list --porcelain', { silent: true });
  if (list.success) {
    const line = list.output.split('\n').find((l) => l.startsWith('worktree '));
    if (line) {
      const mainPath = line.slice('worktree '.length).trim();
      return {
        main: mainPath,
        insideLinkedWorktree: path.resolve(mainPath) !== path.resolve(currentToplevel),
      };
    }
  }
  // Fallback: the shared common dir is <main>/.git → its parent is the root.
  const common = resolveDir(commonDir.output);
  if (common && path.basename(common) === '.git') {
    return { main: path.dirname(common), insideLinkedWorktree: true };
  }
  return { main: currentToplevel, insideLinkedWorktree: false };
}

// A linked worktree is "nested" when its path lives inside ANOTHER linked
// worktree (not the main repo - .worktrees under main is normal). This is the
// corrupt state that creating from inside a worktree used to produce. Each
// offender carries its canonical home so repair can relocate it.
function detectNestedWorktrees(records, treesRoot) {
  const items = records.map((r) => ({ ...r, abs: path.resolve(r.path) }));
  const nested = [];
  for (const w of items) {
    if (w.isMainWorktree) continue;
    const parent = items.find((other) =>
      !other.isMainWorktree &&
      other.abs !== w.abs &&
      w.abs.startsWith(other.abs + path.sep));
    if (parent) {
      nested.push({
        path: w.path,
        branch: w.branch,
        insideOf: parent.path,
        canonical: path.join(treesRoot, TREES_DIRNAME, path.basename(w.path)),
      });
    }
  }
  return nested;
}

// Validate that a path can be used as worktree root (exists or can be created)
function validateWorktreeRoot(rootPath) {
  if (typeof rootPath !== 'string' || rootPath.trim().length === 0) {
    return { valid: false, error: 'Worktree root path is empty' };
  }
  if (/[\0\r\n]/.test(rootPath)) {
    return { valid: false, error: 'Worktree root contains invalid control characters' };
  }
  const resolved = path.resolve(rootPath);

  // Check if path exists and is a directory
  if (fs.existsSync(resolved)) {
    const stat = fs.statSync(resolved);
    if (!stat.isDirectory()) {
      return { valid: false, error: `Path exists but is not a directory: ${resolved}` };
    }
    return { valid: true, path: resolved };
  }

  // Check if parent directory exists (we can create the worktree dir)
  const parent = path.dirname(resolved);
  if (fs.existsSync(parent)) {
    const parentStat = fs.statSync(parent);
    if (!parentStat.isDirectory()) {
      return { valid: false, error: `Parent path is not a directory: ${parent}` };
    }
    return { valid: true, path: resolved };
  }

  // Parent doesn't exist - check if grandparent exists (allows mkdir -p one level)
  const grandparent = path.dirname(parent);
  if (fs.existsSync(grandparent)) {
    return { valid: true, path: resolved };
  }

  return { valid: false, error: `Cannot create worktree directory: parent path does not exist: ${parent}` };
}

// Standard worktree location: <topmost-git-root>/.worktrees/
// One rule for all repo types - standalone, monorepo, submodule (worktrees
// land at the superproject root). Deliberately a top-level sibling of the
// .workbench artifact umbrella, NOT nested under it: worktrees are full checkouts
// (heavy, contain source), so nesting would pollute artifact globs and bloat
// .workbench. Auto-excluded via .git/info/exclude so worktrees never show as noise.
const TREES_DIRNAME = '.worktrees';

// Determine the worktree root directory with priority:
// 1. Explicit --worktree-root flag (Claude's decision)
// 2. WORKTREE_ROOT env var (explicit override)
// 3. <topmost-git-root>/.worktrees/ (standard location)
function getWorktreeRoot(gitRoot, isMonorepo, explicitRoot = null) {
  // Priority 0: Explicit --worktree-root flag (Claude's decision)
  if (explicitRoot) {
    const validation = validateWorktreeRoot(explicitRoot);
    if (!validation.valid) {
      outputError('INVALID_WORKTREE_ROOT', validation.error, {
        suggestion: 'Provide a valid directory path that exists or can be created'
      });
    }
    return { dir: validation.path, source: '--worktree-root flag' };
  }

  // Priority 1: Environment variable override
  const envRoot = process.env.WORKTREE_ROOT;
  if (envRoot) {
    const validation = validateWorktreeRoot(envRoot);
    if (!validation.valid) {
      outputError('INVALID_WORKTREE_ROOT', validation.error, {
        suggestion: 'Fix WORKTREE_ROOT env var or unset it'
      });
    }
    return { dir: validation.path, source: 'WORKTREE_ROOT env' };
  }

  // Priority 2: .worktrees at the main worktree's topmost root.
  // Resolve a linked worktree → main FIRST so an invocation from inside a
  // worktree never nests .worktrees under that worktree, THEN walk submodule
  // superprojects. Order matters: main-resolution undoes worktree nesting,
  // superproject-resolution undoes submodule nesting.
  const { main, insideLinkedWorktree } = resolveMainWorktree(gitRoot);
  const topmostRoot = findTopmostSuperproject(main);
  const dir = path.join(topmostRoot, TREES_DIRNAME);
  let source = '.worktrees';
  if (insideLinkedWorktree && topmostRoot !== gitRoot) {
    source = `.worktrees (redirected to main worktree ${path.basename(topmostRoot)})`;
  } else if (topmostRoot !== gitRoot) {
    source = `.worktrees (superproject ${path.basename(topmostRoot)})`;
  }
  return { dir, source, treesRoot: topmostRoot, redirectedFromWorktree: insideLinkedWorktree };
}

// Make git ignore a path without touching tracked files: append to
// .git/info/exclude (local-only, shared across worktrees via common dir).
// Best-effort - returns a warning string on failure instead of aborting.
function ensureGitExcluded(repoCwd, line) {
  const check = gitArgs(['check-ignore', '-q', '--', line.replace(/^\//, '').replace(/\/$/, '')], { cwd: repoCwd });
  if (check.success) return { added: false };

  const commonDir = getGitCommonDir(repoCwd);
  if (!commonDir) return { added: false, warning: `Could not resolve git dir to exclude ${line}` };

  try {
    const excludePath = path.join(commonDir, 'info', 'exclude');
    fs.mkdirSync(path.dirname(excludePath), { recursive: true });
    const existing = fs.existsSync(excludePath) ? fs.readFileSync(excludePath, 'utf-8') : '';
    if (existing.split('\n').some(l => l.trim() === line)) return { added: false };
    const prefix = existing && !existing.endsWith('\n') ? '\n' : '';
    fs.appendFileSync(excludePath, `${prefix}${line}\n`);
    return { added: true };
  } catch (err) {
    return { added: false, warning: `Could not update .git/info/exclude for ${line}: ${err.message}` };
  }
}

// Check for uncommitted changes
function checkDirtyState(cwd = process.cwd()) {
  const diff = git('diff --quiet', { silent: true, cwd });
  const diffCached = git('diff --cached --quiet', { silent: true, cwd });
  return !diff.success || !diffCached.success;
}

// Get dirty state details
function getDirtyStateDetails(cwd = process.cwd()) {
  const status = git('status --porcelain', { silent: true, cwd });
  if (!status.success) return null;
  const lines = status.output.split('\n').filter(Boolean);
  const modified = lines.filter(l => l.startsWith(' M') || l.startsWith('M ')).length;
  const staged = lines.filter(l => l.startsWith('A ') || l.startsWith('M ') || l.startsWith('D ')).length;
  const untracked = lines.filter(l => l.startsWith('??')).length;
  return { modified, staged, untracked, total: lines.length };
}

// Parse .gitmodules for monorepo detection
function parseGitModules(gitRoot) {
  const modulesPath = path.join(gitRoot, '.gitmodules');
  if (!fs.existsSync(modulesPath)) return [];

  const content = fs.readFileSync(modulesPath, 'utf-8');
  const projects = [];
  const pathRegex = /path\s*=\s*(.+)/g;
  let match;
  while ((match = pathRegex.exec(content)) !== null) {
    const projectPath = match[1].trim();
    projects.push({
      path: projectPath,
      name: path.basename(projectPath)
    });
  }
  return projects;
}

// Find .env files
function findEnvFiles(dir) {
  try {
    const files = fs.readdirSync(dir);
    return files.filter(f => {
      if (!f.startsWith('.env')) return false;
      const fullPath = path.join(dir, f);
      const stat = fs.statSync(fullPath);
      return stat.isFile() && !stat.isSymbolicLink();
    });
  } catch {
    return [];
  }
}

// Find .env template files (*.example)
function findEnvTemplates(dir) {
  try {
    const files = fs.readdirSync(dir);
    return files.filter(f => {
      if (!f.startsWith('.env') || !f.endsWith('.example')) return false;
      const fullPath = path.join(dir, f);
      const stat = fs.statSync(fullPath);
      return stat.isFile() && !stat.isSymbolicLink();
    });
  } catch {
    return [];
  }
}

// Copy env templates to worktree (strips .example suffix).
// Never clobbers an existing dest - real .env copies win over templates.
function copyEnvTemplates(srcDir, destDir) {
  const templates = findEnvTemplates(srcDir);
  const copied = [];
  const warnings = [];

  templates.forEach(template => {
    const srcPath = path.join(srcDir, template);
    const destName = template.replace(/\.example$/, '');
    const destPath = path.join(destDir, destName);
    if (fs.existsSync(destPath)) return;

    try {
      fs.copyFileSync(srcPath, destPath);
      copied.push({ from: template, to: destName });
    } catch (err) {
      warnings.push(`Failed to copy ${template}: ${err.message}`);
    }
  });

  return { copied, warnings };
}

function isTrackedByGit(file, cwd) {
  return gitArgs(['ls-files', '--error-unmatch', '--', file], { cwd }).success;
}

// Recursive .env* scan, 3 levels deep, covers backend/.env, frontend/.env,
// apps/api/.env. Skips dot-dirs and dependency/build dirs.
const ENV_SCAN_SKIP = new Set([
  'node_modules', 'worktrees', 'vendor', 'venv', 'dist', 'build', 'target', '__pycache__'
]);

function findEnvFilesRecursive(dir, relPrefix = '', depth = 0) {
  const out = [];
  let entries;
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return out; }
  entries.forEach(e => {
    const rel = relPrefix ? `${relPrefix}/${e.name}` : e.name;
    if (e.isDirectory()) {
      if (depth < 2 && !e.name.startsWith('.') && !ENV_SCAN_SKIP.has(e.name)) {
        out.push(...findEnvFilesRecursive(path.join(dir, e.name), rel, depth + 1));
      }
    } else if (e.isFile() && e.name.startsWith('.env') && !e.name.endsWith('.example') && e.name !== ENV_WORKTREE_FILE) {
      out.push(rel);
    }
  });
  return out;
}

// Copy real (untracked, gitignored) .env* files from the source checkout,
// including nested ones. Tracked env files arrive via checkout.
function copyUntrackedEnvFiles(srcDir, destDir) {
  const copied = [];
  const warnings = [];

  findEnvFilesRecursive(srcDir).forEach(rel => {
    if (isTrackedByGit(rel, srcDir)) return;
    try {
      const destPath = path.join(destDir, rel);
      fs.mkdirSync(path.dirname(destPath), { recursive: true });
      fs.copyFileSync(path.join(srcDir, rel), destPath);
      copied.push(rel);
    } catch (err) {
      warnings.push(`Failed to copy ${rel}: ${err.message}`);
    }
  });

  return { copied, warnings };
}

// Detect install commands from lockfiles in the new worktree (root + one
// level of subdirs for backend/frontend splits). One match per language
// group per dir. Returned as suggestions - the caller runs them.
const INSTALL_GROUPS = [
  [['bun.lock', 'bun install'], ['bun.lockb', 'bun install'], ['pnpm-lock.yaml', 'pnpm install'],
   ['yarn.lock', 'yarn install'], ['package-lock.json', 'npm install']],
  [['uv.lock', 'uv sync'], ['poetry.lock', 'poetry install'], ['requirements.txt', 'pip install -r requirements.txt']],
  [['go.mod', 'go mod download']],
  [['Cargo.toml', 'cargo build']],
  [['composer.json', 'composer install']],
];

function detectInstallCommands(dir) {
  const dirsToCheck = ['.'];
  try {
    fs.readdirSync(dir, { withFileTypes: true }).forEach(e => {
      if (e.isDirectory() && !e.name.startsWith('.') && !ENV_SCAN_SKIP.has(e.name) && dirsToCheck.length < 30) {
        dirsToCheck.push(e.name);
      }
    });
  } catch { /* unreadable dir - root-only check */ }

  const found = [];
  dirsToCheck.forEach(sub => {
    const base = path.join(dir, sub);
    INSTALL_GROUPS.forEach(group => {
      for (const [file, command] of group) {
        if (fs.existsSync(path.join(base, file))) {
          found.push({ dir: sub, command });
          break;
        }
      }
    });
  });
  return found;
}

// .worktreeinclude - same convention Claude Code's native worktrees use:
// one repo-relative path per line (file or directory) to copy into each new
// worktree. Lines starting with # are comments. Literal paths only.
function readWorktreeInclude(srcDir) {
  const manifestPath = path.join(srcDir, '.worktreeinclude');
  if (!fs.existsSync(manifestPath)) return [];
  return fs.readFileSync(manifestPath, 'utf-8')
    .split('\n')
    .map(l => l.trim())
    .filter(l => l && !l.startsWith('#'));
}

function copyWorktreeIncludeEntries(srcDir, destDir, entries) {
  const copied = [];
  const warnings = [];
  const resolvedSrc = path.resolve(srcDir);

  entries.forEach(entry => {
    if (path.isAbsolute(entry) || entry.split(/[\\/]/).some(seg => seg === '..')) {
      warnings.push(`Skipped unsafe .worktreeinclude entry: ${entry}`);
      return;
    }
    if (/[*?[\]]/.test(entry)) {
      warnings.push(`Skipped glob .worktreeinclude entry (literal paths only): ${entry}`);
      return;
    }
    const srcPath = path.resolve(resolvedSrc, entry);
    if (!srcPath.startsWith(resolvedSrc + path.sep)) {
      warnings.push(`Skipped .worktreeinclude entry outside repo: ${entry}`);
      return;
    }
    if (!fs.existsSync(srcPath)) return;
    const destPath = path.join(destDir, entry);
    try {
      fs.mkdirSync(path.dirname(destPath), { recursive: true });
      fs.cpSync(srcPath, destPath, { recursive: true, force: false, errorOnExist: false });
      copied.push(entry);
    } catch (err) {
      warnings.push(`Failed to copy ${entry}: ${err.message}`);
    }
  });

  return { copied, warnings };
}

// Per-worktree port block: deterministic hash of the worktree name maps to a
// block of 10 ports in 20000–39990 (below the ephemeral range, clear of
// common dev defaults). Collisions with sibling worktrees probe forward.
const ENV_WORKTREE_FILE = '.env.worktree';
const PORT_BLOCK_SIZE = 10;
const PORT_RANGE_START = 20000;
const PORT_BLOCK_COUNT = 2000;

function hashPortBase(name) {
  const n = crypto.createHash('sha1').update(name).digest().readUInt32BE(0);
  return PORT_RANGE_START + (n % PORT_BLOCK_COUNT) * PORT_BLOCK_SIZE;
}

function parseEnvWorktree(worktreePath) {
  const filePath = path.join(worktreePath, ENV_WORKTREE_FILE);
  if (!fs.existsSync(filePath)) return null;
  const vars = {};
  fs.readFileSync(filePath, 'utf-8').split('\n').forEach(line => {
    const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
    if (m) vars[m[1]] = m[2];
  });
  return vars;
}

function collectAssignedPortBases(worktrees) {
  const bases = new Set();
  worktrees.forEach(w => {
    if (!fs.existsSync(w.path)) return;
    const vars = parseEnvWorktree(w.path);
    const base = vars && Number.parseInt(vars.WORKTREE_PORT_BASE, 10);
    if (Number.isFinite(base)) bases.add(base);
  });
  return bases;
}

function assignPortBase(worktreeName, assignedBases) {
  let base = hashPortBase(worktreeName);
  for (let i = 0; i < PORT_BLOCK_COUNT && assignedBases.has(base); i++) {
    base += PORT_BLOCK_SIZE;
    if (base >= PORT_RANGE_START + PORT_BLOCK_COUNT * PORT_BLOCK_SIZE) base = PORT_RANGE_START;
  }
  return base;
}

// Identifier safe for Postgres/MySQL database names (63-char limit)
function worktreeId(worktreeName) {
  return worktreeName.toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 63);
}

// Values land unquoted in .env.worktree which users `source` - strip
// anything shell-meaningful. worktreeName embeds the repo dir name, which
// is not otherwise sanitized.
function safeEnvValue(value) {
  return String(value).replace(/[^A-Za-z0-9._/-]+/g, '-');
}

function buildWorktreeEnv(worktreeName, branchName, portBase, sourceDir, worktreePath) {
  const composeProject = worktreeName.toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '-')
    .replace(/^[^a-z0-9]+/, '');
  return {
    WORKTREE_NAME: safeEnvValue(worktreeName),
    WORKTREE_BRANCH: safeEnvValue(branchName),
    WORKTREE_ID: worktreeId(worktreeName),
    WORKTREE_PORT_BASE: String(portBase),
    PORT: String(portBase),
    COMPOSE_PROJECT_NAME: composeProject,
    WORKTREE_SOURCE: sourceDir,
    WORKTREE_PATH: worktreePath,
  };
}

function writeEnvWorktreeFile(worktreePath, env) {
  const fileVars = ['WORKTREE_NAME', 'WORKTREE_BRANCH', 'WORKTREE_ID', 'WORKTREE_PORT_BASE', 'PORT', 'COMPOSE_PROJECT_NAME'];
  const lines = [
    '# Generated by the worktree skill - per-worktree identity + a block of 10 ports',
    `# (${env.WORKTREE_PORT_BASE}-${Number(env.WORKTREE_PORT_BASE) + PORT_BLOCK_SIZE - 1}). Load: set -a; . ./${ENV_WORKTREE_FILE}; set +a`,
    ...fileVars.map(k => `${k}=${env[k]}`),
    '',
  ];
  fs.writeFileSync(path.join(worktreePath, ENV_WORKTREE_FILE), lines.join('\n'));
}

// Disk usage of a directory in bytes (du -sk → KiB). Best-effort: null on failure.
function dirSizeBytes(p) {
  if (!fs.existsSync(p)) return null;
  try {
    const out = execFileSync('du', ['-sk', p], { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] });
    const kib = Number.parseInt(out.trim().split(/\s+/)[0], 10);
    return Number.isFinite(kib) ? kib * 1024 : null;
  } catch {
    return null;
  }
}

function humanBytes(bytes) {
  if (!Number.isFinite(bytes)) return 'n/a';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let n = bytes;
  let i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(n < 10 && i > 0 ? 1 : 0)}${units[i]}`;
}

// Branch tip reachable from base = fully merged (covers ff/rebase merges).
function isBranchMerged(branch, base, cwd) {
  if (!branch || !base || branch === base || branch === 'detached' || branch === 'bare') return false;
  return gitArgs(['merge-base', '--is-ancestor', branch, base], { cwd }).success;
}

// Branch had an upstream that no longer exists on the remote → stale.
function isUpstreamGone(branch, cwd) {
  if (!branch || branch === 'detached' || branch === 'bare') return false;
  const res = gitArgs(['for-each-ref', '--format=%(upstream:track)', `refs/heads/${branch}`], { cwd });
  return res.success && res.output.includes('[gone]');
}

// Shared removal: env-backup → pre-remove hook → git worktree remove → branch
// delete. Used by both `remove` (single) and `clean` (bulk). Never throws.
function removeWorktree(worktree, opts = {}) {
  const worktreePath = worktree.path;
  const branchName = worktree.branch;
  const warnings = [];
  const sizeBytes = dirSizeBytes(worktreePath);

  let envBackup = null;
  if (!opts.noBackup && fs.existsSync(worktreePath)) {
    const envFiles = findEnvFilesRecursive(worktreePath).filter(rel => !isTrackedByGit(rel, worktreePath));
    if (envFiles.length > 0) {
      const backupDir = path.join(path.dirname(worktreePath), '.env-backups', path.basename(worktreePath));
      try {
        envFiles.forEach(rel => {
          const dest = path.join(backupDir, rel);
          fs.mkdirSync(path.dirname(dest), { recursive: true });
          fs.copyFileSync(path.join(worktreePath, rel), dest);
        });
        envBackup = { dir: backupDir, files: envFiles };
      } catch (err) {
        warnings.push(`Env backup failed: ${err.message}`);
      }
    }
  }

  if (!opts.noPreRemoveHook && fs.existsSync(worktreePath)) {
    const preRemove = runPreRemoveHook(worktreePath);
    if (preRemove && preRemove.warning) warnings.push(preRemove.warning);
  }

  const removeResult = git(`worktree remove "${worktreePath}" --force`, { silent: true });
  if (!removeResult.success) {
    return { success: false, worktreePath, branch: branchName, sizeBytes, envBackup, warnings, error: removeResult.stderr || removeResult.error };
  }

  let branchDeleted = false;
  if (branchName && branchName !== 'detached' && branchName !== 'bare') {
    const deleteResult = git(`branch -d "${branchName}"`, { silent: true });
    if (deleteResult.success) {
      branchDeleted = true;
    } else if (opts.forceBranchDelete) {
      branchDeleted = git(`branch -D "${branchName}"`, { silent: true }).success;
    } else {
      warnings.push(`Branch kept: ${branchName} (${deleteResult.stderr || 'not fully merged'})`);
    }
  }

  return { success: true, worktreePath, branch: branchName, sizeBytes, envBackup, branchDeleted, warnings };
}

// Find matching projects
function findMatchingProjects(projects, query) {
  const queryLower = query.toLowerCase();
  return projects.filter(p =>
    p.name.toLowerCase().includes(queryLower) ||
    p.path.toLowerCase().includes(queryLower)
  );
}

// Check if branch is already checked out
function isBranchCheckedOut(branchName, cwd) {
  const result = git('worktree list --porcelain', { silent: true, cwd });
  if (!result.success) return false;
  return result.output.includes(`branch refs/heads/${branchName}`);
}

// Check if branch exists
function branchExists(branchName, cwd) {
  const local = git(`show-ref --verify --quiet refs/heads/${branchName}`, { silent: true, cwd });
  if (local.success) return 'local';
  const remote = git(`show-ref --verify --quiet refs/remotes/origin/${branchName}`, { silent: true, cwd });
  if (remote.success) return 'remote';
  return false;
}

function getGitCommonDir(cwd) {
  const result = git('rev-parse --git-common-dir', { silent: true, cwd });
  if (!result.success || !result.output) return null;
  return path.resolve(cwd, result.output);
}

function getMainWorktreePath(gitRoot, cwd) {
  const gitCommonDir = getGitCommonDir(cwd);
  if (!gitCommonDir) return gitRoot;

  const configResult = git(`config --file "${gitCommonDir}/config" --get core.worktree`, {
    silent: true,
    cwd
  });
  if (!configResult.success || !configResult.output) return gitRoot;

  return path.resolve(gitCommonDir, configResult.output);
}

function parseWorktreeListPorcelain(output, options = {}) {
  const gitCommonDir = options.gitCommonDir ? path.resolve(options.gitCommonDir) : null;
  const mainWorktreePath = options.mainWorktreePath ? path.resolve(options.mainWorktreePath) : null;
  const worktrees = [];
  let current = null;

  output.split('\n').map(line => line.replace(/\r$/, '')).forEach(line => {
    if (!line) {
      if (current && current.path) {
        worktrees.push(current);
      }
      current = null;
      return;
    }

    if (line.startsWith('worktree ')) {
      if (current && current.path) {
        worktrees.push(current);
      }
      current = {
        adminPath: line.slice('worktree '.length),
        path: line.slice('worktree '.length),
        commit: null,
        branch: 'detached',
        bare: false,
        detached: false,
        locked: false,
        prunable: false
      };
      return;
    }

    if (!current) return;

    if (line.startsWith('HEAD ')) {
      current.commit = line.slice('HEAD '.length);
      return;
    }
    if (line.startsWith('branch ')) {
      current.branch = line.replace('branch refs/heads/', '');
      return;
    }
    if (line === 'bare') {
      current.bare = true;
      current.branch = 'bare';
      return;
    }
    if (line === 'detached') {
      current.detached = true;
      current.branch = 'detached';
      return;
    }
    if (line.startsWith('locked')) {
      current.locked = true;
      current.lockReason = line.slice('locked'.length).trim() || null;
      return;
    }
    if (line.startsWith('prunable')) {
      current.prunable = true;
      current.prunableReason = line.slice('prunable'.length).trim() || null;
    }
  });

  if (current && current.path) {
    worktrees.push(current);
  }

  return worktrees.map(worktree => {
    const normalizedAdminPath = path.resolve(worktree.adminPath);
    const normalizedPath = gitCommonDir && mainWorktreePath && normalizedAdminPath === gitCommonDir
      ? mainWorktreePath
      : path.resolve(worktree.path);
    return {
      ...worktree,
      path: normalizedPath,
      isMainWorktree: mainWorktreePath ? normalizedPath === mainWorktreePath : false
    };
  });
}

function getWorktreeRecords(gitRoot, cwd) {
  const result = git('worktree list --porcelain', { silent: true, cwd });
  if (!result.success) {
    outputError('WORKTREE_LIST_ERROR', 'Failed to list worktrees', {
      suggestion: 'Ensure you are in a git repository'
    });
  }

  return parseWorktreeListPorcelain(result.output, {
    gitCommonDir: getGitCommonDir(cwd),
    mainWorktreePath: getMainWorktreePath(gitRoot, cwd)
  });
}

function getAheadBehind(branchName, baseBranch, cwd) {
  if (!branchName || !baseBranch || branchName === 'detached' || branchName === 'bare') {
    return { ahead: 0, behind: 0 };
  }

  const result = git(`rev-list --left-right --count "${branchName}...${baseBranch}"`, { silent: true, cwd });
  if (!result.success || !result.output) {
    return { ahead: 0, behind: 0 };
  }

  const [ahead, behind] = result.output.trim().split(/\s+/).map(value => Number.parseInt(value, 10));
  return {
    ahead: Number.isFinite(ahead) ? ahead : 0,
    behind: Number.isFinite(behind) ? behind : 0
  };
}

// Sanitize feature name to valid branch name
function sanitizeFeatureName(name, preserveCase = false) {
  const raw = String(name || '').trim();
  if (!raw) return '';

  // Keep ASCII branch names; drop diacritics first for better readability.
  let ascii = raw
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '');

  // When preserveCase is true (--no-prefix), keep original casing
  if (!preserveCase) ascii = ascii.toLowerCase();

  // preserveCase (--no-prefix): preserve `/` for multi-segment branch names (e.g. kai/feat/foo)
  // Security: reject `..` path components to prevent directory traversal
  if (preserveCase && ascii.split('/').some(seg => seg === '..')) {
    return '';
  }

  ascii = ascii
    .replace(preserveCase ? /[^a-zA-Z0-9/.-]/g : /[^a-z0-9-]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');

  if (preserveCase) {
    // Clean up slash sequences: collapse consecutive, trim leading/trailing
    ascii = ascii
      .replace(/\/+/g, '/')
      .replace(/^\/|\/$/g, '');
    // Remove dashes adjacent to slashes (e.g. -/- becomes /)
    ascii = ascii
      .replace(/-?\/-?/g, '/');
  }

  // Multi-segment names need longer limit to accommodate user/type/feature patterns
  ascii = ascii.slice(0, preserveCase ? 80 : 50);

  if (ascii) return ascii;

  // If input had alphanumeric Unicode but collapsed to empty, keep deterministic fallback.
  if (/[\p{L}\p{N}]/u.test(raw)) {
    const hash = crypto.createHash('sha1').update(raw).digest('hex').slice(0, 8);
    return `feature-${hash}`;
  }

  return '';
}

// Flatten branch name segments for filesystem-safe directory naming
function flattenForDirectoryName(branchSegment) {
  return branchSegment.replace(/\//g, '-');
}

// COMMANDS

function cmdInfo() {
  const gitRoot = checkGitRepo();
  checkGitVersion();

  const projects = parseGitModules(gitRoot);
  const isMonorepo = projects.length > 0;
  const baseBranch = detectBaseBranch(gitRoot);
  const dirtyState = checkDirtyState();
  const dirtyDetails = dirtyState ? getDirtyStateDetails() : null;
  const envFiles = findEnvFiles(gitRoot);

  // Get worktree root info (shows where worktrees will be created)
  const worktreeRoot = getWorktreeRoot(gitRoot, isMonorepo);

  // For monorepo, also check each project for env files
  const projectEnvFiles = {};
  if (isMonorepo) {
    projects.forEach(p => {
      const projectDir = path.join(gitRoot, p.path);
      if (fs.existsSync(projectDir)) {
        const files = findEnvFiles(projectDir);
        if (files.length > 0) {
          projectEnvFiles[p.name] = files;
        }
      }
    });
  }

  output({
    info: true,
    repoType: isMonorepo ? 'monorepo' : 'standalone',
    gitRoot,
    baseBranch,
    worktreeRoot: worktreeRoot.dir,
    worktreeRootSource: worktreeRoot.source,
    projects: isMonorepo ? projects : [],
    envFiles,
    projectEnvFiles: isMonorepo ? projectEnvFiles : {},
    dirtyState,
    dirtyDetails
  });
}

function cmdList() {
  const gitRoot = checkGitRepo();
  const worktrees = getWorktreeRecords(gitRoot, gitRoot);

  if (jsonOutput) {
    console.log(JSON.stringify({ success: true, worktrees }, null, 2));
  } else {
    console.log('\n📂 Existing worktrees:');
    worktrees.forEach(w => {
      console.log(`   ${w.path}`);
      console.log(`      Branch: ${w.branch} (${(w.commit || '').slice(0, 7)})`);
    });
  }
}

function cmdStatus() {
  const gitRoot = checkGitRepo();
  checkGitVersion();

  const worktrees = getWorktreeRecords(gitRoot, gitRoot).map(worktree => {
    const existsOnDisk = fs.existsSync(worktree.path);
    const isCurrentWorktree = path.resolve(worktree.path) === path.resolve(gitRoot);
    const branchIsTracked = worktree.branch !== 'detached' && worktree.branch !== 'bare';
    const branchExistsLocally = existsOnDisk && branchIsTracked
      ? branchExists(worktree.branch, worktree.path) === 'local'
      : false;
    const baseBranch = existsOnDisk && !worktree.bare ? detectBaseBranch(worktree.path) : null;
    const dirtyState = existsOnDisk && !worktree.bare ? checkDirtyState(worktree.path) : false;
    const dirtyDetails = dirtyState ? getDirtyStateDetails(worktree.path) : null;
    const divergence = existsOnDisk && branchExistsLocally && baseBranch
      ? getAheadBehind(worktree.branch, baseBranch, worktree.path)
      : { ahead: 0, behind: 0 };
    const merged = existsOnDisk && !worktree.isMainWorktree && baseBranch
      ? isBranchMerged(worktree.branch, baseBranch, worktree.path) : false;
    const sizeBytes = existsOnDisk && !worktree.isMainWorktree ? dirSizeBytes(worktree.path) : null;

    return {
      ...worktree,
      isCurrentWorktree,
      branchExists: branchExistsLocally,
      baseBranch,
      dirtyState,
      dirtyDetails,
      ahead: divergence.ahead,
      behind: divergence.behind,
      merged,
      sizeBytes,
      size: sizeBytes != null ? humanBytes(sizeBytes) : null
    };
  });

  const currentWorktree = worktrees.find(worktree => worktree.isCurrentWorktree) || null;

  // Flag worktrees physically nested inside another linked worktree - the
  // corrupt state an older create-from-inside-a-worktree could produce.
  const treesRoot = getWorktreeRoot(gitRoot, false).treesRoot || gitRoot;
  const nested = detectNestedWorktrees(worktrees, treesRoot);

  if (jsonOutput) {
    console.log(JSON.stringify({
      success: true,
      currentWorktree,
      worktrees,
      nested
    }, null, 2));
    return;
  }

  console.log('\n🩺 Worktree Status');
  if (currentWorktree) {
    console.log(`   Current: ${currentWorktree.path}`);
    console.log(`   Branch: ${currentWorktree.branch}`);
    console.log(`   Base: ${currentWorktree.baseBranch || 'n/a'}`);
    console.log(`   Dirty: ${currentWorktree.dirtyState ? 'yes' : 'no'}`);
    console.log(`   Ahead/Behind: ${currentWorktree.ahead}/${currentWorktree.behind}`);
  }

  console.log('\n📂 Known worktrees:');
  worktrees.forEach(worktree => {
    const flags = [];
    if (worktree.isMainWorktree) flags.push('main');
    if (worktree.isCurrentWorktree) flags.push('current');
    if (worktree.dirtyState) flags.push('dirty');
    if (!worktree.branchExists && worktree.branch !== 'detached' && worktree.branch !== 'bare') flags.push('missing-branch');
    if (worktree.merged) flags.push('merged');
    if (worktree.prunable) flags.push('prunable');
    const suffix = flags.length > 0 ? ` [${flags.join(', ')}]` : '';
    const sizeLabel = worktree.size ? ` (${worktree.size})` : '';
    console.log(`   ${worktree.path}${suffix}`);
    console.log(`      Branch: ${worktree.branch}${sizeLabel}`);
    console.log(`      Base: ${worktree.baseBranch || 'n/a'} | Ahead/Behind: ${worktree.ahead}/${worktree.behind}`);
  });
  const reclaimable = worktrees.filter(w => !w.isMainWorktree && (w.merged || w.prunable) && w.sizeBytes)
    .reduce((sum, w) => sum + w.sizeBytes, 0);
  if (reclaimable > 0) {
    console.log(`\n   💾 ~${humanBytes(reclaimable)} reclaimable via: worktree clean --yes`);
  }
  if (nested.length > 0) {
    console.log(`\n   ⚠️  ${nested.length} nested worktree(s) - created inside another worktree:`);
    nested.forEach(n => console.log(`      ${n.path}\n         inside ${n.insideOf} → should live at ${n.canonical}`));
    console.log(`   Fix: worktree repair --yes  (relocates them to the main root)`);
  }
}

function cmdCreate() {
  const gitRoot = checkGitRepo();
  checkGitVersion();

  const projects = parseGitModules(gitRoot);
  const isMonorepo = projects.length > 0;
  const warnings = [];
  if (branchPrefixWarning) warnings.push(branchPrefixWarning);
  const safeEnvFilesToCopy = [];
  if (envFilesToCopy.length > 0) {
    envFilesToCopy.forEach(envFile => {
      if (!isSafeEnvFileName(envFile)) {
        warnings.push(`Skipped unsafe env file entry: ${envFile}`);
        return;
      }
      if (!safeEnvFilesToCopy.includes(envFile)) {
        safeEnvFilesToCopy.push(envFile);
      }
    });
  }

  // Parse arguments based on repo type
  // Monorepo: create <project> <feature>
  // Standalone: create <feature>
  let project, feature;
  if (isMonorepo) {
    project = arg1;
    feature = arg2;
    if (!project || !feature) {
      outputError('MISSING_ARGS', 'Both project and feature are required for monorepo', {
        suggestion: 'Usage: node worktree.cjs create <project> <feature> --prefix <type>',
        availableProjects: projects.map(p => p.name)
      });
    }
  } else {
    feature = arg1;
    if (!feature) {
      outputError('MISSING_FEATURE', 'Feature name is required', {
        suggestion: 'Usage: node worktree.cjs create <feature> --prefix <type>'
      });
    }
  }

  // Check dirty state
  if (checkDirtyState()) {
    const details = getDirtyStateDetails();
    warnings.push(`Uncommitted changes: ${details.modified} modified, ${details.staged} staged, ${details.untracked} untracked`);
  }

  // Determine working directory
  let workDir = gitRoot;
  let projectPath = '';
  let projectName = '';

  if (isMonorepo) {
    const matches = findMatchingProjects(projects, project);

    if (matches.length === 0) {
      outputError('PROJECT_NOT_FOUND', `Project "${project}" not found`, {
        suggestion: 'Check available projects with: node worktree.cjs info',
        availableProjects: projects.map(p => p.name)
      });
    }

    if (matches.length > 1) {
      outputError('MULTIPLE_PROJECTS_MATCH', `Multiple projects match "${project}"`, {
        suggestion: 'Use AskUserQuestion to let user select one',
        matchingProjects: matches.map(p => ({ name: p.name, path: p.path }))
      });
    }

    projectPath = matches[0].path;
    projectName = matches[0].name;
    workDir = path.join(gitRoot, projectPath);

    if (!fs.existsSync(workDir)) {
      outputError('PROJECT_DIR_NOT_FOUND', `Project directory not found: ${workDir}`, {
        suggestion: 'Initialize submodules: git submodule update --init'
      });
    }
  }

  // Ticket-driven work (Jira, Linear, etc.) should keep the ticket key as the
  // branch name when the caller passes a ticket key/URL or natural-language
  // ticket task. Exact branch names like "ABC-123-some-slug" remain opt-in via
  // --no-prefix so established team branch conventions are still possible.
  const issueKey = extractIssueKey(feature);
  const useIssueKeyAsBranch = !noPrefix && shouldUseIssueKeyAsBranchName(feature, issueKey);
  const featureForBranch = useIssueKeyAsBranch ? issueKey : feature;
  const preserveBranchCase = noPrefix || useIssueKeyAsBranch;

  // Sanitize feature name
  const sanitizedFeature = sanitizeFeatureName(featureForBranch, preserveBranchCase);
  if (!sanitizedFeature) {
    outputError('INVALID_FEATURE_NAME', 'Feature name became empty after sanitization', {
      suggestion: 'Use letters/numbers in feature name (example: "login-validation")'
    });
  }
  const expectedFeature = preserveBranchCase
    ? featureForBranch.replace(/\s+/g, '-')
    : featureForBranch.toLowerCase().replace(/\s+/g, '-');
  if (sanitizedFeature !== expectedFeature) {
    warnings.push(`Feature name sanitized: "${featureForBranch}" → "${sanitizedFeature}"`);
  }
  if (useIssueKeyAsBranch) {
    warnings.push(`Ticket key detected: "${issueKey}" → branch "${sanitizedFeature}"`);
  }

  // Create branch name - --no-prefix and ticket-key mode use sanitized feature as-is
  const branchName = preserveBranchCase ? sanitizedFeature : `${branchPrefix}/${sanitizedFeature}`;

  // Handle --base validation errors
  if (explicitBaseError) {
    const errorMessages = {
      LOOKS_LIKE_FLAG: `Base branch "${explicitBaseError.value}" looks like a flag`,
      SHELL_CHARS: `Base branch "${explicitBaseError.value}" contains invalid shell characters`,
      INVALID_CHARS: `Base branch "${explicitBaseError.value}" contains invalid characters`
    };
    outputError('INVALID_BASE_BRANCH', errorMessages[explicitBaseError.error] || 'Invalid base branch', {
      suggestion: 'Provide a valid branch name (e.g., main, dev, feature/branch-name)'
    });
  }

  // Detect base branch (use explicit --base if provided, otherwise auto-detect)
  const baseBranch = explicitBase || detectBaseBranch(workDir);
  const baseBranchSource = explicitBase ? 'explicit' : 'auto-detected';

  // Validate explicit base branch exists (auto-detected branches are already verified)
  if (explicitBase) {
    const baseExists = branchExists(explicitBase, workDir);
    if (!baseExists) {
      outputError('BASE_BRANCH_NOT_FOUND', `Base branch "${explicitBase}" does not exist`, {
        suggestion: 'Check branch name or use auto-detection by omitting --base',
        availableBranches: ['dev', 'develop', 'main', 'master'].filter(b => branchExists(b, workDir))
      });
    }
  }

  // Check if branch already checked out
  if (isBranchCheckedOut(branchName, workDir)) {
    outputError('BRANCH_CHECKED_OUT', `Branch "${branchName}" is already checked out in another worktree`, {
      suggestion: 'Use a different feature name or remove the existing worktree'
    });
  }

  // Determine worktree path using smart root detection
  // explicitWorktreeRoot comes from --worktree-root flag (Claude's decision)
  const worktreeRoot = getWorktreeRoot(gitRoot, isMonorepo, explicitWorktreeRoot);
  const worktreesDir = worktreeRoot.dir;

  // Invoked from inside a linked worktree: the new worktree was redirected to
  // the main repo's .worktrees (a sibling), NOT nested under the current one.
  // Warn so the user understands why the path isn't where they're standing.
  if (worktreeRoot.redirectedFromWorktree && !explicitWorktreeRoot) {
    warnings.push(
      `Ran from inside a linked worktree - creating the new worktree at the main repo root (${worktreesDir}), not nested under the current one.`
    );
  }

  // Build worktree name: always include repo name for clarity.
  // Use the MAIN worktree's basename (treesRoot), never the current toplevel  - 
  // inside a linked worktree path.basename(gitRoot) would be the worktree's
  // dir name and produce a doubled name like "repo-feat-x-newfeat".
  // Flatten slashes to dashes for filesystem-safe directory names
  const repoName = path.basename(worktreeRoot.treesRoot || gitRoot);
  const flatFeature = flattenForDirectoryName(sanitizedFeature);
  const worktreeName = isMonorepo
    ? `${projectName}-${flatFeature}`
    : `${repoName}-${flatFeature}`;

  const worktreePath = path.join(worktreesDir, worktreeName);

  // Check if worktree already exists
  if (fs.existsSync(worktreePath)) {
    const runtime = detectAgentRuntime();
    outputError('WORKTREE_EXISTS', `Worktree already exists: ${worktreePath}`, {
      suggestion: `To use: cd ${worktreePath} && ${runtime.openCmd}\nTo remove: git worktree remove ${worktreePath}`
    });
  }

  // Check if branch exists
  const branchStatus = branchExists(branchName, workDir);

  // Resolve post-create hook for preview / execution (sourceDir = repo root for hook lookup).
  const sourceDir = isMonorepo ? workDir : gitRoot;
  let plannedHook = null;
  if (!noPostCreateHook) {
    plannedHook = postCreateHook
      ? resolvePostCreateHook(postCreateHook, worktreePath, sourceDir)
      : detectPostCreateHook(sourceDir);
  }

  // Deterministic port block, collision-checked against sibling worktrees
  const assignedBases = collectAssignedPortBases(getWorktreeRecords(gitRoot, workDir));
  const portBase = assignPortBase(worktreeName, assignedBases);

  // Dry-run mode: show what would be done
  if (dryRun) {
    output({
      success: true,
      dryRun: true,
      message: 'Dry run - no changes made',
      wouldCreate: {
        worktreePath,
        worktreeRootSource: worktreeRoot.source,
        branch: branchName,
        baseBranch,
        baseBranchSource,
        checkoutSubmodules,
        branchExists: !!branchStatus,
        project: isMonorepo ? projectName : null,
        portBase,
        envFilesToCopy: safeEnvFilesToCopy.length > 0 ? safeEnvFilesToCopy : undefined,
        worktreeInclude: readWorktreeInclude(sourceDir),
        postCreateHook: plannedHook ? plannedHook.display : null
      },
      warnings: warnings.length > 0 ? warnings : undefined
    });
    return;
  }

  // Create worktrees directory
  try {
    fs.mkdirSync(worktreesDir, { recursive: true });
  } catch (err) {
    outputError('MKDIR_FAILED', `Failed to create worktrees directory: ${worktreesDir}`, {
      suggestion: 'Check write permissions'
    });
  }

  // Fetch remote branch if needed
  if (branchStatus === 'remote') {
    const fetchResult = git(`fetch origin ${branchName}`, { silent: true, cwd: workDir });
    if (!fetchResult.success) {
      outputError('FETCH_FAILED', `Failed to fetch branch from remote: ${branchName}`, {
        suggestion: 'Check network connection and remote repository access'
      });
    }
  }

  // Create worktree
  let createResult;
  if (branchStatus) {
    createResult = git(`worktree add "${worktreePath}" ${branchName}`, { cwd: workDir });
  } else {
    createResult = git(`worktree add -b ${branchName} "${worktreePath}" ${baseBranch}`, { cwd: workDir });
  }

  if (!createResult.success) {
    outputError('WORKTREE_CREATE_FAILED', `Failed to create worktree`, {
      suggestion: createResult.stderr || createResult.error,
      gitError: createResult.stderr
    });
  }

  // Verify the checkout actually landed on the requested branch - guards
  // against silent attach-to-base incidents. Auto-rescue via git switch.
  const actualBranchRes = git('rev-parse --abbrev-ref HEAD', { silent: true, cwd: worktreePath });
  const actualBranch = actualBranchRes.success ? actualBranchRes.output : null;
  if (actualBranch && actualBranch !== branchName) {
    const switchCmd = branchExists(branchName, worktreePath) === 'local'
      ? `switch "${branchName}"`
      : `switch -c "${branchName}"`;
    git(switchCmd, { silent: true, cwd: worktreePath });
    const verify = git('rev-parse --abbrev-ref HEAD', { silent: true, cwd: worktreePath });
    if (!verify.success || verify.output !== branchName) {
      outputError('BRANCH_MISMATCH', `Worktree checked out "${actualBranch}" instead of "${branchName}"`, {
        suggestion: `cd ${worktreePath} && git switch -c ${branchName}`,
        worktreePath
      });
    }
    warnings.push(`Checkout landed on "${actualBranch}"; auto-switched to "${branchName}"`);
  }

  // Warn when branching from a base that is behind its already-fetched remote
  if (!branchStatus && !baseBranch.includes('/')) {
    const localBase = git(`show-ref --verify --quiet refs/heads/${baseBranch}`, { silent: true, cwd: workDir });
    const remoteBase = git(`show-ref --verify --quiet refs/remotes/origin/${baseBranch}`, { silent: true, cwd: workDir });
    if (localBase.success && remoteBase.success) {
      const behindRes = git(`rev-list --count ${baseBranch}..origin/${baseBranch}`, { silent: true, cwd: workDir });
      const behind = Number.parseInt(behindRes.output, 10);
      if (behindRes.success && Number.isFinite(behind) && behind > 0) {
        warnings.push(`Base "${baseBranch}" is ${behind} commit(s) behind origin/${baseBranch} - stale base. Fetch first, or recreate with --base origin/${baseBranch}.`);
      }
    }
  }

  // Env propagation order: real untracked .env* files win, templates fill
  // gaps, explicit --env entries and .worktreeinclude add the rest.
  const envFilesCopied = [];
  if (!noCopyEnv) {
    const untracked = copyUntrackedEnvFiles(sourceDir, worktreePath);
    untracked.copied.forEach(f => envFilesCopied.push(f));
    untracked.warnings.forEach(w => warnings.push(w));
  }

  const envResult = copyEnvTemplates(sourceDir, worktreePath);
  envResult.warnings.forEach(w => warnings.push(w));
  envResult.copied.forEach(c => {
    if (!envFilesCopied.includes(c.to)) envFilesCopied.push(c.to);
  });

  if (safeEnvFilesToCopy.length > 0) {
    safeEnvFilesToCopy.forEach(envFile => {
      const sourcePath = path.join(sourceDir, envFile);
      const destPath = path.join(worktreePath, envFile);
      if (fs.existsSync(sourcePath)) {
        try {
          fs.copyFileSync(sourcePath, destPath);
          if (!envFilesCopied.includes(envFile)) {
            envFilesCopied.push(envFile);
          }
        } catch (err) {
          warnings.push(`Failed to copy ${envFile}: ${err.message}`);
        }
      } else {
        warnings.push(`Env file not found: ${envFile}`);
      }
    });
  }

  const includeEntries = readWorktreeInclude(sourceDir);
  const includeResult = copyWorktreeIncludeEntries(sourceDir, worktreePath, includeEntries);
  includeResult.warnings.forEach(w => warnings.push(w));

  // Per-worktree identity + port block
  const worktreeEnv = buildWorktreeEnv(worktreeName, branchName, portBase, sourceDir, worktreePath);
  try {
    writeEnvWorktreeFile(worktreePath, worktreeEnv);
  } catch (err) {
    warnings.push(`Failed to write ${ENV_WORKTREE_FILE}: ${err.message}`);
  }

  // Keep git status clean: exclude the trees dir (in the repo that contains
  // it) and the generated .env.worktree (in the repo owning the worktree).
  const treesRoot = worktreeRoot.treesRoot;
  if (treesRoot && worktreesDir.startsWith(treesRoot + path.sep)) {
    const rel = path.relative(treesRoot, worktreesDir).split(path.sep).join('/');
    const result = ensureGitExcluded(treesRoot, `/${rel}/`);
    if (result.warning) warnings.push(result.warning);
  }
  const envExclude = ensureGitExcluded(workDir, ENV_WORKTREE_FILE);
  if (envExclude.warning) warnings.push(envExclude.warning);

  if (checkoutSubmodules) {
    const submoduleResult = git('submodule update --init --checkout --recursive', {
      silent: true,
      cwd: worktreePath
    });
    if (!submoduleResult.success) {
      outputError('SUBMODULE_CHECKOUT_FAILED', 'Worktree created but submodule checkout failed', {
        suggestion: submoduleResult.stderr || submoduleResult.error || 'Inspect the new worktree and run git submodule update manually',
        worktreePath
      });
    }
  }

  // Resolve & run post-create hook (explicit flag wins; otherwise auto-detect).
  let hookResult = null;
  if (!noPostCreateHook) {
    const resolvedHook = postCreateHook
      ? resolvePostCreateHook(postCreateHook, worktreePath, sourceDir)
      : detectPostCreateHook(sourceDir);
    if (resolvedHook) {
      hookResult = runPostCreateHook(resolvedHook, worktreePath, worktreeEnv);
      if (!hookResult.success) {
        outputError('POST_CREATE_HOOK_FAILED', `Post-create hook failed: ${resolvedHook.display}`, {
          suggestion: hookResult.stderr || hookResult.error || 'Inspect the worktree and re-run the hook manually',
          worktreePath,
          hookExitCode: hookResult.code
        });
      }
    }
  }

  output({
    success: true,
    message: 'Worktree created successfully!',
    worktreePath,
    worktreeRootSource: worktreeRoot.source,
    branch: branchName,
    baseBranch,
    baseBranchSource,
    checkoutSubmodules,
    project: isMonorepo ? projectName : null,
    portBase,
    worktreeId: worktreeEnv.WORKTREE_ID,
    envWorktreeFile: ENV_WORKTREE_FILE,
    envFilesCopied,
    envTemplatesCopied: envResult.copied,
    includeCopied: includeResult.copied,
    suggestedInstalls: detectInstallCommands(worktreePath),
    sessionSwitch: buildSessionSwitch(worktreePath, !noEnter),
    postCreateHook: hookResult ? { ran: true, hook: hookResult.display } : { ran: false },
    warnings: warnings.length > 0 ? warnings : undefined
  });
}

// Auto-detect a post-create hook script. Order: `.worktree/hooks/post-create`
// (per-repo team convention) → `scripts/setup-worktree`. No Makefile sniffing  - 
// too magical, easy to false-positive. Hook must be executable.
function detectPostCreateHook(repoRoot) {
  const candidates = [
    path.join(repoRoot, '.worktree', 'hooks', 'post-create'),
    path.join(repoRoot, 'scripts', 'setup-worktree'),
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) {
      try {
        fs.accessSync(c, fs.constants.X_OK);
        return { path: c, display: path.relative(repoRoot, c), explicit: false };
      } catch { /* not executable, skip */ }
    }
  }
  return null;
}

// Resolve an explicit --post-create-hook value. Accepts an absolute path,
// a path relative to the source repo, or a shell command string (must start
// with a known invoker prefix to avoid arbitrary-command surprises).
function resolvePostCreateHook(value, worktreePath, repoRoot) {
  if (!value || typeof value !== 'string') {
    outputError('FATAL_ARG', '--post-create-hook requires a path or command');
  }
  // If looks like a file path, resolve & validate executability.
  if (value.startsWith('/') || value.startsWith('./') || value.startsWith('../') || !value.includes(' ')) {
    const abs = path.isAbsolute(value) ? value : path.resolve(repoRoot, value);
    if (!fs.existsSync(abs)) {
      outputError('FATAL_ARG', `Post-create hook not found: ${abs}`);
    }
    try { fs.accessSync(abs, fs.constants.X_OK); }
    catch { outputError('FATAL_ARG', `Post-create hook not executable: ${abs}`); }
    return { path: abs, display: path.relative(repoRoot, abs) || abs, explicit: true };
  }
  // Otherwise treat as a shell command (e.g. "make worktree-init").
  return { command: value, display: value, explicit: true };
}

function runPostCreateHook(hook, worktreePath, worktreeEnv = {}) {
  try {
    const result = execSync(hook.command ? hook.command : `"${hook.path}"`, {
      cwd: worktreePath,
      stdio: jsonOutput ? 'pipe' : 'inherit',
      env: { ...process.env, ...worktreeEnv, WORKTREE_PATH: worktreePath },
    });
    return { success: true, output: result ? result.toString().trim() : '', display: hook.display };
  } catch (err) {
    return {
      success: false,
      code: err.status,
      stderr: err.stderr ? err.stderr.toString().trim() : '',
      error: err.message,
      display: hook.display,
    };
  }
}

// Pre-remove hook: tear down per-worktree resources (drop DB, compose down)
// before the worktree disappears. Failure warns but never blocks removal.
function runPreRemoveHook(worktreePath) {
  const hookPath = path.join(worktreePath, '.worktree', 'hooks', 'pre-remove');
  if (!fs.existsSync(hookPath)) return null;
  try {
    fs.accessSync(hookPath, fs.constants.X_OK);
  } catch {
    return { ran: false, warning: `Pre-remove hook not executable: ${hookPath}` };
  }

  const vars = parseEnvWorktree(worktreePath) || {};
  try {
    execSync(`"${hookPath}"`, {
      cwd: worktreePath,
      stdio: jsonOutput ? 'pipe' : 'inherit',
      env: { ...process.env, ...vars, WORKTREE_PATH: worktreePath },
    });
    return { ran: true };
  } catch (err) {
    return { ran: true, warning: `Pre-remove hook failed (removal continues): ${err.message}` };
  }
}

function cmdRemove() {
  if (!arg1) {
    outputError('MISSING_WORKTREE', 'Worktree name or path is required', {
      suggestion: 'Usage: node worktree.cjs remove <name-or-path>\nUse "node worktree.cjs list" to see available worktrees'
    });
  }

  const gitRoot = checkGitRepo();
  checkGitVersion();
  const worktrees = getWorktreeRecords(gitRoot, gitRoot);

  // Find matching worktree
  const searchTerm = arg1.toLowerCase();
  const removable = worktrees.filter(w => !w.isMainWorktree);
  const exactMatches = removable.filter(w => {
    const name = path.basename(w.path).toLowerCase();
    const fullPath = w.path.toLowerCase();
    const adminPath = (w.adminPath || '').toLowerCase();
    const branch = (w.branch || '').toLowerCase();
    return name === searchTerm || fullPath === searchTerm || adminPath === searchTerm || branch === searchTerm;
  });
  const prefixMatches = removable.filter(w => {
    const name = path.basename(w.path).toLowerCase();
    const fullPath = w.path.toLowerCase();
    const adminPath = (w.adminPath || '').toLowerCase();
    const branch = (w.branch || '').toLowerCase();
    return name.startsWith(searchTerm) || fullPath.startsWith(searchTerm) || adminPath.startsWith(searchTerm) || branch.startsWith(searchTerm);
  });
  const containsMatches = removable.filter(w => {
    const name = path.basename(w.path).toLowerCase();
    const fullPath = w.path.toLowerCase();
    const adminPath = (w.adminPath || '').toLowerCase();
    const branch = (w.branch || '').toLowerCase();
    return name.includes(searchTerm) || fullPath.includes(searchTerm) || adminPath.includes(searchTerm) || branch.includes(searchTerm);
  });

  let removableMatches = exactMatches;
  if (removableMatches.length === 0) {
    removableMatches = prefixMatches;
  }
  if (removableMatches.length === 0 && searchTerm.length >= 4) {
    removableMatches = containsMatches;
  }

  if (removableMatches.length === 0) {
    outputError('WORKTREE_NOT_FOUND', `No worktree matching "${arg1}" found`, {
      suggestion: 'Use "node worktree.cjs list" to see available worktrees',
      availableWorktrees: removable.map(w => path.basename(w.path))
    });
  }

  if (removableMatches.length > 1) {
    outputError('MULTIPLE_WORKTREES_MATCH', `Multiple worktrees match "${arg1}"`, {
      suggestion: 'Be more specific or use full path',
      matchingWorktrees: removableMatches.map(w => ({ name: path.basename(w.path), path: w.path, branch: w.branch }))
    });
  }

  const worktree = removableMatches[0];
  const worktreePath = worktree.path;
  const branchName = worktree.branch;

  // Dry-run mode
  if (dryRun) {
    output({
      success: true,
      dryRun: true,
      message: 'Dry run - no changes made',
      wouldRemove: {
        worktreePath,
        branch: branchName,
        deleteBranch: !!branchName,
        preRemoveHook: fs.existsSync(path.join(worktreePath, '.worktree', 'hooks', 'pre-remove'))
      }
    });
    return;
  }

  const result = removeWorktree(worktree, { noPreRemoveHook });
  if (!result.success) {
    outputError('WORKTREE_REMOVE_FAILED', `Failed to remove worktree: ${worktreePath}`, {
      suggestion: result.error || 'Check if the worktree has uncommitted changes',
      gitError: result.error
    });
  }

  output({
    success: true,
    message: 'Worktree removed successfully!',
    removedPath: worktreePath,
    branchDeleted: result.branchDeleted ? branchName : null,
    branchKept: !result.branchDeleted && branchName && branchName !== 'detached' ? branchName : null,
    reclaimed: result.sizeBytes ? humanBytes(result.sizeBytes) : null,
    envBackup: result.envBackup,
    warnings: result.warnings.length > 0 ? result.warnings : undefined
  });
}

function cmdClean() {
  const gitRoot = checkGitRepo();
  checkGitVersion();

  // Scope: default to both merged and stale; flags narrow it.
  const wantMerged = cleanMerged || !cleanStale;
  const wantStale = cleanStale || !cleanMerged;

  const records = getWorktreeRecords(gitRoot, gitRoot)
    .filter(w => !w.isMainWorktree && fs.existsSync(w.path));

  const candidates = [];
  const skipped = [];
  records.forEach(w => {
    const base = !w.bare ? detectBaseBranch(w.path) : null;
    const dirty = !w.bare && checkDirtyState(w.path);
    const merged = base ? isBranchMerged(w.branch, base, w.path) : false;
    const stale = w.prunable || isUpstreamGone(w.branch, w.path) ||
      (w.branch !== 'detached' && w.branch !== 'bare' && branchExists(w.branch, w.path) === false);

    const reasons = [];
    if (wantMerged && merged) reasons.push(`merged into ${base}`);
    if (wantStale && stale) reasons.push(w.prunable ? 'prunable' : 'gone from remote');
    if (reasons.length === 0) return;

    if (dirty && !cleanForce) {
      skipped.push({ path: w.path, branch: w.branch, reason: 'dirty (use --force)' });
      return;
    }
    candidates.push({ worktree: w, reasons, dirty, sizeBytes: dirSizeBytes(w.path) });
  });

  const willExecute = confirmYes && !dryRun;
  const totalBytes = candidates.reduce((sum, c) => sum + (c.sizeBytes || 0), 0);
  // Stale admin metadata from worktrees whose dir was deleted manually  - 
  // clean subsumes the old `prune` command by handling these too.
  const stalePrune = (git('worktree prune --dry-run --verbose', { silent: true }).output || '')
    .split('\n').filter(Boolean);

  if (!willExecute) {
    if (jsonOutput) {
      console.log(JSON.stringify({
        success: true,
        dryRun: true,
        message: candidates.length || stalePrune.length ? 'Dry run - pass --yes to remove' : 'Nothing to clean',
        scope: { merged: wantMerged, stale: wantStale, includeDirty: cleanForce },
        candidates: candidates.map(c => ({ path: c.worktree.path, branch: c.worktree.branch, reasons: c.reasons, size: humanBytes(c.sizeBytes), sizeBytes: c.sizeBytes })),
        staleMetadata: stalePrune,
        skipped,
        reclaimable: humanBytes(totalBytes),
        reclaimableBytes: totalBytes
      }, null, 2));
      return;
    }
    console.log(`\n🧹 Worktree Clean (dry run - pass --yes to remove)`);
    console.log(`   Scope: ${[wantMerged && 'merged', wantStale && 'stale'].filter(Boolean).join(' + ')}${cleanForce ? ' + dirty' : ''}`);
    if (candidates.length === 0 && stalePrune.length === 0) {
      console.log('   Nothing to clean.');
    } else {
      candidates.forEach(c => {
        console.log(`   ${c.worktree.branch}  (${humanBytes(c.sizeBytes)})  - ${c.reasons.join(', ')}`);
        console.log(`      ${c.worktree.path}`);
      });
      if (candidates.length) console.log(`\n   Reclaimable: ${humanBytes(totalBytes)} across ${candidates.length} worktree(s)`);
      if (stalePrune.length) console.log(`   Stale metadata to prune: ${stalePrune.length} entr${stalePrune.length === 1 ? 'y' : 'ies'}`);
    }
    skipped.forEach(s => console.log(`   skipped ${s.branch}: ${s.reason}`));
    return;
  }

  // Execute
  const removed = [];
  const failed = [];
  candidates.forEach(c => {
    const res = removeWorktree(c.worktree, { noPreRemoveHook, forceBranchDelete: true });
    if (res.success) removed.push(res); else failed.push(res);
  });
  git('worktree prune', { silent: true });

  const reclaimedBytes = removed.reduce((sum, r) => sum + (r.sizeBytes || 0), 0);
  if (jsonOutput) {
    console.log(JSON.stringify({
      success: true,
      message: `Removed ${removed.length} worktree(s), reclaimed ${humanBytes(reclaimedBytes)}`,
      removed: removed.map(r => ({ path: r.worktreePath, branch: r.branch, size: humanBytes(r.sizeBytes), envBackup: r.envBackup })),
      failed: failed.map(r => ({ path: r.worktreePath, error: r.error })),
      prunedMetadata: stalePrune,
      skipped,
      reclaimed: humanBytes(reclaimedBytes),
      reclaimedBytes
    }, null, 2));
    return;
  }
  console.log(`\n🧹 Worktree Clean`);
  removed.forEach(r => console.log(`   ✓ removed ${r.branch} (${humanBytes(r.sizeBytes)})`));
  failed.forEach(r => console.log(`   ✗ ${r.worktreePath}: ${r.error}`));
  if (stalePrune.length) console.log(`   ✓ pruned ${stalePrune.length} stale metadata entr${stalePrune.length === 1 ? 'y' : 'ies'}`);
  skipped.forEach(s => console.log(`   skipped ${s.branch}: ${s.reason}`));
  console.log(`\n   Reclaimed ${humanBytes(reclaimedBytes)} across ${removed.length} worktree(s).`);
}

// Repair worktree integrity: fix admin gitdir links and relocate any worktree
// that was created nested inside another worktree back to the canonical root.
// Dry-run by default; --yes executes. --force allows moving a dirty worktree.
function cmdRepair() {
  const gitRoot = checkGitRepo();
  checkGitVersion();

  const treesRoot = getWorktreeRoot(gitRoot, false).treesRoot || gitRoot;
  const records = getWorktreeRecords(gitRoot, gitRoot);
  const nested = detectNestedWorktrees(records, treesRoot);

  // Plan a move for each nested worktree; flag blockers (dirty / target taken).
  const plan = nested.map((n) => {
    const dirty = checkDirtyState(n.path);
    let blocker = null;
    if (fs.existsSync(n.canonical)) blocker = `target already exists: ${n.canonical}`;
    else if (dirty && !cleanForce) blocker = 'worktree is dirty (commit/stash, or use --force)';
    return { ...n, dirty, blocker };
  });

  const willExecute = confirmYes && !dryRun;

  if (!willExecute) {
    const message = nested.length
      ? `${nested.length} nested worktree(s) to relocate - pass --yes to repair`
      : 'No nested worktrees; nothing to relocate';
    if (jsonOutput) {
      console.log(JSON.stringify({ success: true, dryRun: true, message, treesRoot, plan }, null, 2));
      return;
    }
    console.log(`\n🔧 Worktree Repair (dry-run)`);
    console.log(`   ${message}`);
    plan.forEach((p) => {
      console.log(`   ${p.blocker ? '✗' : '→'} ${p.path}`);
      console.log(`      inside ${p.insideOf} → ${p.canonical}${p.blocker ? `  [blocked: ${p.blocker}]` : ''}`);
    });
    if (nested.length) console.log(`\n   Run: worktree repair --yes${plan.some(p => p.dirty) ? ' --force' : ''}`);
    return;
  }

  // Always repair admin links first (safe, idempotent) - fixes gitdir pointers
  // left dangling by manual moves so subsequent `git worktree move` succeeds.
  git('worktree repair', { silent: true });

  const moved = [];
  const failed = [];
  for (const p of plan) {
    if (p.blocker && !(p.dirty && cleanForce && !fs.existsSync(p.canonical))) {
      failed.push({ path: p.path, error: p.blocker });
      continue;
    }
    fs.mkdirSync(path.dirname(p.canonical), { recursive: true });
    const moveArgs = ['worktree', 'move'];
    if (cleanForce) moveArgs.push('--force');
    moveArgs.push(p.path, p.canonical);
    const res = gitArgs(moveArgs, { cwd: treesRoot });
    if (res.success) moved.push({ from: p.path, to: p.canonical });
    else failed.push({ path: p.path, error: res.stderr || res.error });
  }
  git('worktree repair', { silent: true });
  git('worktree prune', { silent: true });

  if (jsonOutput) {
    console.log(JSON.stringify({
      success: failed.length === 0,
      message: `Relocated ${moved.length} nested worktree(s)`,
      moved, failed, treesRoot
    }, null, 2));
    return;
  }
  console.log(`\n🔧 Worktree Repair`);
  moved.forEach((m) => console.log(`   ✓ moved ${m.from}\n        → ${m.to}`));
  failed.forEach((f) => console.log(`   ✗ ${f.path}: ${f.error}`));
  console.log(`\n   Relocated ${moved.length} worktree(s); ${failed.length} blocked.`);
}

function cmdPorts() {
  const gitRoot = checkGitRepo();
  checkGitVersion();

  const assignments = getWorktreeRecords(gitRoot, gitRoot).map(worktree => {
    const vars = fs.existsSync(worktree.path) ? parseEnvWorktree(worktree.path) : null;
    const portBase = vars ? Number.parseInt(vars.WORKTREE_PORT_BASE, 10) : null;
    return {
      path: worktree.path,
      branch: worktree.branch,
      isMainWorktree: worktree.isMainWorktree,
      name: vars ? vars.WORKTREE_NAME : path.basename(worktree.path),
      portBase: Number.isFinite(portBase) ? portBase : null,
      portRange: Number.isFinite(portBase) ? `${portBase}-${portBase + PORT_BLOCK_SIZE - 1}` : null
    };
  });

  if (jsonOutput) {
    console.log(JSON.stringify({ success: true, blockSize: PORT_BLOCK_SIZE, assignments }, null, 2));
    return;
  }

  console.log('\n🔌 Worktree port assignments (block of 10 each):');
  assignments.forEach(a => {
    const range = a.portBase ? a.portRange : a.isMainWorktree ? 'default ports (main checkout)' : 'none assigned';
    console.log(`   ${a.branch}  →  ${range}`);
    console.log(`      ${a.path}`);
  });
}

function showHelp() {
  const help = `Git Worktree Manager (runtime-agnostic: Claude Code / Codex / shell)

Usage: node worktree.cjs <command> [options]

Commands:
  create <project> <feature>  Create a new worktree (project optional for standalone)
  remove <name-or-path>       Remove a worktree and its branch (runs pre-remove hook)
  info                        Get repo info (type, projects, env files)
  list                        List existing worktrees
  status                      Inspect worktree health and branch status (with disk usage)
  clean                       Bulk-remove merged/stale worktrees + prune metadata to free disk (dry-run; --yes to execute)
  repair                      Relocate worktrees nested inside another worktree to the main root + fix admin links (dry-run; --yes; --force for dirty)
  ports                       Show per-worktree port block assignments

Clean options:
  --merged                 Only worktrees whose branch is merged into its base
  --stale                  Only worktrees gone from remote / prunable (default: merged + stale)
  --force                  Include dirty worktrees (uncommitted changes)
  --yes                    Actually remove (without it, clean is a dry run)

Options:
  --prefix <type>          Branch prefix (feat|fix|refactor|docs|test|chore|perf)
  --base <branch>          Override auto-detected base branch
  --checkout-submodules    Initialize submodules in the new worktree after create
  --post-create-hook <x>   Explicit post-create script path or command (e.g. "make worktree-init")
  --no-post-create-hook    Disable auto-detection (.worktree/hooks/post-create, scripts/setup-worktree)
  --worktree-root <path>   Explicit worktree directory (default: <git-root>/.worktrees)
  --json                   Output in JSON format for LLM consumption
  --env <files>            Comma-separated list of .env files to copy (legacy)
  --no-copy-env            Skip auto-copy of untracked .env* files from source checkout
  --no-enter               Stay in the current dir; don't switch the session into the worktree
  --no-pre-remove-hook     Skip .worktree/hooks/pre-remove teardown on remove
  --dry-run                Show what would be done without executing
  --no-prefix              Skip branch prefix and preserve original case
  --help, -h               Show this help message

Exit codes:
  0   success
  2   bad CLI input / not a git repo
  10  git command failed (may be transient)
  13  permission denied
  17  worktree or branch already exists
  28  disk / mkdir failed
  68  network (fetch) failed
  70  runtime / node version error
  75  post-create hook failed`;
  console.log(help);
}

// Main
function main() {
  if (command === '--help' || command === '-h' || command === 'help') {
    showHelp();
    return;
  }

  switch (command) {
    case 'create':
      cmdCreate();
      break;
    case 'remove':
      cmdRemove();
      break;
    case 'info':
      cmdInfo();
      break;
    case 'list':
      cmdList();
      break;
    case 'status':
      cmdStatus();
      break;
    case 'clean':
      cmdClean();
      break;
    case 'repair':
      cmdRepair();
      break;
    case 'ports':
      cmdPorts();
      break;
    default:
      outputError('UNKNOWN_COMMAND', `Unknown command: ${command || '(none)'}`, {
        suggestion: 'Available commands: create, remove, info, list, status, clean, repair, ports. Use --help for usage.'
      });
  }
}

main();
