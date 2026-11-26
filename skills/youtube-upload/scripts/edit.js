// Finish an uploaded video: title, description, thumbnail, audience, playlist, privacy.
// yt.sh stages thumb.jpg and meta.json ({channel, authuser, id, title, description, playlist, privacy}).
for (let i = 0; i < 60; i++) { try { await fs.stat('ready'); break; } catch { await sleep(500); } }
const meta = JSON.parse(await fs.readFile('meta.json', 'utf8'));
const privacy = (meta.privacy || 'private').toUpperCase();
if (!['PRIVATE', 'UNLISTED'].includes(privacy)) throw new Error(`privacy ${privacy} refused: public waits for the owner`);
const P = await openTab(`https://studio.youtube.com/video/${meta.id}/edit?authuser=${meta.authuser ?? 0}`);
try {
  await sleep(6000);
  const channel = await P.evaluate(() => ytcfg.get('CHANNEL_ID'));
  if (channel !== meta.channel) throw new Error(`signed in to channel ${channel}, expected ${meta.channel}`);
  console.log('STEP channel ok');
  const fill = async (name, text) => {
    await P.getByRole('textbox', { name }).click();
    await P.keyboard.press('ControlOrMeta+A'); await P.keyboard.press('Backspace');
    await P.keyboard.insertText(text);
  };
  await fill(/Add a title/, meta.title);
  await fill(/Tell viewers/, meta.description || '');
  await P.locator('input[type=file]').first().setInputFiles('thumb.jpg');
  await sleep(4000);
  await P.getByRole('radio', { name: "No, it's not made for kids" }).click();
  console.log('STEP details');
  if (meta.playlist) {
    await P.getByRole('button', { name: 'Select playlists' }).click();
    const pick = P.locator('ytcp-playlist-dialog');
    await pick.getByRole('searchbox').fill(meta.playlist);
    await sleep(1500);
    // The row's checkbox is a custom element: a locator click reports no change, so click it in the page.
    const toggle = (el, [name, click]) => {
      const rows = [...el.querySelectorAll('ytcp-ve.row-content')]
        .filter(r => r.querySelector('.label-text')?.textContent.trim() === name);
      if (rows.length !== 1) return `found ${rows.length} times`;
      const box = rows[0].querySelector('#checkbox');
      if (!box) return 'found without a checkbox';
      if (click && box.getAttribute('aria-checked') !== 'true') box.click();
      return String(box.getAttribute('aria-checked'));
    };
    const found = await pick.evaluate(toggle, [meta.playlist, true]);
    if (found.startsWith('found')) throw new Error(`playlist "${meta.playlist}" ${found}; create it once in Studio first`);
    await sleep(1000);
    if (await pick.evaluate(toggle, [meta.playlist, false]) !== 'true') throw new Error(`playlist "${meta.playlist}" did not stay checked`);
    await pick.getByRole('button', { name: 'Done' }).click();
    await sleep(1000);
    console.log('STEP playlist');
  }
  const save = P.getByRole('button', { name: 'Save' });
  if (await save.isEnabled()) { await save.click(); await sleep(5000); }
  console.log('STEP saved');
  // An upload whose wizard was closed early stays a draft until its Visibility step is finished.
  const draft = P.getByRole('button', { name: 'Edit draft' });
  if (await draft.count()) {
    await draft.click();
    const dlg = P.locator('ytcp-uploads-dialog');
    await dlg.locator('#next-button').waitFor({ timeout: 30000 });
    await sleep(2000);
    for (let i = 0; i < 3; i++) { await dlg.locator('#next-button').click(); await sleep(1500); }
    const radio = dlg.locator(`tp-yt-paper-radio-button[name=${privacy}]`);
    await radio.click();
    await sleep(1000);
    // A locator click on these custom elements can report success and change nothing: read it back.
    if (await radio.getAttribute('aria-checked') !== 'true') throw new Error(`${privacy} did not stay selected; nothing saved`);
    await dlg.locator('#done-button').click();
    await sleep(5000);
    console.log(`STEP ${privacy.toLowerCase()}`);
  } else {
    console.log('STEP not a draft: visibility left as it is; status reads it back');
  }
} finally {
  await closeTab(P);
}
