#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');

function createSummary() {
  return { total: 0, passed: 0, failed: 0, skipped: 0, flaky: 0, duration: 0, suites: [], failures: [] };
}

function parsePlaywrightData(summary, data) {
  const walk = (suite) => {
    const agg = { name: suite.title || suite.file || 'Unknown', source: 'playwright', passed: 0, failed: 0, skipped: 0 };
    for (const spec of suite.specs || []) {
      for (const test of spec.tests || []) {
        summary.total++;
        if (test.status === 'expected') {
          summary.passed++;
          agg.passed++;
        } else if (test.status === 'unexpected') {
          summary.failed++;
          agg.failed++;
          summary.failures.push({
            name: `${suite.title} > ${spec.title}`,
            source: 'playwright',
            error: (test.results && test.results[0] && test.results[0].error && test.results[0].error.message) || 'Unknown error',
          });
        } else if (test.status === 'skipped') {
          summary.skipped++;
          agg.skipped++;
        } else if (test.status === 'flaky') {
          summary.flaky++;
          summary.passed++;
          agg.passed++;
        }
      }
    }
    for (const child of suite.suites || []) walk(child);
    if (agg.passed + agg.failed + agg.skipped > 0) summary.suites.push(agg);
  };
  for (const suite of data.suites || []) walk(suite);
  summary.duration += (data.stats && data.stats.duration) || 0;
  return summary;
}

function parseVitestData(summary, data) {
  for (const file of data.testResults || []) {
    const agg = { name: path.basename(file.name || 'unknown'), source: 'vitest', passed: 0, failed: 0, skipped: 0 };
    for (const test of file.assertionResults || []) {
      summary.total++;
      if (test.status === 'passed') {
        summary.passed++;
        agg.passed++;
      } else if (test.status === 'failed') {
        summary.failed++;
        agg.failed++;
        summary.failures.push({
          name: test.fullName || test.title,
          source: 'vitest',
          error: (test.failureMessages && test.failureMessages[0]) || 'Unknown error',
        });
      } else if (test.status === 'skipped' || test.status === 'pending') {
        summary.skipped++;
        agg.skipped++;
      }
    }
    summary.suites.push(agg);
  }
  return summary;
}

// Regex JUnit parsing keeps this dependency-free; nested <testsuites>/CDATA edge
// cases are out of scope — Playwright/Vitest JSON are the first-class inputs.
function parseJunitXml(summary, xml) {
  for (const ts of xml.match(/<testsuite[^>]*>/g) || []) {
    const attr = (name) => (ts.match(new RegExp(`${name}="([^"]*)"`)) || [])[1];
    const tests = parseInt(attr('tests') || '0', 10);
    const failures = parseInt(attr('failures') || '0', 10);
    const skipped = parseInt(attr('skipped') || '0', 10);
    summary.total += tests;
    summary.passed += tests - failures - skipped;
    summary.failed += failures;
    summary.skipped += skipped;
    summary.duration += parseFloat(attr('time') || '0') * 1000;
    summary.suites.push({ name: attr('name') || 'Unknown', source: 'junit', passed: tests - failures - skipped, failed: failures, skipped });
  }
  for (const m of xml.matchAll(/<testcase[^>]*name="([^"]+)"[^>]*>[\s\S]*?<failure[^>]*>([\s\S]*?)<\/failure>/g)) {
    summary.failures.push({ name: m[1], source: 'junit', error: m[2].trim().slice(0, 200) });
  }
  return summary;
}

function passRate(summary) {
  return summary.total > 0 ? (summary.passed / summary.total) * 100 : 0;
}

function formatMarkdown(summary) {
  const lines = [
    '## Test Results Summary',
    '',
    '| Metric | Value |',
    '|--------|-------|',
    `| Total | ${summary.total} |`,
    `| Passed | ${summary.passed} |`,
    `| Failed | ${summary.failed} |`,
    `| Skipped | ${summary.skipped} |`,
    `| Pass rate | ${passRate(summary).toFixed(1)}% |`,
    `| Duration | ${(summary.duration / 1000).toFixed(2)}s |`,
  ];
  if (summary.failures.length) {
    lines.push('', '### Failures', '');
    for (const f of summary.failures.slice(0, 10)) lines.push(`- **[${f.source}]** ${f.name} — ${f.error.slice(0, 120)}`);
    if (summary.failures.length > 10) lines.push(`- … and ${summary.failures.length - 10} more`);
  }
  return lines.join('\n');
}

function formatText(summary) {
  const lines = [
    `total ${summary.total} · passed ${summary.passed} · failed ${summary.failed} · skipped ${summary.skipped}${summary.flaky ? ` · flaky ${summary.flaky}` : ''}`,
    `pass rate ${passRate(summary).toFixed(1)}% · ${(summary.duration / 1000).toFixed(2)}s`,
  ];
  for (const f of summary.failures.slice(0, 10)) lines.push(`FAIL [${f.source}] ${f.name}: ${f.error.slice(0, 100)}`);
  return lines.join('\n');
}

function main() {
  const args = process.argv.slice(2);
  const get = (name) => {
    const i = args.indexOf(`--${name}`);
    return i !== -1 ? args[i + 1] : null;
  };
  const summary = createSummary();
  const read = (p) => fs.readFileSync(p, 'utf8');
  if (get('playwright')) parsePlaywrightData(summary, JSON.parse(read(get('playwright'))));
  if (get('vitest')) parseVitestData(summary, JSON.parse(read(get('vitest'))));
  if (get('junit')) parseJunitXml(summary, read(get('junit')));

  if (summary.total === 0) {
    console.error('no results parsed — pass --playwright/--vitest <results.json> or --junit <results.xml>');
    process.exit(2);
  }

  const format = get('output') || 'text';
  console.log(format === 'json' ? JSON.stringify(summary, null, 2) : format === 'markdown' ? formatMarkdown(summary) : formatText(summary));

  const threshold = parseInt(get('fail-threshold') || '0', 10);
  if ((threshold > 0 && passRate(summary) < threshold) || summary.failed > 0) process.exit(1);
}

module.exports = { createSummary, parsePlaywrightData, parseVitestData, parseJunitXml, passRate, formatMarkdown, formatText };

if (require.main === module) main();
