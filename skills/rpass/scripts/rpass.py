#!/usr/bin/env python3
"""Create, update and share RPass (Rippling password manager) notes through the Aside browser, without printing secrets.

RPass has no CLI or API: the vault lives in its browser extension. This drives the extension page and the Rippling
share page with `aside repl`. Values travel only inside a mode-600 generated script that is deleted after the run;
only lines the generated script prefixes with "RPASS:" are printed.

  rpass.py envblocks --out note.env services/api/.env services/worker/.env ...
  rpass.py put   --account u1 --name team-api-keys --body-file note.env [--vault "Acme Vault"]
  rpass.py share --account u1 --name team-api-keys --add "Teams > Platform Team" --access manage [--remove "Jane Doe"]
  rpass.py access --account u1 --name team-api-keys
  rpass.py remove --account u1 --name team-api-keys --yes
"""
import argparse, json, os, re, stat, subprocess, sys, tempfile

EXT_ID = "mobhfbcgjoleoljhpkkdhopdiemlocka"  # the public RPass Chrome extension; override with --ext-id
LEVELS = {"use": "Use but not view", "view": "Use and view", "manage": "Manage"}


def envblocks(args):
    out = [f"# {args.title}" if args.title else None, "# Copy each block into the file named in its header. Never commit .env.", ""]
    out = [l for l in out if l is not None]
    for path in args.files:
        keys = [l.rstrip("\n") for l in open(path) if "=" in l and not l.lstrip().startswith("#") and l.strip()]
        out += [f"# ===== {path} =====", *keys, ""]
    body = "\n".join(out).rstrip() + "\n"
    fd = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)  # an existing file keeps its old mode otherwise
    with os.fdopen(fd, "w") as f:
        f.write(body)
    n = sum(1 for l in body.splitlines() if "=" in l and not l.startswith("#"))
    print(f"wrote {args.out} (mode 600): {n} keys from {len(args.files)} files")


JS_OPEN_ITEM = """
const say = (...a) => console.log('RPASS:', ...a);
const EXT = %(ext)s, NAME = %(name)s;
await openTab(`chrome-extension://${EXT}/index.html`); await sleep(4000);
async function findItem() {
  await page.locator('input').first().fill(NAME); await sleep(2500);
  const hit = page.getByText(NAME, { exact: true });
  const n = await hit.count();
  if (n > 1) { say('ABORT:', n, 'notes are named', JSON.stringify(NAME)); throw new Error('ambiguous note'); }
  return n ? hit.first() : null;
}
async function itemMenu(label) {
  const pos = await page.evaluate(() => {
    const back = document.querySelector('[data-testid=item-header-back-button]'); if (!back) return null;
    const b = back.getBoundingClientRect();
    const c = [...document.querySelectorAll('[data-testid=test_button]')].map(e => e.getBoundingClientRect())
      .filter(r => Math.abs(r.y - b.y) < 20 && r.x > b.x).sort((x, y) => x.x - y.x).pop();
    return c ? { x: c.x + c.width / 2, y: c.y + c.height / 2 } : null;
  });
  if (!pos) throw new Error('item menu not found');
  await page.mouse.click(pos.x, pos.y); await sleep(1200);
  await page.getByText(label, { exact: true }).first().click(); await sleep(2500);
}
"""

