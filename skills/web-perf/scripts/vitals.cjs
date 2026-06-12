#!/usr/bin/env node
'use strict';

const { connectToPage, parseArgs } = require('./cdp.cjs');

// Buffered observers so metrics recorded before attach still surface. INP needs real
// interactions — null on a fresh load is correct, not a failure. FID is dead (2024).
const VITALS_EXPRESSION = `new Promise((resolve) => {
  const vitals = { LCP: null, CLS: 0, FCP: null, TTFB: null, INP: null };
  try {
    new PerformanceObserver((list) => {
      const entries = list.getEntries();
      if (entries.length) { const last = entries[entries.length - 1]; vitals.LCP = last.renderTime || last.loadTime; }
    }).observe({ type: 'largest-contentful-paint', buffered: true });
  } catch (e) {}
  try {
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) if (!entry.hadRecentInput) vitals.CLS += entry.value;
    }).observe({ type: 'layout-shift', buffered: true });
  } catch (e) {}
  try {
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.interactionId && (vitals.INP === null || entry.duration > vitals.INP)) vitals.INP = entry.duration;
      }
    }).observe({ type: 'event', buffered: true, durationThreshold: 16 });
  } catch (e) {}
  try {
    const fcp = performance.getEntriesByType('paint').find((e) => e.name === 'first-contentful-paint');
    if (fcp) vitals.FCP = fcp.startTime;
  } catch (e) {}
  try {
    const [nav] = performance.getEntriesByType('navigation');
    if (nav) vitals.TTFB = nav.responseStart - nav.requestStart;
  } catch (e) {}
  const resources = performance.getEntriesByType('resource');
  setTimeout(() => resolve(JSON.stringify({
    vitals,
    resources: {
      count: resources.length,
      totalDurationMs: Math.round(resources.reduce((s, r) => s + r.duration, 0)),
      transferBytes: resources.reduce((s, r) => s + (r.transferSize || 0), 0),
    },
  })), 1000);
})`;

function round(v) {
  return v === null || v === undefined ? null : Math.round(v * 100) / 100;
}

function formatVitals(payload, heap) {
  const v = payload.vitals;
  return {
    vitals: { LCP: round(v.LCP), CLS: round(v.CLS), FCP: round(v.FCP), TTFB: round(v.TTFB), INP: round(v.INP) },
    resources: payload.resources,
    heap,
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.port) {
    console.error('usage: vitals.cjs --port <cdp-port> [--url <navigate-to>] [--match <tab-url-substring>] [--json]');
    process.exit(2);
  }
  const session = await connectToPage(args.port, args.match);
  try {
    if (args.url) {
      await session.send('Page.enable');
      // Background tabs don't paint — without focus LCP/FCP never fire.
      await session.send('Page.bringToFront').catch(() => {});
      const loaded = session.once('Page.loadEventFired', 30000);
      await session.send('Page.navigate', { url: args.url });
      await loaded;
      await new Promise((r) => setTimeout(r, 500));
    }
    const evalRes = await session.send('Runtime.evaluate', {
      expression: VITALS_EXPRESSION,
      awaitPromise: true,
      returnByValue: true,
    });
    if (evalRes.exceptionDetails) throw new Error(evalRes.exceptionDetails.text || 'vitals evaluation failed');
    const payload = JSON.parse(evalRes.result.value);

    await session.send('Performance.enable');
    const { metrics } = await session.send('Performance.getMetrics');
    const metric = (name) => (metrics.find((m) => m.name === name) || {}).value || 0;
    const heap = {
      usedMB: round(metric('JSHeapUsedSize') / 1048576),
      totalMB: round(metric('JSHeapTotalSize') / 1048576),
      documents: metric('Documents'),
      nodes: metric('Nodes'),
    };

    const out = { url: args.url || session.targetUrl, ...formatVitals(payload, heap) };
    if (args.json) {
      console.log(JSON.stringify(out, null, 2));
    } else {
      const v = out.vitals;
      console.log(`url     ${out.url}`);
      console.log(`vitals  LCP ${v.LCP}ms · FCP ${v.FCP}ms · TTFB ${v.TTFB}ms · CLS ${v.CLS} · INP ${v.INP === null ? 'n/a (no interactions yet)' : `${v.INP}ms`}`);
      console.log(`heap    ${heap.usedMB}MB used / ${heap.totalMB}MB · ${heap.nodes} nodes`);
      console.log(`network ${out.resources.count} resources · ${out.resources.totalDurationMs}ms total · ${Math.round(out.resources.transferBytes / 1024)}KB`);
    }
  } finally {
    session.close();
  }
}

module.exports = { VITALS_EXPRESSION, formatVitals, round };

if (require.main === module) {
  main().catch((err) => {
    console.error(`vitals: ${err.message}`);
    process.exit(1);
  });
}
