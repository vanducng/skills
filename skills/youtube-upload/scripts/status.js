// Read back each video as Studio shows it. yt.sh stages meta.json ({channel, authuser, playlist, ids}).
for (let i = 0; i < 60; i++) { try { await fs.stat('ready'); break; } catch { await sleep(500); } }
const meta = JSON.parse(await fs.readFile('meta.json', 'utf8'));
for (const id of meta.ids) {
  const P = await openTab(`https://studio.youtube.com/video/${id}/edit?authuser=${meta.authuser ?? 0}`);
  try {
    await sleep(7000);
    const channel = await P.evaluate(() => ytcfg.get('CHANNEL_ID'));
    if (channel !== meta.channel) throw new Error(`signed in to channel ${channel}, expected ${meta.channel}`);
    const text = await P.evaluate(() => document.body.innerText);
    // Only the playlist control counts: the title on the same page usually carries the series name too.
    const playlists = await P.evaluate(() => document.querySelector('ytcp-video-metadata-playlists')?.innerText ?? null);
    const kids = await P.getByRole('radio', { name: "Yes, it's made for kids" }).getAttribute('aria-checked').catch(() => null);
    console.log('RESULT', JSON.stringify({
      id,
      link: `https://youtu.be/${id}`,
      channel,
      title: await P.getByRole('textbox', { name: /Add a title/ }).innerText(),
      // Pending means YouTube's checks have not run yet; the chosen privacy applies after them.
      visibility: (text.match(/Visibility\n(\w+)/) || [])[1] || 'unknown',
      draft: /draft state/.test(text),
      playlist: meta.playlist && playlists !== null ? playlists.includes(meta.playlist) : null,
      customThumbnail: await P.getByRole('button', { name: 'Uploaded thumbnail' }).count() === 1,
      ...(kids === null ? {} : { madeForKids: kids === 'true' }),
    }));
  } finally {
    await closeTab(P);
  }
}
