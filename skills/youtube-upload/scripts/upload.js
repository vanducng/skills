// Upload v.mp4 to YouTube Studio and print its id. yt.sh stages v.mp4 and meta.json here, then touches 'ready'.
const started = Date.now();
for (let i = 0; i < 60; i++) { try { await fs.stat('ready'); break; } catch { await sleep(500); } }
const meta = JSON.parse(await fs.readFile('meta.json', 'utf8'));
const P = await openTab(`https://studio.youtube.com/channel/${meta.channel}/videos/upload?d=ud&authuser=${meta.authuser ?? 0}`);
try {
  await sleep(4000);
  const channel = await P.evaluate(() => ytcfg.get('CHANNEL_ID'));
  if (channel !== meta.channel) throw new Error(`signed in to channel ${channel}, expected ${meta.channel}`);
  console.log('STEP channel ok');
  const dlg = P.locator('ytcp-uploads-dialog');
  await dlg.locator('input[type=file]').first().setInputFiles('v.mp4');
  const link = dlg.locator('a[href*="youtu.be/"]').first();
  await link.waitFor({ timeout: 60000 });
  const href = await link.getAttribute('href');
  const id = href.split(/[?#]/)[0].split('/').filter(Boolean).pop() || '';
  if (!/^[A-Za-z0-9_-]{11}$/.test(id)) throw new Error(`could not read a video id from ${href}`);
  // The video exists from here on: print the id before anything else can time out.
  console.log('RESULT', JSON.stringify({ id }));
  // Closing the tab before the bytes are sent leaves "Upload interrupted" in Studio, and a resume needs the
  // same file picked by hand. Wait for "Upload complete", inside the repl's 120 s limit.
  let text = '';
  while (Date.now() - started < 108000) {
    text = await dlg.innerText().catch(() => '');
    if (/Upload complete/i.test(text)) break;
    await sleep(1000);
  }
  if (!/Upload complete/i.test(text)) {
    const pct = (text.match(/Uploading\D{0,3}(\d+)\s*%/) || [])[1] ?? '?';
    throw new Error(`upload of ${id} not complete (${pct}%) within the time limit; it will show "Upload interrupted"`);
  }
  console.log('STEP upload complete');
} finally {
  await closeTab(P);
}
