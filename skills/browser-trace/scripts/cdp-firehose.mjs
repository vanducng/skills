#!/usr/bin/env node
// Zero-dep CDP firehose: attach to a page target and stream every protocol
// event as one JSON object per line to stdout ({method, params, ts}).
// start-capture.mjs redirects stdout to cdp/raw.ndjson.
//
// Usage:
//   node scripts/cdp-firehose.mjs <port|ws-url>
//
// Env:
//   O11Y_DOMAINS  space-separated CDP domains to enable
//                 (default: "Network Console Runtime Log Page")

import { cdpConnect } from './lib.mjs';

const [target] = process.argv.slice(2);
if (!target) {
  console.error('usage: cdp-firehose.mjs <port|ws-url>');
  process.exit(2);
}

const domains = (process.env.O11Y_DOMAINS || 'Network Console Runtime Log Page').trim().split(/\s+/);

let client = null;
function shutdown() {
  client?.close();
  process.exit(0);
}
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);

try {
  client = await cdpConnect(target, {
    onEvent: (ev) => {
      process.stdout.write(JSON.stringify({ method: ev.method, params: ev.params, ts: Date.now() }) + '\n');
    },
    onClose: () => process.exit(0),
  });
} catch (err) {
  console.error(`cdp-firehose: ${err.message}`);
  process.exit(1);
}

for (const d of domains) {
  try {
    await client.send(`${d}.enable`);
  } catch (err) {
    console.error(`cdp-firehose: ${d}.enable failed: ${err.message}`);
  }
}

// Without this, Page.lifecycleEvent never fires and page/lifecycle.jsonl stays empty.
if (domains.includes('Page')) {
  try {
    await client.send('Page.setLifecycleEventsEnabled', { enabled: true });
  } catch (err) {
    console.error(`cdp-firehose: Page.setLifecycleEventsEnabled failed: ${err.message}`);
  }
}
