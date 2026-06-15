#!/usr/bin/env node
'use strict';
/**
 * scout-block.cjs - VD-CLI clean-room PreToolUse hook.
 *
 * Blocks reads/searches into heavy/ignored directories (node_modules, .git,
 * dist, build, vendor, etc.). Also blocks overly-broad Glob patterns.
 *
 * Decision JSON: writes to stdout with exit 2 to block; exit 0 to allow.
 * Fail-open: any unexpected error → exit 0 (allow).
 *
 * Config: add a project-local <git-root>/.vdignore or ~/.claude/.vdignore
 *         with gitignore-style patterns to extend the default blocklist.
 *         Prefix a pattern with "!" to un-block (allowlist).
 *
 * No npm runtime deps — all pattern matching is self-contained.
 */

try {
  const fs   = require('fs');
  const path = require('path');
  const os   = require('os');
  const { execFileSync } = require('child_process');

  // ── default blocked directories ──────────────────────────────────────────

  const DEFAULT_BLOCKED = [
    'node_modules',
    '__pycache__',
    '.git',
    'dist',
    'build',
    '.next',
    '.nuxt',
    '.venv',
    'venv',
    'vendor',
    'target',
    'coverage',
    '.cache',
    '.turbo',
    '.parcel-cache',
  ];

  // ── minimal gitignore-style pattern matching ──────────────────────────────
  // Handles: simple dir names, dir/** globs, negation (!).
  // Deliberately minimal — no full gitignore spec needed for our use case.

  /**
   * Convert a simple pattern to a RegExp.
   * Supports: * (one segment), ** (any depth), ? (one char), literal names.
   */
  function patternToRegex(pat) {
    // Escape all special regex chars except * and ?
    let r = pat
      .replace(/[.+^${}()|[\]\\]/g, '\\$&')
      .replace(/\\\*/g, '__STAR__')
      .replace(/\?/g, '[^/]')
      .replace(/__STAR____STAR__/g, '.*')
      .replace(/__STAR__/g, '[^/]*');
    return new RegExp('(^|/)' + r + '(/|$)');
  }

  /**
   * Load and parse a .vdignore-style file.
   * Returns { allowed: RegExp[], blocked: RegExp[] }
   */
  function loadIgnoreFile(filePath) {
    const allowed = [];
    const blocked = [];
    if (!filePath || !fs.existsSync(filePath)) return { allowed, blocked };
    try {
      const lines = fs.readFileSync(filePath, 'utf8').split('\n');
      for (const raw of lines) {
        const line = raw.trim();
        if (!line || line.startsWith('#')) continue;
        if (line.startsWith('!')) {
          const inner = line.slice(1).trim();
          if (inner) allowed.push(patternToRegex(inner));
        } else {
          blocked.push(patternToRegex(line));
        }
      }
    } catch { /* fail-open */ }
    return { allowed, blocked };
  }

  function getGitRoot(cwd) {
    try {
      return execFileSync('git', ['rev-parse', '--show-toplevel'], {
        cwd: cwd || process.cwd(),
        encoding: 'utf8',
        timeout: 2000,
        stdio: ['pipe', 'pipe', 'pipe']
      }).trim() || null;
    } catch { return null; }
  }

  /**
   * Build a combined checker from defaults + optional config files.
   * Priority: allowlist wins over blocklist.
   */
  function buildChecker(cwd) {
    const claudeDir = path.join(os.homedir(), '.claude');
    const globalIgnore  = path.join(claudeDir, '.vdignore');
    const gitRoot = getGitRoot(cwd);
    const localIgnore = gitRoot ? path.join(gitRoot, '.vdignore') : null;

    const globalRules = loadIgnoreFile(globalIgnore);
    const localRules  = localIgnore ? loadIgnoreFile(localIgnore) : { allowed: [], blocked: [] };

    const defaultBlockedRegexes = DEFAULT_BLOCKED.map(name =>
      new RegExp('(^|/)' + name.replace(/[.+^${}()|[\]\\]/g, '\\$&') + '(/|$)')
    );

    const allBlocked = [...defaultBlockedRegexes, ...globalRules.blocked, ...localRules.blocked];
    const allAllowed = [...globalRules.allowed, ...localRules.allowed];

    return { allBlocked, allAllowed };
  }

  /**
   * Test a normalized path string against the checker.
   * Returns { blocked: boolean, pattern: string|null }
   */
  function testPath(checker, normalized) {
    if (!normalized) return { blocked: false, pattern: null };

    // Allowlist wins.
    for (const re of checker.allAllowed) {
      if (re.test(normalized)) return { blocked: false, pattern: null };
    }

    for (const re of checker.allBlocked) {
      if (re.test(normalized)) {
        return { blocked: true, pattern: re.source };
      }
    }
    return { blocked: false, pattern: null };
  }

  // ── path normalization ────────────────────────────────────────────────────

  function normalize(p) {
    if (!p || typeof p !== 'string') return '';
    return p.trim().replace(/\\/g, '/').replace(/^\.\//, '').replace(/^\/+/, '');
  }

  // ── extract paths from tool input ────────────────────────────────────────

  const DIRECT_PATH_KEYS = ['file_path', 'path', 'pattern'];

  // Build tool commands that operate on filesystem paths (not build invocations).
  const FS_CMDS = new Set([
    'cat','head','tail','less','more','ls','cd','rm','cp','mv','find','tree',
    'stat','du','wc','diff','open','code','vim','nano','bat','tee','touch',
    'mkdir','rmdir','chmod','chown','ln','readlink','realpath','rsync','scp',
    'tar','zip','unzip'
  ]);

  // Commands whose presence anywhere in the command indicates a build/execute
  // operation — allow these through regardless of path-like args.
  const BUILD_CMD_PREFIXES = [
    'npm ', 'npx ', 'pnpm ', 'yarn ', 'bun ', 'bunx ',
    'go build', 'go test', 'go run',
    'cargo build', 'cargo test', 'cargo run',
    'make ', 'mvn ', 'gradle ',
    'docker build', 'docker-compose',
    'kubectl ', 'terraform ',
    'python ', 'python3 ', 'pip ', 'pip3 ',
    'node ', 'tsc ', 'vite ', 'webpack ',
    'jest ', 'vitest ', 'mocha ',
  ];

  function isBuildCommand(cmd) {
    const lower = cmd.toLowerCase().trim();
    return BUILD_CMD_PREFIXES.some(p => lower.startsWith(p) || lower.includes(' ' + p.trim() + ' '));
  }

  function extractBashPaths(cmd) {
    if (!cmd) return [];
    if (isBuildCommand(cmd)) return [];

    const results = [];

    // Extract quoted segments first
    const quotedRe = /["']([^"']+)["']/g;
    let m;
    while ((m = quotedRe.exec(cmd)) !== null) {
      const s = m[1];
      if (s.includes('/') || s.includes('\\')) results.push(s);
    }

    // Remove quoted segments and split remaining
    const unquoted = cmd.replace(/["'][^"']*["']/g, ' ');
    const tokens = unquoted.split(/\s+/).filter(Boolean);

    let isFs = false;
    let seenCmd = false;
    let skipNext = false;

    for (const tok of tokens) {
      if (skipNext) { skipNext = false; continue; }
      if (['&&', '||', ';', '|'].includes(tok)) { isFs = false; seenCmd = false; continue; }
      if (tok.startsWith('-')) {
        // --exclude=X style: skip both halves
        if (tok.includes('=')) continue;
        // --exclude X style
        if (['--exclude','--exclude-dir','--ignore','--skip','-x'].includes(tok)) skipNext = true;
        continue;
      }
      if (!seenCmd) {
        seenCmd = true;
        isFs = FS_CMDS.has(tok.toLowerCase());
        continue;
      }
      // For fs commands, blocked dir names (no slash) count; for others require slash.
      const hasSlash = tok.includes('/') || tok.includes('\\');
      const looksPath = hasSlash || /\.[a-zA-Z0-9]{1,6}$/.test(tok);
      const isBlockedName = DEFAULT_BLOCKED.includes(tok);
      if (isFs && isBlockedName) { results.push(tok); continue; }
      if (looksPath) results.push(tok);
    }
    return results;
  }

  function extractPaths(toolName, toolInput) {
    const paths = [];
    for (const key of DIRECT_PATH_KEYS) {
      if (toolInput[key] && typeof toolInput[key] === 'string') {
        paths.push(toolInput[key]);
      }
    }
    if (toolInput.command && typeof toolInput.command === 'string') {
      paths.push(...extractBashPaths(toolInput.command));
    }
    return paths.filter(Boolean);
  }

  // ── broad glob detection ──────────────────────────────────────────────────
  // Blocks patterns like **/*.ts or * at project root (context overflow risk).

  const BROAD_GLOB_RE = [
    /^\*\*$/,
    /^\*$/,
    /^\*\*\/\*$/,
    /^\*\*\/\.\*$/,
    /^\*\.\w+$/,
    /^\*\.\{[^}]+\}$/,
    /^\*\*\/\*\.\w+$/,
    /^\*\*\/\*\.\{[^}]+\}$/,
  ];

  const SPECIFIC_DIRS = new Set([
    'src','lib','app','apps','packages','components','pages','api','server',
    'client','web','mobile','shared','common','utils','helpers','services',
    'hooks','store','routes','models','controllers','views','tests','__tests__','spec',
  ]);

  function isBroadGlob(pattern) {
    return BROAD_GLOB_RE.some(re => re.test(pattern.trim()));
  }

  function hasSpecificDir(pattern) {
    const first = pattern.split('/')[0];
    return first && !first.includes('*') && first !== '.' && first !== '..'
      ? true
      : false;
  }

  function checkBroadGlob(toolName, toolInput) {
    if (toolName !== 'Glob') return null;
    const pattern = toolInput.pattern;
    if (!pattern || !isBroadGlob(pattern) || hasSpecificDir(pattern)) return null;
    const basePath = toolInput.path || '';
    // Only block when no specific base path is given.
    if (basePath && !basePath.match(/^\.?\/?$/) && SPECIFIC_DIRS.has(path.basename(basePath))) return null;
    return {
      blocked: true,
      reason: `Pattern '${pattern}' is too broad — would fill context window. Use a more specific path prefix.`,
      suggestions: ['src/**/*', 'lib/**/*', 'app/**/*'],
    };
  }

  // ── output helpers ────────────────────────────────────────────────────────

  function useColors() {
    if (process.env.NO_COLOR !== undefined) return false;
    if (process.env.FORCE_COLOR !== undefined) return true;
    return Boolean(process.stderr.isTTY);
  }

  function colorize(code, text) {
    if (!useColors()) return text;
    return `\x1b[${code}m${text}\x1b[0m`;
  }

  function formatBlockMsg(blockedPath, pattern, toolName, configHint) {
    const lines = [
      '',
      colorize('36', 'NOTE:') + ' This block is intentional — protects context window.',
      '',
      colorize('31', 'BLOCKED') + `: Access to '${blockedPath}' denied`,
      '',
      `  ${colorize('33', 'Pattern:')}  ${pattern}`,
      `  ${colorize('33', 'Tool:')}     ${toolName}`,
      '',
      `  ${colorize('34', 'To allow, add to')} ${configHint}:`,
      `    !${pattern}`,
      '',
    ];
    return lines.join('\n');
  }

  function formatBroadMsg(reason, suggestions) {
    const lines = [
      '',
      colorize('36', 'NOTE:') + ' This block is intentional to optimize context.',
      '',
      colorize('31', 'BLOCKED') + ': Overly broad glob pattern detected',
      '',
      `  ${colorize('33', 'Reason:')} ${reason}`,
      '',
      `  ${colorize('34', 'Use more specific patterns:')}`,
      ...(suggestions || []).map(s => `    • ${s}`),
      '',
    ];
    return lines.join('\n');
  }

  // ── main ──────────────────────────────────────────────────────────────────

  function main() {
    let data;
    try {
      const raw = fs.readFileSync(0, 'utf-8');
      if (!raw || !raw.trim()) { process.exit(0); }
      data = JSON.parse(raw);
    } catch {
      process.exit(0); // fail-open on parse error
    }

    if (!data.tool_input || typeof data.tool_input !== 'object') {
      process.exit(0);
    }

    const toolName  = String(data.tool_name || 'unknown');
    const toolInput = data.tool_input;
    const cwd       = typeof data.cwd === 'string' && data.cwd.trim()
      ? data.cwd.trim()
      : process.cwd();
    const claudeDir = path.join(os.homedir(), '.claude');
    const configHint = path.join(claudeDir, '.vdignore');

    // Check broad glob first (Glob tool only)
    const broadResult = checkBroadGlob(toolName, toolInput);
    if (broadResult) {
      process.stderr.write(formatBroadMsg(broadResult.reason, broadResult.suggestions));
      process.exit(2);
    }

    // Build checker (loads .vdignore files)
    const checker = buildChecker(cwd);

    // Extract and test paths
    const rawPaths = extractPaths(toolName, toolInput);
    for (const p of rawPaths) {
      const norm = normalize(p);
      if (!norm) continue;
      const result = testPath(checker, norm);
      if (result.blocked) {
        process.stderr.write(formatBlockMsg(norm, result.pattern || norm, toolName, configHint));
        process.exit(2);
      }
    }

    process.exit(0);
  }

  main();

} catch (e) {
  process.exit(0); // fail-open
}
