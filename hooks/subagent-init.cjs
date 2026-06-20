#!/usr/bin/env node
'use strict';
/**
 * subagent-init.cjs - VD-CLI clean-room SubagentStart hook.
 *
 * Emits hookSpecificOutput.additionalContext JSON to stdout.
 * Re-derives all paths independently (does not rely on VD_* env vars).
 */

try {
  const fs = require('fs');
  const path = require('path');

  const { loadConfig } = require('./lib/config.cjs');
  const {
    normalizePath,
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
    getGitBranch,
    resolveSkillsVenv,
    isGlobalScratchPath
  } = require('./lib/paths.cjs');
  const { readSessionState } = require('./lib/state.cjs');

  const PLAN_AWARE_AGENTS = new Set([
    'planner', 'project-manager', 'code-simplifier',
    'brainstormer', 'code-reviewer', 'fullstack-developer'
  ]);

  async function main() {
    const raw = fs.readFileSync(0, 'utf-8').trim();
    if (!raw) { process.exit(0); }

    const payload = JSON.parse(raw);
    const agentType = payload.agent_type || 'unknown';
    const agentId = payload.agent_id || 'unknown';
    const effectiveCwd = payload.cwd?.trim() || process.cwd();
    const sessionId = payload.session_id || process.env.VD_SESSION_ID || null;

    const config = loadConfig();

    const gitBranch = getGitBranch(effectiveCwd);
    const baseDir = effectiveCwd;

    // Re-derive naming pattern independently (not from env)
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

    const activePlan = resolved.resolvedBy === 'session' ? resolved.path : '';
    const suggestedPlan = resolved.resolvedBy === 'branch' ? resolved.path : '';
    const taskListId = extractTaskListId(resolved);

    const thinkingLang = config.locale?.thinkingLanguage || '';
    const responseLang = config.locale?.responseLanguage || '';
    const effectiveThinking = thinkingLang || (responseLang ? 'en' : '');

    const skillsVenv = resolveSkillsVenv(effectiveCwd);

    const lines = [];

    lines.push(`## Subagent: ${agentType}`);
    lines.push(`ID: ${agentId} | CWD: ${effectiveCwd}`);
    lines.push('');

    lines.push('## Context');
    if (activePlan) {
      lines.push(`- Plan: ${activePlan}`);
      if (taskListId) {
        lines.push(`- Task List: ${taskListId} (shared with session)`);
      }
    } else if (suggestedPlan) {
      lines.push(`- Plan: none | Suggested: ${suggestedPlan}`);
    } else {
      lines.push('- Plan: none');
    }
    lines.push(`- Reports: ${reportsPath}`);
    // Umbrella-on: append sibling dirs after docs; umbrella-off: legacy two-dir line
    if (umbrellaVal) {
      lines.push(`- Paths: ${plansPath}/ | ${docsPath}/ | Visuals: ${visualsPath}/ | Journals: ${journalsPath}/ | State: ${statePath}/`);
      if (scratchFeature) lines.push('- Feature: none; artifacts use _global/scratch until `workbench new` or `workbench switch` selects a feature.');
    } else {
      lines.push(`- Paths: ${plansPath}/ | ${docsPath}/`);
    }
    lines.push('');

    const hasThinking = effectiveThinking && effectiveThinking !== responseLang;
    if (hasThinking || responseLang) {
      lines.push('## Language');
      if (hasThinking) {
        lines.push(`- Thinking: Use ${effectiveThinking} for reasoning (logic, precision).`);
      }
      if (responseLang) {
        lines.push(`- Response: Respond in ${responseLang} (natural, fluent).`);
      }
      lines.push('');
    }

    lines.push('## Rules');
    lines.push(`- Reports → ${reportsPath}`);
    lines.push('- YAGNI / KISS / DRY');
    lines.push('- Before PR merge/next ship step: fetch review comments, validate, fix valid ones, reply/resolve, re-check');
    lines.push('- Concise, list unresolved Qs at end');
    if (skillsVenv) {
      lines.push(`- Python scripts in .claude/skills/: Use \`${skillsVenv}\``);
      lines.push('- Never use global pip install');
    }

    lines.push('');
    lines.push('## Naming');
    lines.push(`- Report: ${path.join(reportsPath, `${agentType}-${namePattern}.md`)}`);
    lines.push(`- Plan dir: ${path.join(plansPath, namePattern)}/`);
    // Umbrella siblings in Naming block (only when opt-in active)
    if (umbrellaVal) {
      lines.push(`- Visual: ${path.join(visualsPath, namePattern)}/`);
      lines.push(`- Journal: ${path.join(journalsPath, namePattern)}.md`);
      lines.push(`- State dir: ${statePath}/`);
    }

    if (PLAN_AWARE_AGENTS.has(agentType)) {
      lines.push('');
      lines.push('## Plan Status Updates');
      lines.push('Edit the plan.md Status column directly: `Pending` → `In Progress` → `Completed`.');
    }

    if (config.trust?.enabled && config.trust?.passphrase) {
      lines.push('');
      lines.push('## Trust Verification');
      lines.push(`Passphrase: "${config.trust.passphrase}"`);
    }

    const agentCtx = config.subagent?.agents?.[agentType]?.contextPrefix;
    if (agentCtx) {
      lines.push('');
      lines.push('## Agent Instructions');
      lines.push(agentCtx);
    }

    process.stdout.write(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'SubagentStart',
        additionalContext: lines.join('\n')
      }
    }) + '\n');

    process.exit(0);
  }

  main().catch(err => {
    process.stderr.write(`[subagent-init] error: ${err.message}\n`);
    process.exit(0);
  });

} catch (e) {
  process.stderr.write(`[subagent-init] fatal: ${e.message}\n`);
  process.exit(0);
}
