#!/usr/bin/env node
'use strict';
/**
 * statusline.cjs - VD-CLI clean-room statusLine hook.
 *
 * Reads Claude Code statusLine stdin JSON, emits a single ANSI status line.
 * Sections: model · cwd/branch · context usage · active plan · cost.
 * Registered via settings.json "statusLine" key (not hooks{}).
 * Fail-open: always emits at least a minimal line; never crashes.
 */

try {
  const fs = require('fs');
  const path = require('path');
  const os = require('os');
  const { execFileSync } = require('child_process');

  // ── ANSI helpers ──────────────────────────────────────────────────────────

  const NO_COLOR = process.env.NO_COLOR !== undefined || process.env.TERM === 'dumb';
  const FORCE_COLOR = process.env.FORCE_COLOR !== undefined;
  const useColor = FORCE_COLOR || (!NO_COLOR && Boolean(process.stderr.isTTY || process.stdout.isTTY));

  function ansi(code, text) {
    if (!useColor || !text) return text || '';
    return `\x1b[${code}m${text}\x1b[0m`;
  }

  const dim     = (s) => ansi('2', s);
  const cyan    = (s) => ansi('36', s);
  const magenta = (s) => ansi('35', s);
  const yellow  = (s) => ansi('33', s);
  const green   = (s) => ansi('32', s);
  const red     = (s) => ansi('31', s);
  const bold    = (s) => ansi('1', s);

  function contextColor(pct) {
    if (pct >= 85) return red;
    if (pct >= 70) return yellow;
    return green;
  }

  // ── git branch (cheap, no network) ────────────────────────────────────────

  function gitBranch(cwd) {
    try {
      return execFileSync('git', ['branch', '--show-current'], {
        cwd: cwd || process.cwd(),
        encoding: 'utf8',
        timeout: 2000,
        stdio: ['pipe', 'pipe', 'pipe']
      }).trim() || null;
    } catch {
      return null;
    }
  }

  // ── path helpers ──────────────────────────────────────────────────────────

  function shortenDir(fullPath) {
    const home = os.homedir();
    if (fullPath.startsWith(home)) {
      return '~' + fullPath.slice(home.length);
    }
    return fullPath;
  }

  function basename(fullPath) {
    return path.basename(fullPath) || fullPath;
  }

  // ── active plan (reads session temp state) ────────────────────────────────

  function readActivePlan(sessionId) {
    if (!sessionId) return null;
    try {
      const tmpFile = path.join(os.tmpdir(), `vd-session-${sessionId}.json`);
      if (!fs.existsSync(tmpFile)) return null;
      const state = JSON.parse(fs.readFileSync(tmpFile, 'utf8'));
      return state.activePlan || null;
    } catch {
      return null;
    }
  }

  // ── context bar ───────────────────────────────────────────────────────────

  function contextBar(pct) {
    const capped = Math.min(100, Math.max(0, pct));
    const filled = Math.round(capped / 10);
    const bar = '█'.repeat(filled) + '░'.repeat(10 - filled);
    const colorFn = contextColor(capped);
    return colorFn(bar) + ' ' + colorFn(`${Math.round(capped)}%`);
  }

  // ── format cost ───────────────────────────────────────────────────────────

  function formatCost(usd) {
    if (typeof usd !== 'number' || usd <= 0) return null;
    if (usd < 0.01) return '<$0.01';
    if (usd < 1) return `$${usd.toFixed(2)}`;
    return `$${usd.toFixed(2)}`;
  }

  // ── main ──────────────────────────────────────────────────────────────────

  function main() {
    let payload = {};
    try {
      const raw = fs.readFileSync(0, 'utf-8').trim();
      if (raw) payload = JSON.parse(raw);
    } catch {
      // Fail-open: proceed with empty payload.
    }

    const sessionId  = payload.session_id || null;
    // Claude Code sends model as an object {id, display_name}; tolerate a plain string too.
    const model      = (payload.model && typeof payload.model === 'object'
      ? (payload.model.display_name || payload.model.id)
      : payload.model) || null;
    const cwd        = (payload.cwd || payload.workspace?.current_dir || process.cwd()).trim();
    const contextPct = typeof payload.context_window_usage_percent === 'number'
      ? payload.context_window_usage_percent
      : (typeof payload.exceeds_200k_tokens === 'boolean' && payload.exceeds_200k_tokens ? 100 : null);
    const totalCost  = typeof payload.total_cost_usd === 'number'
      ? payload.total_cost_usd
      : (payload.cost && typeof payload.cost.total_cost_usd === 'number' ? payload.cost.total_cost_usd : null);

    const parts = [];

    // Model
    if (model) {
      const shortModel = model.replace(/^claude-/, '').replace(/-\d{8}$/, '');
      parts.push(cyan(shortModel));
    }

    // Directory + branch
    const dirShort = basename(cwd);
    const branch = gitBranch(cwd);
    const dirPart = branch
      ? `${dim(shortenDir(cwd))} ${magenta(branch)}`
      : dim(shortenDir(cwd));
    parts.push(dirPart);

    // Context bar
    if (contextPct !== null) {
      parts.push(contextBar(contextPct));
    }

    // Active plan (cheap session-state read)
    const activePlan = readActivePlan(sessionId);
    if (activePlan) {
      const planName = path.basename(activePlan);
      parts.push(dim('plan:') + ' ' + yellow(planName));
    }

    // Cost
    const costStr = formatCost(totalCost);
    if (costStr) {
      parts.push(dim(costStr));
    }

    if (parts.length === 0) {
      process.stdout.write(dim('vd') + '\n');
    } else {
      process.stdout.write(parts.join('  ') + '\n');
    }

    process.exit(0);
  }

  main();

} catch (e) {
  // Absolute last resort: emit minimal line and exit cleanly.
  try {
    process.stdout.write('vd\n');
  } catch { /* nothing more we can do */ }
  process.exit(0);
}
