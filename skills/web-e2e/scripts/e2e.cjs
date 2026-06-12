#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const https = require('node:https');
const { execFileSync, spawnSync } = require('node:child_process');

const STRATEGIES = ['oauth-interactive', 'form', 'token-inject'];
const PORT_BASE = 9300;
const PORT_RANGE = 100;
const BODY_CAP = 64 * 1024;

function findConfig(startDir) {
  let dir = path.resolve(startDir);
  for (;;) {
    const candidate = path.join(dir, '.e2e', 'config.json');
    if (fs.existsSync(candidate)) return candidate;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

function normalizeHealth(health) {
  return (health || []).map((h) => (typeof h === 'string' ? { url: h } : h));
}

function validateConfig(cfg) {
  const errors = [];
  if (!cfg || typeof cfg !== 'object') return ['config is not an object'];
  if (!cfg.name || typeof cfg.name !== 'string') errors.push('name: required string');
  if (!/^https?:\/\//.test(cfg.baseUrl || '')) errors.push('baseUrl: required http(s) URL');
  if (cfg.profile !== undefined && !/^[a-z][a-z0-9-]*$/.test(cfg.profile)) {
    errors.push('profile: must be kebab-case (matches browser-profile naming)');
  }
  for (const h of normalizeHealth(cfg.health)) {
    if (!/^https?:\/\//.test(h.url || '')) errors.push(`health: bad url ${JSON.stringify(h.url)}`);
    if (h.expect !== undefined && !Number.isInteger(h.expect)) errors.push('health.expect: must be an integer status code');
  }
  for (const c of cfg.checks || []) {
    if (!c.name || !c.cmd) errors.push('checks: each entry needs name and cmd');
  }
  const auth = cfg.auth;
  if (!auth || typeof auth !== 'object') {
    errors.push('auth: required object');
  } else {
    if (!STRATEGIES.includes(auth.strategy)) errors.push(`auth.strategy: must be one of ${STRATEGIES.join(', ')}`);
    if (!/^https?:\/\//.test(auth.probeUrl || '')) errors.push('auth.probeUrl: required absolute URL of an authenticated route');
    try {
      if (!auth.loginUrlPattern) errors.push('auth.loginUrlPattern: required regex');
      else if (new RegExp(auth.loginUrlPattern).test(auth.probeUrl || '')) {
        errors.push('auth.loginUrlPattern matches auth.probeUrl itself — the probe would always report logged-out');
      }
    } catch {
      errors.push('auth.loginUrlPattern: invalid regex');
    }
    for (const k of ['settleMs', 'timeoutMs']) {
      if (auth[k] !== undefined && (!Number.isInteger(auth[k]) || auth[k] <= 0)) errors.push(`auth.${k}: must be a positive integer (ms)`);
    }
  }
  if (cfg.boot !== undefined) {
    if (!cfg.boot || typeof cfg.boot !== 'object') {
      errors.push('boot: must be an object with up/down command strings');
    } else {
      if (cfg.boot.up !== undefined && typeof cfg.boot.up !== 'string') errors.push('boot.up: must be a shell command string');
      if (cfg.boot.down !== undefined && typeof cfg.boot.down !== 'string') errors.push('boot.down: must be a shell command string');
    }
  }
  return errors;
}

// GET only (readyz-style endpoints commonly reject HEAD); redirects are NOT followed —
// a 3xx is reported as its own status and must be expected explicitly.
function httpGet(url, { insecureTLS = false, timeoutMs = 5000 } = {}) {
  return new Promise((resolve) => {
    const u = new URL(url);
    const mod = u.protocol === 'https:' ? https : http;
    const opts = { method: 'GET', timeout: timeoutMs };
    if (u.protocol === 'https:' && insecureTLS) opts.rejectUnauthorized = false;
    const req = mod.request(u, opts, (res) => {
      let body = '';
      res.on('data', (chunk) => {
        if (body.length < BODY_CAP) body += chunk.toString('utf8');
      });
      res.on('end', () => resolve({ status: res.statusCode, body }));
    });
    req.on('timeout', () => req.destroy(new Error('timeout')));
    req.on('error', (err) => resolve({ status: 0, body: '', error: err.message }));
    req.end();
  });
}

async function checkHealth(entries, { insecureTLS = false } = {}) {
  const results = [];
  for (const h of entries) {
    const expect = h.expect ?? 200;
    const res = await httpGet(h.url, { insecureTLS: h.insecureTLS ?? insecureTLS });
    const pass = res.status === expect && (!h.bodyContains || res.body.includes(h.bodyContains));
    results.push({ url: h.url, expect, status: res.status, pass, ...(res.error ? { error: res.error } : {}) });
  }
  return results;
}

function runCheck(check, cwd) {
  const r = spawnSync('/bin/sh', ['-c', check.cmd], { cwd, timeout: 15000, stdio: 'ignore' });
  return { name: check.name, pass: r.status === 0, exit: r.status };
}

// Same hash as browser-profile/_lib.sh port_for(): POSIX cksum, so both sides agree.
function profilePort(name) {
  const out = execFileSync('/bin/sh', ['-c', 'printf %s "$1" | cksum', 'sh', name], { encoding: 'utf8' });
  const sum = parseInt(out.trim().split(/\s+/)[0], 10);
  return PORT_BASE + (sum % PORT_RANGE);
}

function profilesRoot() {
  return process.env.BROWSER_PROFILE_ROOT || path.join(os.homedir(), '.claude', 'browser-profiles');
}

function inspectProfile(name) {
  const dir = path.join(profilesRoot(), name);
  const result = { name, dir, port: profilePort(name), exists: fs.existsSync(dir), lock: 'none', running: false };
  const lockPath = path.join(dir, 'SingletonLock');
  let target = null;
  try {
    target = fs.readlinkSync(lockPath);
  } catch {
    try {
      if (fs.existsSync(lockPath)) target = '';
    } catch { /* unreadable -> treat as no lock */ }
  }
  if (target === null) return result;
  result.lock = 'stale';
  const pid = parseInt(target.slice(target.lastIndexOf('-') + 1), 10);
  if (Number.isInteger(pid) && pid > 0) {
    try {
      process.kill(pid, 0);
      const cmd = execFileSync('ps', ['-p', String(pid), '-o', 'command='], { encoding: 'utf8' });
      if (cmd.includes(`--user-data-dir=${dir} `) || cmd.trimEnd().endsWith(`--user-data-dir=${dir}`)) {
        result.lock = 'live';
        result.running = true;
        result.pid = pid;
      }
    } catch { /* dead pid -> stale */ }
  }
  return result;
}

async function cdpAlive(port) {
  const res = await httpGet(`http://127.0.0.1:${port}/json/version`, { timeoutMs: 1000 });
  return res.status === 200;
}

// Opens (and closes) a tab in the profile window via the CDP HTTP API only.
// Early-exits logged-out on loginUrlPattern match (covers external IdPs like accounts.google.com);
// logged-in requires the URL to hold steady for settleMs. SPA route guards redirect client-side
// AFTER js boot + an auth API round-trip — on a cold Chrome that exceeds short windows, so the
// default is generous; tune per project via auth.settleMs.
async function probeAuth({ cdpBase, probeUrl, loginUrlPattern, settleMs = 3000, intervalMs = 500, timeoutMs = 15000 }) {
  const pattern = new RegExp(loginUrlPattern);
  const created = await httpJson(`${cdpBase}/json/new?${encodeURIComponent(probeUrl)}`, 'PUT').catch(() => null);
  if (!created || !created.id) return { state: 'unknown', error: 'could not open probe tab' };
  const id = created.id;
  const deadline = Date.now() + timeoutMs;
  let lastUrl = null;
  let stableSince = 0;
  let state = 'unknown';
  let finalUrl = null;
  try {
    while (Date.now() < deadline) {
      await sleep(intervalMs);
      const targets = (await httpJson(`${cdpBase}/json/list`, 'GET').catch(() => null)) || [];
      const t = targets.find((x) => x.id === id);
      const url = t ? t.url : null;
      if (!url || url === 'about:blank') continue;
      finalUrl = url;
      if (pattern.test(url)) {
        state = 'logged-out';
        break;
      }
      if (url === lastUrl) {
        if (Date.now() - stableSince >= settleMs) {
          state = 'logged-in';
          break;
        }
      } else {
        lastUrl = url;
        stableSince = Date.now();
      }
    }
  } finally {
    await httpJson(`${cdpBase}/json/close/${id}`, 'GET').catch(() => {});
  }
  return { state, finalUrl };
}

function httpJson(url, method) {
  return new Promise((resolve, reject) => {
    const req = http.request(url, { method, timeout: 3000 }, (res) => {
      let body = '';
      res.on('data', (c) => (body += c));
      res.on('end', () => {
        try {
          resolve(JSON.parse(body));
        } catch {
          resolve(null);
        }
      });
    });
    req.on('timeout', () => req.destroy(new Error('timeout')));
    req.on('error', reject);
    req.end();
  });
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function tail(s, n = 2000) {
  return s.length > n ? `…${s.slice(-n)}` : s;
}

function runBoot(cmd, cwd) {
  const r = spawnSync('/bin/sh', ['-c', cmd], { cwd, timeout: 180000, encoding: 'utf8' });
  return { cmd, exit: r.status, output: tail((r.stdout || '') + (r.stderr || '')) };
}

function parseArgs(argv) {
  const args = { wait: false, json: false, config: null, timeout: 120 };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === 'status') continue;
    else if (a === '--wait') args.wait = true;
    else if (a === '--json') args.json = true;
    else if (a === '--config') args.config = argv[++i];
    else if (a === '--timeout') args.timeout = parseInt(argv[++i], 10) || 120;
    else {
      console.error(`unknown arg: ${a}\nusage: e2e.cjs [status] [--wait] [--json] [--config <path>] [--timeout <s>]`);
      process.exit(2);
    }
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const configPath = args.config || findConfig(process.cwd());
  if (!configPath) {
    console.error('no .e2e/config.json found (searched cwd upward). See vd:web-e2e references/examples/.');
    process.exit(2);
  }
  const cfg = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  const errors = validateConfig(cfg);
  if (errors.length) {
    console.error(`invalid ${configPath}:\n  - ${errors.join('\n  - ')}`);
    process.exit(2);
  }
  const projectDir = path.dirname(path.dirname(configPath));
  const health = normalizeHealth(cfg.health && cfg.health.length ? cfg.health : [cfg.baseUrl]);
  const out = { name: cfg.name, baseUrl: cfg.baseUrl, configPath };

  out.health = await checkHealth(health, { insecureTLS: cfg.insecureTLS });
  let healthy = out.health.every((h) => h.pass);

  if (!healthy && args.wait) {
    if (cfg.boot && cfg.boot.up) out.boot = runBoot(cfg.boot.up, projectDir);
    const deadline = Date.now() + args.timeout * 1000;
    while (!healthy && Date.now() < deadline) {
      await sleep(2000);
      out.health = await checkHealth(health, { insecureTLS: cfg.insecureTLS });
      healthy = out.health.every((h) => h.pass);
    }
  }

  out.checks = (cfg.checks || []).map((c) => runCheck(c, projectDir));
  const checksPass = out.checks.every((c) => c.pass);

  if (cfg.profile) {
    out.profile = inspectProfile(cfg.profile);
    out.profile.cdpAlive = out.profile.running ? await cdpAlive(out.profile.port) : false;
  }

  if (!healthy) {
    out.auth = { state: 'skipped', reason: 'health not green — probe result would be meaningless' };
  } else if (!out.profile) {
    out.auth = { state: 'skipped', reason: 'no profile configured' };
  } else if (!out.profile.cdpAlive) {
    out.auth = out.profile.running
      ? { state: 'skipped', reason: `profile Chrome running but CDP down on :${out.profile.port} — profile-close.sh ${cfg.profile} then profile-open.sh ${cfg.profile}` }
      : { state: 'skipped', reason: `profile not running — profile-open.sh ${cfg.profile}` };
  } else if (cfg.auth.strategy === 'token-inject') {
    out.auth = { state: 'inject-required', reason: 'token-inject re-authenticates every run; no probe needed' };
  } else {
    out.auth = await probeAuth({
      cdpBase: `http://127.0.0.1:${out.profile.port}`,
      probeUrl: cfg.auth.probeUrl,
      loginUrlPattern: cfg.auth.loginUrlPattern,
      ...(cfg.auth.settleMs ? { settleMs: cfg.auth.settleMs } : {}),
      ...(cfg.auth.timeoutMs ? { timeoutMs: cfg.auth.timeoutMs } : {}),
    });
    out.auth.strategy = cfg.auth.strategy;
  }

  out.ok = healthy && checksPass;

  if (args.json) {
    console.log(JSON.stringify(out, null, 2));
  } else {
    for (const h of out.health) console.log(`health  ${h.pass ? 'ok ' : 'FAIL'} ${h.url} -> ${h.status} (want ${h.expect})`);
    for (const c of out.checks) console.log(`check   ${c.pass ? 'ok ' : 'FAIL'} ${c.name}`);
    if (out.boot) console.log(`boot    exit=${out.boot.exit} ${out.boot.cmd}`);
    if (out.profile) {
      const p = out.profile;
      console.log(`profile ${p.name} · ${p.running ? 'open' : p.lock === 'stale' ? 'stale-lock' : 'closed'} · port ${p.port} · cdp ${p.cdpAlive ? 'ok' : 'down'}`);
    }
    console.log(`auth    ${out.auth.state}${out.auth.finalUrl ? ` (${out.auth.finalUrl})` : ''}${out.auth.reason ? ` — ${out.auth.reason}` : ''}`);
    console.log(out.ok ? `READY — ${cfg.name} @ ${cfg.baseUrl}` : `NOT READY — ${cfg.name} @ ${cfg.baseUrl}`);
  }
  process.exit(out.ok ? 0 : 1);
}

module.exports = {
  findConfig,
  normalizeHealth,
  validateConfig,
  httpGet,
  checkHealth,
  runCheck,
  profilePort,
  inspectProfile,
  cdpAlive,
  probeAuth,
};

if (require.main === module) {
  main().catch((err) => {
    console.error(`e2e: ${err.message}`);
    process.exit(2);
  });
}
