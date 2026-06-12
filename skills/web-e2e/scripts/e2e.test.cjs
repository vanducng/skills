'use strict';

const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');

const {
  findConfig,
  normalizeHealth,
  validateConfig,
  checkHealth,
  runCheck,
  profilePort,
  probeAuth,
} = require('./e2e.cjs');

const EXAMPLES = path.join(__dirname, '..', 'references', 'examples');

function validBase() {
  return {
    name: 'myapp',
    baseUrl: 'http://localhost:8082',
    profile: 'myapp-dev',
    health: ['http://localhost:8082/'],
    auth: { strategy: 'form', probeUrl: 'http://localhost:8082/', loginUrlPattern: '/login' },
  };
}

test('validateConfig accepts both shipped example configs', () => {
  for (const f of fs.readdirSync(EXAMPLES)) {
    const cfg = JSON.parse(fs.readFileSync(path.join(EXAMPLES, f), 'utf8'));
    assert.deepStrictEqual(validateConfig(cfg), [], `${f} should validate clean`);
  }
});

test('validateConfig rejects bad inputs', () => {
  assert.ok(validateConfig(null).length);
  assert.ok(validateConfig({}).length >= 3);
  assert.ok(validateConfig({ ...validBase(), baseUrl: 'ftp://x' }).some((e) => e.includes('baseUrl')));
  assert.ok(validateConfig({ ...validBase(), profile: 'Bad_Name' }).some((e) => e.includes('profile')));
  const badStrategy = validBase();
  badStrategy.auth.strategy = 'magic';
  assert.ok(validateConfig(badStrategy).some((e) => e.includes('auth.strategy')));
  const badPattern = validBase();
  badPattern.auth.loginUrlPattern = '([';
  assert.ok(validateConfig(badPattern).some((e) => e.includes('invalid regex')));
  const badHealth = validBase();
  badHealth.health = [{ url: 'http://x', expect: 'ok' }];
  assert.ok(validateConfig(badHealth).some((e) => e.includes('health.expect')));
  const selfMatch = validBase();
  selfMatch.auth.probeUrl = 'http://localhost:8082/login';
  assert.ok(validateConfig(selfMatch).some((e) => e.includes('matches auth.probeUrl')));
  const badSettle = validBase();
  badSettle.auth.settleMs = '3000';
  assert.ok(validateConfig(badSettle).some((e) => e.includes('auth.settleMs')));
  assert.ok(validateConfig({ ...validBase(), boot: null }).some((e) => e.includes('boot:')));
});

test('normalizeHealth maps strings to objects', () => {
  assert.deepStrictEqual(normalizeHealth(['http://a', { url: 'http://b', expect: 302 }]), [
    { url: 'http://a' },
    { url: 'http://b', expect: 302 },
  ]);
});

test('findConfig walks up to the nearest .e2e/config.json', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'e2e-'));
  const nested = path.join(root, 'a', 'b');
  fs.mkdirSync(path.join(root, '.e2e'), { recursive: true });
  fs.mkdirSync(nested, { recursive: true });
  fs.writeFileSync(path.join(root, '.e2e', 'config.json'), '{}');
  assert.strictEqual(findConfig(nested), path.join(root, '.e2e', 'config.json'));
  fs.rmSync(root, { recursive: true, force: true });
});

