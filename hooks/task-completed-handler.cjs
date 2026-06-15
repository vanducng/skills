#!/usr/bin/env node
'use strict';
/**
 * task-completed-handler.cjs - VD-CLI clean-room TaskCompleted hook.
 *
 * Fires when a task is marked completed in a team session.
 * Appends a completion log entry to VD_REPORTS_PATH and emits a
 * progress summary as additionalContext.
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
      const total = pending + inProgress + completed;
      return { pending, inProgress, completed, total };
    } catch { return null; }
  }

  function appendCompletionLog(teamName, taskId, taskSubject, teammateName) {
    const reportsPath = process.env.VD_REPORTS_PATH;
    if (!reportsPath) return;
    try {
      fs.mkdirSync(reportsPath, { recursive: true });
      const logFile = path.join(reportsPath, `team-${teamName}-completions.md`);
      const ts = new Date().toISOString().slice(0, 19).replace('T', ' ');
      fs.appendFileSync(logFile, `- [${ts}] Task #${taskId} "${taskSubject}" completed by ${teammateName}\n`);
    } catch { /* fail-open */ }
  }

  function main() {
    let payload = {};
    try {
      const raw = fs.readFileSync(0, 'utf-8').trim();
      if (!raw) process.exit(0);
      payload = JSON.parse(raw);
    } catch { process.exit(0); }

    const { task_id, task_subject, teammate_name, team_name } = payload;
    if (!team_name) process.exit(0);

    appendCompletionLog(team_name, task_id, task_subject || '', teammate_name || 'unknown');

    const counts = countTasks(team_name);
    const lines  = [];
    lines.push(`## Task Completed`);
    lines.push(`Task #${task_id} "${task_subject || ''}" completed by ${teammate_name || 'unknown'}.`);

    if (counts) {
      const remaining = counts.pending + counts.inProgress;
      lines.push(`Progress: ${counts.completed}/${counts.total} done. ${counts.pending} pending, ${counts.inProgress} in progress.`);
      if (remaining === 0) {
        lines.push('');
        lines.push('**All tasks completed.** Consider shutting down teammates and synthesizing results.');
      }
    }

    process.stdout.write(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'TaskCompleted',
        additionalContext: lines.join('\n')
      }
    }) + '\n');

    process.exit(0);
  }

  main();

} catch (e) {
  process.exit(0);
}