JS_PUT = JS_OPEN_ITEM + """
const BODY = %(body)s, VAULT = %(vault)s;
// The note form shows a vault picker on create only; an opened item shows a "Vault <name>" label instead.
const itemVault = () => page.evaluate(() => {
  const l = [...document.querySelectorAll('*')].find(e => e.childElementCount === 0 && (e.textContent || '').trim() === 'Vault');
  let p = l && l.parentElement; while (p && (p.innerText || '').trim() === 'Vault') p = p.parentElement;
  return p ? (p.innerText || '').replace(/\\s+/g, ' ').replace(/^Vault /, '').trim() : '';
});
const item = await findItem();
let v;
if (item) { await item.click(); await sleep(3000); v = await itemVault(); }
else {
  await page.getByRole('button', { name: 'Add' }).first().click(); await sleep(1200);
  await page.getByText('Note', { exact: true }).first().click(); await sleep(2500);
  v = await page.getByPlaceholder('Search vaults').inputValue();
}
if (!v || (VAULT && v.toLowerCase() !== VAULT.toLowerCase()) || /^Personal/i.test(v)) {
  say('ABORT: vault is', JSON.stringify(v), VAULT ? `(expected ${JSON.stringify(VAULT)})` : '(personal vault items cannot be shared)'); throw new Error('vault');
}
if (item) await itemMenu('Edit');
say(item ? 'editing existing note in vault' : 'creating in vault', JSON.stringify(v));
await page.getByPlaceholder('Name this note').fill(NAME);
await page.getByPlaceholder('Type your note here').fill(BODY);
const ok = (await page.getByPlaceholder('Name this note').inputValue()) === NAME
  && (await page.getByPlaceholder('Type your note here').inputValue()) === BODY;
if (!ok) { say('ABORT: field check failed'); await page.getByRole('button', { name: 'Cancel' }).click(); throw new Error('fields'); }
await page.getByRole('button', { name: item ? 'Save' : 'Create' }).click(); await sleep(3500);
await openTab(`chrome-extension://${EXT}/index.html`); await sleep(4000);
say('saved; listed:', !!(await findItem()), '; body chars:', BODY.length);
"""

JS_SHARE = JS_OPEN_ITEM + """
const ADD = %(add)s, REMOVE = %(remove)s, LEVEL = %(level)s, CHANGE = %(change)s;
const item = await findItem(); if (!item) { say('ABORT: no note named', NAME); throw new Error('missing'); }
await item.click(); await sleep(3000);
const m = page.url().match(/vault\\/([^/]+)\\/.*item\\/([^/?#]+)/); if (!m) { say('ABORT: item url'); throw new Error('url'); }
await openTab(`https://app.rippling.com/rpass/share/vault/${m[1]}/item/${m[2]}?rpassId=${EXT}`); await sleep(8000);
const table = () => page.evaluate(() => { const s = (document.querySelector('main') || document.body).innerText; const i = s.indexOf('People with access'); const j = s.indexOf('Preview people'); return s.slice(i, j > i ? j : i + 800).replace(/\\s+/g, ' '); });
const row = who => page.locator('tr,[role=row]').filter({ hasText: who }).first();
for (const who of ADD) {
  const box = page.getByPlaceholder('Search for people or groups');
  await box.click(); await sleep(600); await box.fill(''); await box.type(who.split(/ [>→] /).pop(), { delay: 70 }); await sleep(3500);
  let opts = page.locator('li'); for (const w of who.split(/[ >→]+/).filter(Boolean)) opts = opts.filter({ hasText: w });
  const n = await opts.count();
  if (n !== 1) { say('ABORT:', JSON.stringify(who), 'matched', n, 'entries'); throw new Error('ambiguous'); }
  await opts.first().click(); await sleep(1500);
}
for (const who of REMOVE) { await row(who.split(/ [>→] /).pop()).getByTestId('remove-recipient-icon').click(); await sleep(1200); }
if (LEVEL) for (const who of [...ADD, ...CHANGE]) {
  await row(who.split(/ [>→] /).pop()).locator('[role=combobox]').first().click(); await sleep(1200);
  await page.locator('[role=option],li').filter({ hasText: new RegExp('^' + LEVEL) }).first().click(); await sleep(1200);
}
say('pending:', await table());
await page.getByTestId('share-modal-share-button').click(); await sleep(6000);
say('result:', /Sharing settings updated/.test(await page.evaluate(() => document.body.innerText)) ? 'updated' : 'NOT CONFIRMED');
"""

JS_REMOVE = JS_OPEN_ITEM + """
const item = await findItem(); if (!item) { say('no note named', NAME); throw new Error('missing'); }
await item.click(); await sleep(3000); await itemMenu('Remove');
const confirm = page.getByRole('button', { name: /^(Remove|Delete)$/ }).last();
if (await confirm.count()) { await confirm.click(); await sleep(3000); }
await openTab(`chrome-extension://${EXT}/index.html`); await sleep(4000);
say('removed:', !(await findItem()));
"""