test('checkHealth uses GET, honors expect and bodyContains, never follows redirects', async () => {
  const methods = [];
  const server = http.createServer((req, res) => {
    methods.push(req.method);
    if (req.url === '/ready') return res.writeHead(200).end('{"status":"ready"}');
    if (req.url === '/redir') return res.writeHead(302, { location: '/login' }).end();
    res.writeHead(404).end();
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const base = `http://127.0.0.1:${server.address().port}`;

  const results = await checkHealth([
    { url: `${base}/ready`, bodyContains: 'ready' },
    { url: `${base}/redir`, expect: 302 },
    { url: `${base}/redir` },
    { url: `${base}/missing` },
    { url: `${base}/ready`, bodyContains: 'nope' },
  ]);
  assert.deepStrictEqual(results.map((r) => r.pass), [true, true, false, false, false]);
  assert.ok(methods.every((m) => m === 'GET'), 'health checks must use GET');
  server.close();
});

test('checkHealth reports unreachable hosts as failures, not throws', async () => {
  const results = await checkHealth([{ url: 'http://127.0.0.1:1/nope' }]);
  assert.strictEqual(results[0].pass, false);
  assert.strictEqual(results[0].status, 0);
});

test('runCheck passes on exit 0 and fails otherwise', () => {
  assert.strictEqual(runCheck({ name: 'yes', cmd: 'true' }, '/tmp').pass, true);
  assert.strictEqual(runCheck({ name: 'no', cmd: 'false' }, '/tmp').pass, false);
});

test('profilePort matches browser-profile _lib.sh and stays in range', () => {
  const { execFileSync } = require('node:child_process');
  for (const name of ['retell-staging', 'cnb-polaris', 'hire-intelligence']) {
    const sum = parseInt(
      execFileSync('/bin/sh', ['-c', 'printf %s "$1" | cksum', 'sh', name], { encoding: 'utf8' }).split(/\s+/)[0],
      10
    );
    const expected = 9300 + (sum % 100);
    assert.strictEqual(profilePort(name), expected);
    assert.ok(expected >= 9300 && expected < 9400);
  }
});

// Mock CDP HTTP server: PUT /json/new creates a target whose URL follows a scripted sequence.
function mockCdp(urlSequence) {
  let reads = 0;
  const server = http.createServer((req, res) => {
    if (req.method === 'PUT' && req.url.startsWith('/json/new')) {
      return res.writeHead(200).end(JSON.stringify({ id: 't1', url: 'about:blank' }));
    }
    if (req.url === '/json/list') {
      const url = urlSequence[Math.min(reads, urlSequence.length - 1)];
      reads += 1;
      return res.writeHead(200).end(JSON.stringify([{ id: 't1', url }]));
    }
    if (req.url.startsWith('/json/close/')) {
      server.closed = true;
      return res.writeHead(200).end('Target is closing');
    }
    res.writeHead(404).end();
  });
  return server;
}

async function runProbe(urlSequence, pattern) {
  const server = mockCdp(urlSequence);
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const result = await probeAuth({
    cdpBase: `http://127.0.0.1:${server.address().port}`,
    probeUrl: 'http://localhost:8082/',
    loginUrlPattern: pattern,
    settleMs: 200,
    intervalMs: 50,
    timeoutMs: 2000,
  });
  const closed = server.closed === true;
  server.close();
  return { ...result, closed };
}

test('probeAuth: redirect to login -> logged-out, early exit', async () => {
  const r = await runProbe(['about:blank', 'http://localhost:8082/login'], '/login');
  assert.strictEqual(r.state, 'logged-out');
  assert.ok(r.closed, 'probe tab must be closed');
});

test('probeAuth: external IdP redirect matches foreign-origin pattern', async () => {
  const r = await runProbe(
    ['https://myapp.test/dashboard', 'https://accounts.google.com/o/oauth2/auth'],
    '/login|accounts\\.google\\.com'
  );
  assert.strictEqual(r.state, 'logged-out');
});

test('probeAuth: stable authed URL -> logged-in after settle window', async () => {
  const r = await runProbe(['about:blank', 'http://localhost:8082/', 'http://localhost:8082/'], '/login');
  assert.strictEqual(r.state, 'logged-in');
  assert.strictEqual(r.finalUrl, 'http://localhost:8082/');
  assert.ok(r.closed);
});

test('probeAuth: never-settling URL -> unknown at timeout', async () => {
  const seq = Array.from({ length: 100 }, (_, i) => `http://localhost:8082/step${i}`);
  const r = await runProbe(seq, '/login');
  assert.strictEqual(r.state, 'unknown');
});

test('probeAuth: unreachable CDP -> unknown, no throw', async () => {
  const r = await probeAuth({
    cdpBase: 'http://127.0.0.1:1',
    probeUrl: 'http://x/',
    loginUrlPattern: '/login',
    timeoutMs: 300,
    intervalMs: 50,
  });
  assert.strictEqual(r.state, 'unknown');
});
