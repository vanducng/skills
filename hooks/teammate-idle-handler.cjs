#!/usr/bin/env node
'use strict';
/**
 * teammate-idle-handler.cjs - VD-CLI clean-room TeammateIdle hook.
 *
 * Fires when an agent team teammate goes idle.
 * Emits available/unblocked task summary as additionalContext.
 * No-op when team_name is absent. Fail-open: always exits 0.
 */

try {
  const fs   = require('fs');
  const path = require('path');
  const os   = require('os');

  const TASKS_DIR = path.join(os.homedir(), '.claude', 'tasks');

  function readJson(filePath) {
    try { return JSON.parse(fs.readFileSync(filePath, 'utf8')); }
    catch { return null; }
  }

  function getTaskInfo(teamName) {
    const taskDir = path.join(TASKS_DIR, teamName);
    try {
      if (!fs.existsSync(taskDir)) return null;
      const files = fs.readdirSync(taskDir).filter(f => f.endsWith('.json'));
      const tasks = files.map(f => readJson(path.join(taskDir, f))).filter(Boolean);

      const completedIds = new Set(
        tasks.filter(t => t.status === 'completed').map(t => String(t.id))
      );

      let pending = 0, inProgress = 0, completed = 0;
      const unblocked = [];

      for (const task of tasks) {
        if (task.status === 'completed') { completed++; continue; }
        if (task.status === 'in_progress') { inProgress++; continue; }
        if (task.status !== 'pending') continue;
        pending++;

        const blockers = task.blockedBy || [];
        const isUnblocked = blockers.every(id => completedIds.has(String(id)));
        if (isUnblocked && !task.owner) {
          unblocked.push({ id: task.id, subject: task.subject || '' });
        }
      }

      const total = pending + inProgress + completed;
      return { pending, inProgress, completed, total, unblocked };
    } catch { return null; }
  }

  function main() {
    let payload = {};
    try {
      const raw = fs.readFileSync(0, 'utf-8').trim();
      if (!raw) process.exit(0);
      payload = JSON.parse(raw);
    } catch { process.exit(0); }

    const { teammate_name, team_name } = payload;
    if (!team_name) process.exit(0);

    const info   = getTaskInfo(team_name);
    const lines  = [];
    lines.push(`## Teammate Idle`);
    lines.push(`${teammate_name || 'Teammate'} is idle.`);

    if (info) {
      const remaining = info.pending + info.inProgress;
      lines.push(`Tasks: ${info.completed}/${info.total} done. ${remaining} remaining.`);
      if (info.unblocked.length > 0) {
        lines.push(`Unblocked & unassigned: ${info.unblocked.map(t => `#${t.id} "${t.subject}"`).join(', ')}`);
        lines.push(`Consider assigning work to ${teammate_name || 'this teammate'} or waking them with a message.`);
      } else if (remaining === 0) {
        lines.push(`No remaining tasks. Consider shutting down ${teammate_name || 'this teammate'}.`);
      } else {
        lines.push(`All remaining tasks are blocked or assigned. ${teammate_name || 'Teammate'} may be waiting for dependencies.`);
      }
    }

    process.stdout.write(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'TeammateIdle',
        additionalContext: lines.join('\n')
      }
    }) + '\n');

    process.exit(0);
  }

  main();

} catch (e) {
  process.exit(0);
}