JS_ACCESS = JS_OPEN_ITEM + """
const item = await findItem(); if (!item) { say('no note named', NAME); throw new Error('missing'); }
await item.click(); await sleep(3000);
const m = page.url().match(/vault\\/([^/]+)\\/.*item\\/([^/?#]+)/);
await openTab(`https://app.rippling.com/rpass/share/vault/${m[1]}/item/${m[2]}?rpassId=${EXT}`); await sleep(8000);
say(await page.evaluate(() => { const s = (document.querySelector('main') || document.body).innerText; const i = s.indexOf('People with access'); const j = s.indexOf('Preview people'); return s.slice(i, j > i ? j : i + 800).replace(/\\s+/g, ' '); }));
await page.getByRole('button', { name: 'Preview people' }).click(); await sleep(3500);
say('resolved:', await page.evaluate(() => { const d = document.querySelector('[role=dialog]') || document.body; const s = d.innerText; const i = s.indexOf('Employee'); return s.slice(i, i + 1500).replace(/\\s+/g, ' '); }));
"""


def run(account, js):
    # The repl's fs only reaches its own session and project roots, so values go into the script itself.
    fd, path = tempfile.mkstemp(suffix=".js")
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "w") as f:
            f.write(js)
        try:
            p = subprocess.run(["aside", "repl", "--account", account, "--file", path], capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired:
            sys.exit("aside repl did not finish in 10 minutes; check the browser and rerun")
    finally:
        os.unlink(path)
    lines = [l for l in (p.stdout + p.stderr).splitlines() if l.startswith("RPASS:")]
    print("\n".join(l[7:] for l in lines) or "(no RPASS output)")
    if p.returncode or any("ABORT" in l for l in lines):
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("envblocks", help="build a copy-paste .env note body from .env files")
    e.add_argument("--out", required=True); e.add_argument("--title", default=""); e.add_argument("files", nargs="+")
    for name in ("put", "share", "access", "remove"):
        s = sub.add_parser(name)
        s.add_argument("--account", required=True, help="Aside account or account:profile signed in to the company Rippling")
        s.add_argument("--name", required=True, help="exact note name")
        s.add_argument("--ext-id", default=EXT_ID)
        if name == "put":
            s.add_argument("--body-file", required=True); s.add_argument("--vault", default="", help="exact vault name to require")
        if name == "share":
            s.add_argument("--add", action="append", default=[], help="person or group as shown in the picker; repeat")
            s.add_argument("--remove", action="append", default=[], help="person or group to remove; repeat")
            s.add_argument("--set", action="append", default=[], help="existing person or group whose level changes; repeat")
            s.add_argument("--access", choices=LEVELS, help="level for --add and --set")
        if name == "remove":
            s.add_argument("--yes", action="store_true", help="required: removing a shared note removes it for everyone")
    a = ap.parse_args()
    if a.cmd == "envblocks":
        return envblocks(a)
    base = {"ext": json.dumps(a.ext_id), "name": json.dumps(a.name)}
    if a.cmd == "put":
        body = open(a.body_file).read()
        if not body.strip():
            sys.exit("empty body")
        run(a.account, JS_PUT % {**base, "body": json.dumps(body), "vault": json.dumps(a.vault)})
    elif a.cmd == "share":
        if (a.add or a.set) and not a.access:
            sys.exit("--access is required with --add or --set")
        run(a.account, JS_SHARE % {**base, "add": json.dumps(a.add), "remove": json.dumps(a.remove),
                                   "change": json.dumps(a.set), "level": json.dumps(LEVELS.get(a.access, ""))})
    elif a.cmd == "remove":
        if not a.yes:
            sys.exit("remove needs --yes")
        run(a.account, JS_REMOVE % base)
    else:
        run(a.account, JS_ACCESS % base)


if __name__ == "__main__":
    main()
