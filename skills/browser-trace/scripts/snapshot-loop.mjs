#!/usr/bin/env node
// Periodic screenshot + DOM HTML + URL sampler. Invoked by start-capture.mjs;
// not meant to be run directly.
//
// One persistent raw-CDP connection is reused across ticks (Page.captureScreenshot,
// Runtime.evaluate) instead of spawning a process per sample. If the socket
// drops, the next tick reconnects instead of crashing the loop.

import fs from 'node:fs';
import path from 'node:path';

import { cdpConnect, isoStampForFilename, sleepMs } from './lib.mjs';

const [target, RD, intervalArg] = process.argv.slice(2);
if (!target || !RD) {
  console.error('usage: snapshot-loop.mjs <target> <run-dir> [interval-seconds]');
  process.exit(2);
}

const intervalMs = (Number(intervalArg) || 2) * 1000;
const indexPath = path.join(RD, 'index.jsonl');

let stopping = false;
let client = null;
function onSignal() {
  stopping = true;
  client?.close();
}
process.on('SIGTERM', onSignal);
process.on('SIGINT',  onSignal);

async function ensureClient() {
  if (client) return client;
  try {
    client = await cdpConnect(target, { onClose: () => { client = null; } });
  } catch {
    client = null;
  }
  return client;
}

async function evalString(expression) {
  const r = await client.send('Runtime.evaluate', { expression, returnByValue: true });
  return typeof r?.result?.value === 'string' ? r.result.value : '';
}

while (!stopping) {
  const ts   = isoStampForFilename();
  const png  = path.join(RD, 'screenshots', `${ts}.png`);
  const html = path.join(RD, 'dom',         `${ts}.html`);
  const tmp  = `${html}.partial`;
  let urlValue = '';

  if (await ensureClient()) {
    // Best-effort screenshot. If the command fails we just don't get one this tick.
    try {
      const shot = await client.send('Page.captureScreenshot', { format: 'png' });
      if (shot?.data) fs.writeFileSync(png, Buffer.from(shot.data, 'base64'));
    } catch { /* best-effort */ }

    // DOM dump via temp file → rename, so we never leave a 0-byte HTML behind.
    try {
      const htmlBody = await evalString('document.body.outerHTML');
      if (htmlBody) {
        fs.writeFileSync(tmp, htmlBody);
        fs.renameSync(tmp, html);
      }
    } catch { /* best-effort */ }

    try {
      urlValue = await evalString('location.href');
    } catch { /* best-effort */ }
  }

  // Cleanup any leftover .partial from a previous interrupted iteration.
  if (fs.existsSync(tmp)) {
    try { fs.unlinkSync(tmp); } catch {}
  }

  const screenshotRel = fs.existsSync(png)  ? `screenshots/${ts}.png` : '';
  const domRel        = fs.existsSync(html) ? `dom/${ts}.html`        : '';
  fs.appendFileSync(indexPath,
    JSON.stringify({ ts, screenshot: screenshotRel, dom: domRel, url: urlValue }) + '\n');

  await sleepMs(intervalMs);
}

client?.close();
