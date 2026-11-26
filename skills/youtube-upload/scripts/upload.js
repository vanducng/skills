// Upload v.mp4 to YouTube Studio and print its id. yt.sh stages v.mp4 and meta.json here, then touches 'ready'.
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
} finally {
  await closeTab(P);
}
