#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const { connectToPage, parseArgs } = require('./cdp.cjs');

const TRACE_CATEGORIES = [
  'devtools.timeline',
  'disabled-by-default-devtools.timeline',
  'disabled-by-default-devtools.timeline.frame',
  'v8.execute',
  'blink.user_timing',
];

// Long task = top-level main-thread task over 50ms (the RAIL/INP blocking threshold).
function summarizeTrace(events) {
  const longTasks = [];
  const byName = new Map();
  for (const e of events) {
    if (e.ph !== 'X' || typeof e.dur !== 'number') continue;
    const ms = e.dur / 1000;
    const agg = byName.get(e.name) || { count: 0, totalMs: 0 };
    agg.count += 1;
    agg.totalMs += ms;
    byName.set(e.name, agg);
    if (e.name === 'RunTask' && ms > 50) longTasks.push({ startUs: e.ts, durMs: Math.round(ms * 10) / 10 });
  }
  const top = [...byName.entries()]
    .map(([name, a]) => ({ name, count: a.count, totalMs: Math.round(a.totalMs) }))
    .sort((a, b) => b.totalMs - a.totalMs)
    .slice(0, 10);
  return { events: events.length, longTasks, topByTotalDuration: top };
}

async function readStream(session, handle) {
  let data = '';
  for (;;) {
    const chunk = await session.send('IO.read', { handle, size: 1048576 });
    data += chunk.base64Encoded ? Buffer.from(chunk.data, 'base64').toString('utf8') : chunk.data;
    if (chunk.eof) break;
  }
  await session.send('IO.close', { handle }).catch(() => {});
  return data;
}

async function main() {
  const args = parseArgs(process.argv.slice(2), { out: 'trace.json' });
  if (!args.port || !args.url) {
    console.error('usage: perf-trace.cjs --port <cdp-port> --url <navigate-to> [--out trace.json] [--settle <ms>] [--json]');
    process.exit(2);
  }
  const session = await connectToPage(args.port, args.match);
  try {
    await session.send('Page.enable');
    await session.send('Page.bringToFront').catch(() => {});
    await session.send('Tracing.start', {
      transferMode: 'ReturnAsStream',
      traceConfig: { includedCategories: TRACE_CATEGORIES },
    });
    const loaded = session.once('Page.loadEventFired', 45000);
    await session.send('Page.navigate', { url: args.url });
    await loaded;
    await new Promise((r) => setTimeout(r, Number(args.settle) || 1500));

    const complete = session.once('Tracing.tracingComplete', 30000);
    await session.send('Tracing.end');
    const { stream } = await complete;
    const raw = await readStream(session, stream);
    fs.writeFileSync(args.out, raw);

    const parsed = JSON.parse(raw);
    const summary = summarizeTrace(Array.isArray(parsed) ? parsed : parsed.traceEvents || []);
    const out = { url: args.url, trace: args.out, ...summary };
    if (args.json) {
      console.log(JSON.stringify(out, null, 2));
    } else {
      console.log(`trace   ${out.trace} (${out.events} events) — load in DevTools Performance panel`);
      console.log(`tasks   ${out.longTasks.length} long task(s) >50ms${out.longTasks.length ? ` · worst ${Math.max(...out.longTasks.map((t) => t.durMs))}ms` : ''}`);
      for (const t of out.topByTotalDuration.slice(0, 5)) console.log(`        ${t.name} ×${t.count} = ${t.totalMs}ms`);
    }
  } finally {
    session.close();
  }
}

module.exports = { TRACE_CATEGORIES, summarizeTrace };

if (require.main === module) {
  main().catch((err) => {
    console.error(`perf-trace: ${err.message}`);
    process.exit(1);
  });
}
