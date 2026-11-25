// Read back each video as Studio shows it. yt.sh stages meta.json ({channel, authuser, playlist, ids}).
for (let i = 0; i < 60; i++) { try { await fs.stat('ready'); break; } catch { await sleep(500); } }
const meta = JSON.parse(await fs.readFile('meta.json', 'utf8'));
for (const id of meta.ids) {
  const P = await openTab(`https://studio.youtube.com/video/${id}/edit?authuser=${meta.authuser ?? 0}`);
  try {
    await sleep(7000);
    const text = await P.evaluate(() => document.body.innerText);
    console.log('RESULT', JSON.stringify({
      id,
      link: `https://youtu.be/${id}`,
      channel: await P.evaluate(() => ytcfg.get('CHANNEL_ID')),
      title: await P.getByRole('textbox', { name: /Add a title/ }).innerText(),
      // Pending means YouTube's checks have not run yet; the chosen privacy applies after them.
      visibility: (text.match(/Visibility\n(\w+)/) || [])[1] || 'unknown',
      draft: /draft state/.test(text),
      playlist: meta.playlist ? text.includes(meta.playlist) : null,
      customThumbnail: await P.getByRole('button', { name: 'Uploaded thumbnail' }).count() === 1,
      madeForKids: !/not made for kids/.test(text),
    }));
  } finally {
    await closeTab(P);
  }
}
