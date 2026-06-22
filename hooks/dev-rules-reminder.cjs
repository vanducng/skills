#!/usr/bin/env node
'use strict';
/**
 * dev-rules-reminder.cjs - VD-CLI clean-room UserPromptSubmit hook.
 *
 * Emits hookSpecificOutput.additionalContext JSON to stdout with:
 *   ## Paths  — Reports/Plans/Docs/Visuals/Journals/State (umbrella-aware)
 *   ## Naming — Report + Plan-dir patterns
 *   ## Rules  — same core rules as subagent-init
 *
 * Never throws (fail-open). Path-safe: no hardcoded home dirs.
 */

try {
  const fs = require('fs');
  const path = require('path');

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
    getGitBranch,
    resolveSkillsVenv,
    isGlobalScratchPath
  } = require('./lib/paths.cjs');
  const { readSessionState } = require('./lib/state.cjs');

  function readPayload() {
    let raw = '';
    if (!process.stdin.isTTY) raw = fs.readFileSync(0, 'utf-8').trim();
    if (!raw) {
      raw = process.argv.slice(2).reverse().find(arg => arg.trim().startsWith('{')) || '';
    }
    if (!raw) return null;
    return JSON.parse(raw);
  }

  async function main() {
    const payload = readPayload();
    if (!payload) { process.exit(0); }

    const sessionId = payload.session_id || process.env.VD_SESSION_ID || null;
    const baseDir = (payload.cwd && payload.cwd.trim()) ? payload.cwd.trim() : process.cwd();

    const config = loadConfig();
    const gitBranch = getGitBranch(baseDir);
    const namePattern = resolveNamingPattern(config.plan, gitBranch);

    const pathResolveOpts = { readOnly: true };
    const stateCache = new Map();
    const readSessionStateOnce = (sid) => {
      const key = sid || '';
      if (!stateCache.has(key)) stateCache.set(key, readSessionState(sid));
      return stateCache.get(key);
    };

    const resolved = resolvePlanPath(sessionId, config, readSessionStateOnce, baseDir);
    const reportsPath = getReportsPath(resolved.path, resolved.resolvedBy, config.plan, config.paths, baseDir, config, sessionId, readSessionStateOnce, pathResolveOpts);
    const plansPath = getPlansPath(baseDir, config, sessionId, readSessionStateOnce, pathResolveOpts);
    const docsPath = getDocsPath(baseDir, config);

    const umbrellaVal = config.paths?.umbrella || null;
    const visualsPath  = umbrellaVal ? getVisualsPath(baseDir, config, sessionId, readSessionStateOnce, pathResolveOpts)  : null;
    const journalsPath = umbrellaVal ? getJournalsPath(baseDir, config, sessionId, readSessionStateOnce, pathResolveOpts) : null;
    const statePath    = umbrellaVal ? getStatePath(baseDir, config, sessionId, readSessionStateOnce, pathResolveOpts)    : null;
    const umbrellaRoot = umbrellaVal ? resolveUmbrellaRoot(config, baseDir) : null;
    const scratchFeature = umbrellaVal && !!umbrellaRoot && config.paths?.layout === 'feature-first'
      && isGlobalScratchPath(reportsPath, baseDir, config);

    const skillsVenv = resolveSkillsVenv(baseDir);

    const lines = [];

    lines.push('## Paths');
    if (umbrellaVal) {
      lines.push(`Reports: ${reportsPath}/ | Plans: ${plansPath}/ | Docs: ${docsPath}/ | Visuals: ${visualsPath}/ | Journals: ${journalsPath}/ | State: ${statePath}/`);
      if (scratchFeature) lines.push('- Feature: none; artifacts use _global/scratch until `workbench new` or `workbench switch` selects a feature.');
    } else {
      lines.push(`Reports: ${reportsPath}/ | Plans: ${plansPath}/ | Docs: ${docsPath}/`);
    }
    lines.push('');

    lines.push('## Naming');
    lines.push(`- Report: ${path.join(reportsPath, `{type}-${namePattern}.md`)}`);
    lines.push(`- Plan dir: ${path.join(plansPath, namePattern)}/`);
    lines.push('- Replace `{type}` with: agent name, report type, or context');
    lines.push('- Replace `{slug}` in pattern with: descriptive-kebab-slug');
    lines.push('');

    lines.push('## Rules');
    lines.push(`- Reports → ${reportsPath}`);
    lines.push('- YAGNI / KISS / DRY');
    lines.push('- Before PR merge/next ship step: fetch review comments, validate, fix valid ones, reply/resolve, re-check');
    lines.push('- Concise, list unresolved Qs at end');
    if (skillsVenv) {
      lines.push(`- Python scripts in .claude/skills/: Use \`${skillsVenv}\``);
      lines.push('- Never use global pip install');
    }

    // Codex wants top-level additionalContext; Claude wants nested hookSpecificOutput.
    // Detect by the hook's own install dir so one source is correct in either copy.
    const ctx = lines.join('\n');
    const eventName = payload.hook_event_name || payload.hookEventName || 'UserPromptSubmit';
    const out = __dirname.includes('/.codex/')
      ? { additionalContext: ctx }
      : { hookSpecificOutput: { hookEventName: eventName, additionalContext: ctx } };
    process.stdout.write(JSON.stringify(out) + '\n');

    process.exit(0);
  }

  main().catch(err => {
    process.stderr.write(`[dev-rules-reminder] error: ${err.message}\n`);
    process.exit(0);
  });

} catch (e) {
  process.stderr.write(`[dev-rules-reminder] fatal: ${e.message}\n`);
  process.exit(0);
}
