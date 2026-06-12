'use strict';

const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { buildConfig, readE2eConfig, scaffold, GITIGNORE_LINES } = require('./init-playwright.cjs');
const {
  createSummary,
  parsePlaywrightData,
  parseVitestData,
  parseJunitXml,
  passRate,
  formatMarkdown,
} = require('./analyze-test-results.cjs');

test('buildConfig inherits baseUrl, storageState default, and TLS posture from .e2e config', () => {
  const cfg = buildConfig({ baseUrl: 'https://myapp.test', insecureTLS: true });
  assert.ok(cfg.includes("'https://myapp.test'"));
  assert.ok(cfg.includes("storageState: process.env.E2E_STORAGE_STATE || '.e2e/storageState.json'"));
  assert.ok(cfg.includes('ignoreHTTPSErrors: true'));
  const plain = buildConfig(null);
  assert.ok(plain.includes("'http://localhost:3000'"));
  assert.ok(!plain.includes('ignoreHTTPSErrors'));
});

test('scaffold writes files once, reads .e2e/config.json, and appends gitignore', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'wt-'));
  fs.mkdirSync(path.join(dir, '.e2e'));
  fs.writeFileSync(path.join(dir, '.e2e', 'config.json'), JSON.stringify({ baseUrl: 'http://localhost:8082' }));
  const logs = [];
  const r1 = scaffold(dir, (m) => logs.push(m));
  assert.strictEqual(r1.usedE2eConfig, true);
  assert.deepStrictEqual(r1.created.sort(), ['playwright.config.ts', 'tests/e2e/logged-out.spec.ts', 'tests/e2e/smoke.spec.ts']);
  assert.ok(fs.readFileSync(path.join(dir, 'playwright.config.ts'), 'utf8').includes('localhost:8082'));
  const gi = fs.readFileSync(path.join(dir, '.gitignore'), 'utf8');
  for (const line of GITIGNORE_LINES) assert.ok(gi.includes(line));
  const r2 = scaffold(dir, () => {});
  assert.deepStrictEqual(r2.created, [], 'second run must be a no-op');
  assert.strictEqual(readE2eConfig(path.join(dir, 'missing')), null);
  fs.rmSync(dir, { recursive: true, force: true });
});

test('parsePlaywrightData handles nested suites, flaky, and failures', () => {
  const s = parsePlaywrightData(createSummary(), {
    stats: { duration: 5000 },
    suites: [
      {
        title: 'outer',
        specs: [{ title: 'ok', tests: [{ status: 'expected' }] }],
        suites: [
          {
            title: 'inner',
            specs: [
              { title: 'bad', tests: [{ status: 'unexpected', results: [{ error: { message: 'boom' } }] }] },
              { title: 'meh', tests: [{ status: 'flaky' }] },
              { title: 'skip', tests: [{ status: 'skipped' }] },
            ],
          },
        ],
      },
    ],
  });
  assert.deepStrictEqual(
    { total: s.total, passed: s.passed, failed: s.failed, skipped: s.skipped, flaky: s.flaky },
    { total: 4, passed: 2, failed: 1, skipped: 1, flaky: 1 }
  );
  assert.strictEqual(s.failures[0].error, 'boom');
  assert.strictEqual(s.duration, 5000);
});

test('parseVitestData and parseJunitXml aggregate counts', () => {
  const v = parseVitestData(createSummary(), {
    testResults: [
      {
        name: '/x/a.test.ts',
        assertionResults: [
          { status: 'passed', title: 'p' },
          { status: 'failed', fullName: 'a > f', failureMessages: ['nope'] },
          { status: 'pending', title: 's' },
        ],
      },
    ],
  });
  assert.deepStrictEqual({ t: v.total, p: v.passed, f: v.failed, s: v.skipped }, { t: 3, p: 1, f: 1, s: 1 });

  const j = parseJunitXml(
    createSummary(),
    `<testsuites><testsuite name="suite1" tests="3" failures="1" skipped="1" time="2.5">
       <testcase name="bad"><failure>assert blew up</failure></testcase>
     </testsuite></testsuites>`
  );
  assert.deepStrictEqual({ t: j.total, p: j.passed, f: j.failed, s: j.skipped, d: j.duration }, { t: 3, p: 1, f: 1, s: 1, d: 2500 });
  assert.strictEqual(j.failures[0].name, 'bad');
});

test('passRate and markdown verdict', () => {
  const s = createSummary();
  s.total = 4;
  s.passed = 3;
  s.failed = 1;
  s.failures.push({ name: 'x', source: 'vitest', error: 'e' });
  assert.strictEqual(passRate(s), 75);
  const md = formatMarkdown(s);
  assert.ok(md.includes('| Pass rate | 75.0% |'));
  assert.ok(md.includes('### Failures'));
});
