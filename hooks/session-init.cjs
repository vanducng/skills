#!/usr/bin/env node
'use strict';
/**
 * session-init.cjs - VD-CLI clean-room SessionStart hook.
 *
 * Emits all VD_* env vars to CLAUDE_ENV_FILE, writes per-session temp state,
 * and prints a context summary. Never throws (fail-open).
 */

try {
  const fs = require('fs');
  const path = require('path');
  const os = require('os');

  const { loadConfig } = require('./lib/config.cjs');
  const {
    getReportsPath,
    getPlansPath,
    getDocsPath,
    getVisualsPath,
    getJournalsPath,
    getStatePath,
    resolveNamingPattern,
    resolvePlanPath,
    resolveUmbrellaRoot,
    extractTaskListId,
    isGlobalScratchPath,
    getGitBranch,
    getGitRoot
  } = require('./lib/paths.cjs');
  const { readSessionState, updateSessionState } = require('./lib/state.cjs');

  // ── shell escaping (\ " $ `) ─────────────────────────────────────────────
  function escapeShell(v) {
    return String(v)
      .replace(/\\/g, '\\\\')
      .replace(/"/g, '\\"')
      .replace(/\$/g, '\\$')
      .replace(/`/g, '\\`');
  }

  function writeEnv(envFile, key, value) {
    if (!envFile || value === null || value === undefined) return;
    fs.appendFileSync(envFile, `export ${key}="${escapeShell(value)}"\n`);
  }

  // ── project detection ─────────────────────────────────────────────────────
  function detectProjectType(override) {
    if (override && override !== 'auto') return override;
    if (fs.existsSync('pnpm-workspace.yaml') || fs.existsSync('lerna.json')) return 'monorepo';
    if (fs.existsSync('package.json')) {
      try {
        const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
        if (pkg.workspaces) return 'monorepo';
        if (pkg.main || pkg.exports) return 'library';
      } catch { /* ignore */ }
    }
    return 'single-repo';
  }

  function detectPackageManager(override) {
    if (override && override !== 'auto') return override;
    if (fs.existsSync('bun.lockb')) return 'bun';
    if (fs.existsSync('pnpm-lock.yaml')) return 'pnpm';
    if (fs.existsSync('yarn.lock')) return 'yarn';
    if (fs.existsSync('package-lock.json')) return 'npm';
    return '';
  }

  function detectFramework(override) {
    if (override && override !== 'auto') return override;
    if (!fs.existsSync('package.json')) return '';
    try {
      const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
      const deps = { ...pkg.dependencies, ...pkg.devDependencies };
      if (deps['next']) return 'next';
      if (deps['nuxt']) return 'nuxt';
      if (deps['astro']) return 'astro';
      if (deps['@remix-run/node'] || deps['@remix-run/react']) return 'remix';
      if (deps['svelte'] || deps['@sveltejs/kit']) return 'svelte';
      if (deps['vue']) return 'vue';
      if (deps['react']) return 'react';
      if (deps['express']) return 'express';
      if (deps['fastify']) return 'fastify';
    } catch { /* ignore */ }
    return '';
  }

  function getCodingLevelStyleName(level) {
    const map = { 0: 'coding-level-0-eli5', 1: 'coding-level-1-junior',
      2: 'coding-level-2-mid', 3: 'coding-level-3-senior',
      4: 'coding-level-4-lead', 5: 'coding-level-5-god' };
    return map[level] || 'coding-level-5-god';
  }

  // ── agent-team detection ──────────────────────────────────────────────────
  function detectAgentTeam() {
    try {
      const teamsDir = path.join(os.homedir(), '.claude', 'teams');
      if (!fs.existsSync(teamsDir)) return null;
      for (const entry of fs.readdirSync(teamsDir, { withFileTypes: true })) {
        if (!entry.isDirectory()) continue;
        try {
          const cfg = JSON.parse(fs.readFileSync(path.join(teamsDir, entry.name, 'config.json'), 'utf8'));
          if (cfg.members?.length > 0) return { teamName: entry.name, memberCount: cfg.members.length };
        } catch { /* skip */ }
      }
    } catch { /* skip */ }
    return null;
  }

  // ── main ──────────────────────────────────────────────────────────────────
  async function main() {
    const raw = fs.readFileSync(0, 'utf-8').trim();
    const data = raw ? JSON.parse(raw) : {};
    const envFile = process.env.CLAUDE_ENV_FILE || null;
    const sessionId = data.session_id || null;
    const source = data.source || 'unknown';
    const baseDir = process.cwd();

    const config = loadConfig();

    // Resolve plan (session lookup needs the state reader injected)
    const stateCache = new Map();
    const readSessionStateOnce = (sid) => {
      const key = sid || '';
      if (!stateCache.has(key)) stateCache.set(key, readSessionState(sid));
      return stateCache.get(key);
    };

    const resolved = resolvePlanPath(sessionId, config, readSessionStateOnce, baseDir);

    // Persist session state
    if (sessionId) {
      updateSessionState(sessionId, prev => ({
        ...prev,
        sessionOrigin: baseDir,
        activePlan: resolved.resolvedBy === 'session' ? resolved.path : null,
        suggestedPlan: null, // session-init always writes null here per contract
        timestamp: Date.now(),
        source
      }));
    }

    const gitBranch = getGitBranch();
    const gitRoot = getGitRoot();
    const namePattern = resolveNamingPattern(config.plan, gitBranch);

    // Pass baseDir so getReportsPath's isAbsolute guard handles absolute
    // activePlan paths correctly (avoids double-anchoring).
    // Append trailing '/' explicitly to match golden (contract §3.5).
    // Pass full config plus session state so umbrella and feature-first layouts
    // resolve through the same path logic as the producer skills.
    const pathResolveOpts = { readOnly: true };
    const reportsPathAbs = getReportsPath(resolved.path, resolved.resolvedBy, config.plan, config.paths, baseDir, config, sessionId, readSessionStateOnce, pathResolveOpts) + '/';
    const plansPathAbs = getPlansPath(baseDir, config, sessionId, readSessionStateOnce, pathResolveOpts);
    const docsPathAbs = getDocsPath(baseDir, config);
    // Umbrella siblings — only computed when umbrella is active (additive, zero parity risk)
    const umbrellaVal = config.paths?.umbrella || null;
    const visualsPathAbs  = umbrellaVal ? getVisualsPath(baseDir, config, sessionId, readSessionStateOnce, pathResolveOpts)  : null;
    const journalsPathAbs = umbrellaVal ? getJournalsPath(baseDir, config, sessionId, readSessionStateOnce, pathResolveOpts) : null;
    const statePathAbs    = umbrellaVal ? getStatePath(baseDir, config, sessionId, readSessionStateOnce, pathResolveOpts)    : null;
    const umbrellaRoot = umbrellaVal ? resolveUmbrellaRoot(config, baseDir) : null;
    const featureFirst = umbrellaVal && !!umbrellaRoot && config.paths?.layout === 'feature-first';
    const scratchFeature = featureFirst && isGlobalScratchPath(reportsPathAbs, baseDir, config);

    const taskListId = extractTaskListId(resolved);

    const projectType = detectProjectType(config.project?.type);
    const packageManager = detectPackageManager(config.project?.packageManager);
    const framework = detectFramework(config.project?.framework);
    const codingLevel = config.codingLevel ?? -1;

    // os.userInfo() can throw on systems where UID has no passwd entry (containers/CI).
    // Guard locally so a missing passwd entry doesn't blank every subsequent env write.
    let realHomedir;
    try { realHomedir = os.userInfo().homedir; } catch { realHomedir = os.homedir(); }
    const user = process.env.USERNAME || process.env.USER || process.env.LOGNAME
      || (() => { try { return os.userInfo().username; } catch { return ''; } })();
    const locale = process.env.LANG || '';
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    // VD_CLAUDE_SETTINGS_DIR must point to the real ~/.claude, not a test-injected fake HOME.
    // Use os.userInfo().homedir (not process.env.HOME) so it's immune to HOME env changes.
    const claudeSettingsDir = path.join(realHomedir, '.claude');

    if (envFile) {
      writeEnv(envFile, 'VD_SESSION_ID', sessionId || '');
      writeEnv(envFile, 'VD_PLAN_NAMING_FORMAT', config.plan.namingFormat);
      writeEnv(envFile, 'VD_PLAN_DATE_FORMAT', config.plan.dateFormat);
      writeEnv(envFile, 'VD_PLAN_ISSUE_PREFIX', config.plan.issuePrefix || '');
      writeEnv(envFile, 'VD_PLAN_REPORTS_DIR', config.plan.reportsDir);
      writeEnv(envFile, 'VD_NAME_PATTERN', namePattern);
      writeEnv(envFile, 'VD_ACTIVE_PLAN', resolved.resolvedBy === 'session' ? resolved.path : '');
      writeEnv(envFile, 'VD_SUGGESTED_PLAN', resolved.resolvedBy === 'branch' ? resolved.path : '');

      if (taskListId) {
        writeEnv(envFile, 'CLAUDE_CODE_TASK_LIST_ID', taskListId);
      }

      writeEnv(envFile, 'VD_GIT_ROOT', gitRoot || '');
      writeEnv(envFile, 'VD_REPORTS_PATH', reportsPathAbs);
      writeEnv(envFile, 'VD_DOCS_PATH', docsPathAbs);
      writeEnv(envFile, 'VD_PLANS_PATH', plansPathAbs);
      writeEnv(envFile, 'VD_PROJECT_ROOT', baseDir);
      // Umbrella vars — emitted only when opt-in is active (purely additive)
      if (umbrellaVal) {
        writeEnv(envFile, 'VD_UMBRELLA', umbrellaVal);
        writeEnv(envFile, 'VD_VISUALS_PATH',  visualsPathAbs);
        writeEnv(envFile, 'VD_JOURNALS_PATH', journalsPathAbs);
        writeEnv(envFile, 'VD_STATE_PATH',    statePathAbs);
      }
      writeEnv(envFile, 'VD_PROJECT_TYPE', projectType);
      writeEnv(envFile, 'VD_PACKAGE_MANAGER', packageManager);
      writeEnv(envFile, 'VD_FRAMEWORK', framework);
      writeEnv(envFile, 'VD_NODE_VERSION', process.version);
      writeEnv(envFile, 'VD_OS_PLATFORM', process.platform);
      writeEnv(envFile, 'VD_GIT_BRANCH', gitBranch || '');
      writeEnv(envFile, 'VD_USER', user);
      writeEnv(envFile, 'VD_LOCALE', locale);
      writeEnv(envFile, 'VD_TIMEZONE', timezone);
      writeEnv(envFile, 'VD_CLAUDE_SETTINGS_DIR', claudeSettingsDir);

      if (config.locale?.thinkingLanguage) {
        writeEnv(envFile, 'VD_THINKING_LANGUAGE', config.locale.thinkingLanguage);
      }
      if (config.locale?.responseLanguage) {
        writeEnv(envFile, 'VD_RESPONSE_LANGUAGE', config.locale.responseLanguage);
      }

      const val = config.plan?.validation || {};
      writeEnv(envFile, 'VD_VALIDATION_MODE', val.mode || 'prompt');
      writeEnv(envFile, 'VD_VALIDATION_MIN_QUESTIONS', val.minQuestions ?? 3);
      writeEnv(envFile, 'VD_VALIDATION_MAX_QUESTIONS', val.maxQuestions ?? 8);
      writeEnv(envFile, 'VD_VALIDATION_FOCUS_AREAS', (val.focusAreas || ['assumptions', 'risks', 'tradeoffs', 'architecture']).join(','));
      writeEnv(envFile, 'VD_CODING_LEVEL', codingLevel);
      writeEnv(envFile, 'VD_CODING_LEVEL_STYLE', getCodingLevelStyleName(codingLevel));

      const teamInfo = detectAgentTeam();
      if (teamInfo) {
        writeEnv(envFile, 'VD_AGENT_TEAM', teamInfo.teamName);
        writeEnv(envFile, 'VD_AGENT_TEAM_MEMBERS', teamInfo.memberCount);
      }
    }

    const planPart = resolved.path
      ? (resolved.resolvedBy === 'session' ? `Plan: ${resolved.path}` : `Suggested: ${resolved.path}`)
      : '';
    const parts = [`Session ${source}. Project: ${projectType}`];
    if (packageManager) parts.push(`PM: ${packageManager}`);
    parts.push(`Plan naming: ${config.plan.namingFormat}`);
    if (planPart) parts.push(planPart);
    if (scratchFeature) parts.push('Feature: _global/scratch');
    process.stdout.write(parts.join(' | ') + '\n');

    process.exit(0);
  }

  main().catch(err => {
    process.stderr.write(`[session-init] error: ${err.message}\n`);
    process.exit(0);
  });

} catch (e) {
  process.stderr.write(`[session-init] fatal: ${e.message}\n`);
  process.exit(0);
}
