'use strict';

const http = require('node:http');

function getJson(url, timeoutMs = 3000) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, { timeout: timeoutMs }, (res) => {
      let body = '';
      res.on('data', (c) => (body += c));
      res.on('end', () => {
        try {
          resolve(JSON.parse(body));
        } catch (err) {
          reject(err);
        }
      });
    });
    req.on('timeout', () => req.destroy(new Error('timeout')));
    req.on('error', reject);
  });
}

function listTargets(port) {
  return getJson(`http://127.0.0.1:${port}/json/list`);
}

// Prefer the most recently active page target; chrome:// surfaces are never useful here.
function pickPageTarget(targets, urlFilter) {
  const pages = (targets || []).filter(
    (t) => t.type === 'page' && !String(t.url || '').startsWith('chrome') && !String(t.url || '').startsWith('devtools')
  );
  if (urlFilter) return pages.find((t) => String(t.url || '').includes(urlFilter)) || null;
  return pages[0] || null;
}

async function waitForCdp(port, timeoutMs = 5000) {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    try {
      await getJson(`http://127.0.0.1:${port}/json/version`, 1000);
      return true;
    } catch {
      if (Date.now() > deadline) return false;
      await new Promise((r) => setTimeout(r, 500));
    }
  }
}

// Minimal CDP session over the global WebSocket (Node 22+). One command in flight per id;
// events fan out to on(method) listeners.
class CdpSession {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = new Map();
    this.ws = null;
  }

  connect() {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(this.wsUrl);
      ws.onopen = () => resolve();
      ws.onerror = () => reject(new Error(`cannot connect to ${this.wsUrl}`));
      ws.onmessage = (event) => this.dispatch(String(event.data));
      this.ws = ws;
    });
  }

  dispatch(raw) {
    let msg;
    try {
      msg = JSON.parse(raw);
    } catch {
      return;
    }
    if (msg.id && this.pending.has(msg.id)) {
      const { resolve, reject } = this.pending.get(msg.id);
      this.pending.delete(msg.id);
      msg.error ? reject(new Error(`${msg.error.message || 'CDP error'}`)) : resolve(msg.result);
    } else if (msg.method && this.listeners.has(msg.method)) {
      for (const fn of this.listeners.get(msg.method)) fn(msg.params);
    }
  }

  send(method, params = {}, timeoutMs = 30000) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`CDP ${method} timed out after ${timeoutMs}ms`));
      }, timeoutMs);
      this.pending.set(id, {
        resolve: (v) => {
          clearTimeout(timer);
          resolve(v);
        },
        reject: (e) => {
          clearTimeout(timer);
          reject(e);
        },
      });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  on(method, fn) {
    if (!this.listeners.has(method)) this.listeners.set(method, []);
    this.listeners.get(method).push(fn);
  }

  once(method, timeoutMs = 30000) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error(`timed out waiting for ${method}`)), timeoutMs);
      this.on(method, (params) => {
        clearTimeout(timer);
        resolve(params);
      });
    });
  }

  close() {
    try {
      this.ws && this.ws.close();
    } catch { /* already closed */ }
  }
}

async function connectToPage(port, urlFilter) {
  if (!(await waitForCdp(port, 3000))) {
    throw new Error(`no CDP endpoint on :${port} - open the profile first (profile-open.sh <name>)`);
  }
  const target = pickPageTarget(await listTargets(port), urlFilter);
  if (!target) throw new Error(`no page target on :${port}${urlFilter ? ` matching "${urlFilter}"` : ''}`);
  const session = new CdpSession(target.webSocketDebuggerUrl);
  await session.connect();
  session.targetUrl = target.url;
  return session;
}

function parseArgs(argv, defaults = {}) {
  const args = { ...defaults };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      const next = argv[i + 1];
      if (next === undefined || next.startsWith('--')) args[key] = true;
      else args[key] = argv[++i];
    }
  }
  return args;
}

module.exports = { getJson, listTargets, pickPageTarget, waitForCdp, CdpSession, connectToPage, parseArgs };
