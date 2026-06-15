#!/usr/bin/env node
'use strict';
/**
 * team-context-inject.cjs - VD-CLI clean-room SubagentStart hook.
 *
 * When the spawned agent has an agent_id matching "name@team-name" format,
 * injects team peer list and task summary as additionalContext.
 * No-op when teams directory is absent or agent is not a team member.
 * Fail-open: always exits 0.
 */

try {
  const fs   = require('fs');
  const path = require('path');
  const os   = require('os');

  const TEAMS_DIR = path.join(os.homedir(), '.claude', 'teams');
  const TASKS_DIR = path.join(os.homedir(), '.claude', 'tasks');

  function readJson(filePath) {
    try {
      return JSON.parse(fs.readFileSync(filePath, 'utf8'));
    } catch { return null; }
  }

  /**
   * Extract team name from agent_id (format "agentName@team-name").
   * Rejects path-traversal and invalid forms.
   */
  function extractTeamName(agentId) {
    if (!agentId || typeof agentId !== 'string') return null;
    const at = agentId.indexOf('@');
    if (at < 1) return null;
    const name = agentId.slice(at + 1);
    if (!name || name.includes('/') || name.includes('\\') || name.includes('..')) return null;
    return name;
  }

  function buildPeerList(config, currentAgentId) {
    if (!Array.isArray(config?.members)) return 'none';
    const peers = config.members
      .filter(m => m.agentId !== currentAgentId)
      .map(m => `${m.name} (${m.agentType || 'unknown'})`)
      .join(', ');
    return peers || 'none';
  }

  function countTasks(teamName) {
    const taskDir = path.join(TASKS_DIR, teamName);
    try {
      if (!fs.existsSync(taskDir)) return null;
      const files = fs.readdirSync(taskDir).filter(f => f.endsWith('.json'));
      let pending = 0, inProgress = 0, completed = 0;
      for (const file of files) {
        const t = readJson(path.join(taskDir, file));
        if (!t?.status) continue;
        if (t.status === 'pending') pending++;
        else if (t.status === 'in_progress') inProgress++;
        else if (t.status === 'completed') completed++;
      }
      return { pending, inProgress, completed };
    } catch { return null; }
  }

  function buildVdContext() {
    const env = process.env;
    const ctx = [];
    if (env.VD_REPORTS_PATH) ctx.push(`Reports: ${env.VD_REPORTS_PATH}`);
    if (env.VD_PLANS_PATH)   ctx.push(`Plans: ${env.VD_PLANS_PATH}`);
    if (env.VD_PROJECT_ROOT) ctx.push(`Project: ${env.VD_PROJECT_ROOT}`);
    if (env.VD_NAME_PATTERN) ctx.push(`Naming: ${env.VD_NAME_PATTERN}`);
    if (env.VD_GIT_BRANCH)   ctx.push(`Branch: ${env.VD_GIT_BRANCH}`);
    if (env.VD_ACTIVE_PLAN)  ctx.push(`Active plan: ${env.VD_ACTIVE_PLAN}`);
    ctx.push('Commits: conventional (feat:, fix:, docs:, refactor:, test:, chore:)');
    return ctx;
  }

  function main() {
    let payload = {};
    try {
      const raw = fs.readFileSync(0, 'utf-8').trim();
      if (!raw) process.exit(0);
      payload = JSON.parse(raw);
    } catch { process.exit(0); }

    const agentId  = payload.agent_id || '';
    const teamName = extractTeamName(agentId);
    if (!teamName) process.exit(0);

    if (!fs.existsSync(TEAMS_DIR)) process.exit(0);

    const configPath = path.join(TEAMS_DIR, teamName, 'config.json');
    const config = readJson(configPath);
    if (!config) process.exit(0);

    const peerList = buildPeerList(config, agentId);
    const counts   = countTasks(teamName);

    const lines = [];
    lines.push(`## Team Context`);
    lines.push(`Team: ${config.name || teamName}`);
    lines.push(`Your peers: ${peerList}`);
    if (counts) {
      lines.push(`Task summary: ${counts.pending} pending, ${counts.inProgress} in progress, ${counts.completed} completed`);
    }

    const vdCtx = buildVdContext();
    if (vdCtx.length > 0) {
      lines.push('');
      lines.push('## VD Context');
      lines.push(...vdCtx);
    }

    lines.push('');
    lines.push('Remember: Check TaskList, claim tasks, respect file ownership, use SendMessage to communicate.');

    process.stdout.write(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'SubagentStart',
        additionalContext: lines.join('\n')
      }
    }) + '\n');

    process.exit(0);
  }

  main();

} catch (e) {
  process.exit(0);
}
