'use strict';

const test = require('node:test');
const assert = require('node:assert');
const http = require('node:http');

const { pickPageTarget, parseArgs, waitForCdp, listTargets } = require('./cdp.cjs');
const { VITALS_EXPRESSION, formatVitals, round } = require('./vitals.cjs');
const { summarizeTrace, TRACE_CATEGORIES } = require('./perf-trace.cjs');

test('pickPageTarget skips chrome:// and devtools targets, honors url filter', () => {
  const targets = [
    { type: 'page', url: 'chrome://newtab/' },
    { type: 'iframe', url: 'http://app.test/frame' },
    { type: 'page', url: 'devtools://devtools/bundled' },
    { type: 'page', url: 'http://localhost:8082/admin' },
    { type: 'page', url: 'http://localhost:21460/dashboard' },
  ];
  assert.strictEqual(pickPageTarget(targets).url, 'http://localhost:8082/admin');
  assert.strictEqual(pickPageTarget(targets, '21460').url, 'http://localhost:21460/dashboard');
  assert.strictEqual(pickPageTarget(targets, 'nope'), null);
  assert.strictEqual(pickPageTarget([]), null);
});

test('parseArgs handles values, flags, and defaults', () => {
  assert.deepStrictEqual(parseArgs(['--port', '9382', '--json', '--out', 't.json'], { out: 'trace.json' }), {
    port: '9382',
    json: true,
    out: 't.json',
  });
  assert.deepStrictEqual(parseArgs([], { settle: '1500' }), { settle: '1500' });
});

test('VITALS_EXPRESSION is syntactically valid and FID-free', () => {
  assert.doesNotThrow(() => new Function(`return ${VITALS_EXPRESSION}`));
  assert.ok(!VITALS_EXPRESSION.includes('FID'), 'FID is deprecated; INP replaces it');
  for (const metric of ['LCP', 'CLS', 'FCP', 'TTFB', 'INP']) assert.ok(VITALS_EXPRESSION.includes(metric));
});

test('formatVitals rounds and preserves null INP', () => {
  const out = formatVitals(
    { vitals: { LCP: 1234.5678, CLS: 0.05123, FCP: 800.111, TTFB: 12.345, INP: null }, resources: { count: 3 } },
    { usedMB: 10 }
  );
  assert.deepStrictEqual(out.vitals, { LCP: 1234.57, CLS: 0.05, FCP: 800.11, TTFB: 12.35, INP: null });
  assert.strictEqual(round(null), null);
});

test('summarizeTrace finds long tasks and aggregates by name', () => {
  const us = (ms) => ms * 1000;
  const events = [
    { ph: 'X', name: 'RunTask', ts: 1, dur: us(80) },
    { ph: 'X', name: 'RunTask', ts: 2, dur: us(10) },
    { ph: 'X', name: 'FunctionCall', ts: 3, dur: us(30) },
    { ph: 'X', name: 'FunctionCall', ts: 4, dur: us(40) },
    { ph: 'B', name: 'NotComplete', ts: 5 },
    { ph: 'X', name: 'NoDur', ts: 6 },
  ];
  const s = summarizeTrace(events);
  assert.strictEqual(s.events, 6);
  assert.strictEqual(s.longTasks.length, 1);
  assert.strictEqual(s.longTasks[0].durMs, 80);
  assert.deepStrictEqual(s.topByTotalDuration[0], { name: 'RunTask', count: 2, totalMs: 90 });
  assert.deepStrictEqual(s.topByTotalDuration[1], { name: 'FunctionCall', count: 2, totalMs: 70 });
});

test('TRACE_CATEGORIES covers the DevTools timeline set', () => {
  for (const cat of ['devtools.timeline', 'disabled-by-default-devtools.timeline']) {
    assert.ok(TRACE_CATEGORIES.includes(cat));
  }
});

test('listTargets/waitForCdp behave against a mock endpoint and a dead port', async () => {
  const server = http.createServer((req, res) => {
    if (req.url === '/json/list') return res.writeHead(200).end(JSON.stringify([{ type: 'page', url: 'http://x/' }]));
    if (req.url === '/json/version') return res.writeHead(200).end('{}');
    res.writeHead(404).end();
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const port = server.address().port;
  assert.strictEqual((await listTargets(port))[0].url, 'http://x/');
  assert.strictEqual(await waitForCdp(port, 1000), true);
  server.close();
  assert.strictEqual(await waitForCdp(1, 600), false);
});
