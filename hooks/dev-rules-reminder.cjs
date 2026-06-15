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
    getGitBranch,
    resolveSkillsVenv
  } = require('./lib/paths.cjs');
  const { readSessionState } = require('./lib/state.cjs');

  async function main() {
    const raw = fs.readFileSync(0, 'utf-8').trim();
    if (!raw) { process.exit(0); }

    const payload = JSON.parse(raw);
    const sessionId = payload.session_id || process.env.VD_SESSION_ID || null;
    const baseDir = (payload.cwd && payload.cwd.trim()) ? payload.cwd.trim() : process.cwd();

    const config = loadConfig();
    const gitBranch = getGitBranch(baseDir);
    const namePattern = resolveNamingPattern(config.plan, gitBranch);

    const resolved = resolvePlanPath(sessionId, config, readSessionState);
    const reportsPath = getReportsPath(resolved.path, resolved.resolvedBy, config.plan, config.paths, baseDir, config);
    const plansPath = getPlansPath(baseDir, config);
    const docsPath = getDocsPath(baseDir, config);

    const umbrellaVal = config.paths?.umbrella || null;
    const visualsPath  = umbrellaVal ? getVisualsPath(baseDir, config)  : null;
    const journalsPath = umbrellaVal ? getJournalsPath(baseDir, config) : null;
    const statePath    = umbrellaVal ? getStatePath(baseDir, config)    : null;

    const skillsVenv = resolveSkillsVenv(baseDir);

    const lines = [];

    lines.push('## Paths');
    if (umbrellaVal) {
      lines.push(`Reports: ${reportsPath}/ | Plans: ${plansPath}/ | Docs: ${docsPath}/ | Visuals: ${visualsPath}/ | Journals: ${journalsPath}/ | State: ${statePath}/`);
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
    lines.push('- Concise, list unresolved Qs at end');
    if (skillsVenv) {
      lines.push(`- Python scripts in .claude/skills/: Use \`${skillsVenv}\``);
      lines.push('- Never use global pip install');
    }

    process.stdout.write(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'UserPromptSubmit',
        additionalContext: lines.join('\n')
      }
    }) + '\n');

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
