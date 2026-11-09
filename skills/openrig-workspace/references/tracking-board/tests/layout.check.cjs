#!/usr/bin/env node
// Board layout check in headless Chrome: renders the fixtures and asserts the layout at 390, 768, 1024 and 1440.
//
//   node tests/layout.check.cjs [--out <dir>] [--shots]
//
// For fixtures/board.json and fixtures/long.json (9 open decisions, 8 dated updates, long section titles):
//   lead      no card in .lead sits more than 24px below the card above it (nothing floats in a stretched row);
//   waiting   one "Waiting on you" card holds the asks, then the open decisions, with one count; the Open decisions
//             stat links to that card's decision list;
//   decisions every decision starts collapsed with its recommendation on one line; one opened stays open on reload;
//   measure   inside a section, paragraphs, tables, code and lists share one width;
//   history   a section with dated "Status / Update / Correction (...)" paragraphs shows the newest one and keeps the
//             rest in a closed "Earlier updates (n)"; no section is taller than about two screens until "Show all";
//   rail      each rail label is one line, with the full title as its tooltip (>= 1024);
//   headline  the headline is at most two lines at 1440, and one line when one line fits the hero.
// Exit 0 when everything holds, 1 with the failures. --shots writes the first screen of each width to --out.
// Chrome: $CHROME, else the macOS app path, else `google-chrome` on PATH. Needs Node 22 (global WebSocket).
"use strict";
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const args = process.argv.slice(2);
const out = args.includes("--out") ? args[args.indexOf("--out") + 1] : os.tmpdir();
const shots = args.includes("--shots");
const dir = path.join(__dirname, "..");
const CHROME = process.env.CHROME || ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"].find(p => fs.existsSync(p)) || "google-chrome";
const WIDTHS = [[390, 844], [768, 1024], [1024, 768], [1440, 900]];
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function cdp(port) {
  let ws;
  for (let i = 0; i < 50 && !ws; i++) {
    try { ws = (await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" })).json()).webSocketDebuggerUrl; } catch { await sleep(100); }
  }
  if (!ws) throw new Error("Chrome did not open its debugging port");
  const sock = new WebSocket(ws); await new Promise((ok, no) => { sock.onopen = ok; sock.onerror = no; });
  let id = 0; const wait = new Map();
  sock.onmessage = m => { const d = JSON.parse(m.data); if (d.id && wait.has(d.id)) { const [ok, no] = wait.get(d.id); wait.delete(d.id); d.error ? no(new Error(d.error.message)) : ok(d.result); } };
  const send = (method, params = {}) => new Promise((ok, no) => { wait.set(++id, [ok, no]); sock.send(JSON.stringify({ id, method, params })); });
  const ev = async expr => {
    const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error(`page: ${(r.exceptionDetails.exception && r.exceptionDetails.exception.description) || r.exceptionDetails.text}`);
    return r.result.value;
  };
  return { send, ev, close: () => sock.close() };
}

// Runs in the page; returns a list of failures for this width.
const PROBE = `(() => {
  const bad = [], $$ = (s, r = document) => [...r.querySelectorAll(s)], vis = el => el.getClientRects().length > 0;
  const b = JSON.parse(document.getElementById("board").textContent), W = innerWidth;
  const openDec = (b.decisions || []).filter(d => d.status !== "accepted"), needs = b.needs || [];
  // lead: each visible card's top against the lowest bottom of the cards above it that share its columns.
  const cards = $$(".lead > *").flatMap(el => getComputedStyle(el).display === "contents" ? [...el.children] : [el]).filter(vis).map(el => [el, el.getBoundingClientRect()]);
  for (const [el, r] of cards) {
    const above = cards.filter(([o, q]) => o !== el && q.bottom <= r.top + 1 && q.left < r.right - 1 && q.right > r.left + 1);
    if (!above.length) continue;
    const gap = r.top - Math.max(...above.map(([, q]) => q.bottom));
    if (gap > 24) bad.push(\`lead: \${el.id || el.className} sits \${Math.round(gap)}px below the card above it\`);
  }
  // waiting: one card, asks then decisions, one count.
  const wait = document.getElementById("needs"), list = document.getElementById("decisions");
  if (!wait || !/Waiting on you/.test(wait.querySelector("h2")?.textContent || "")) bad.push("waiting: no card titled Waiting on you");
  else {
    if (openDec.length && !(list && wait.contains(list))) bad.push("waiting: the open decisions are not inside the Waiting on you card");
    const cnt = wait.querySelector(".cnt")?.textContent.trim();
    if (cnt !== String(needs.length + openDec.length)) bad.push(\`waiting: count \${cnt}, want \${needs.length + openDec.length}\`);
    const asks = wait.querySelector("ol"), first = asks && list && (asks.compareDocumentPosition(list) & Node.DOCUMENT_POSITION_FOLLOWING);
    if (needs.length && openDec.length && !first) bad.push("waiting: the asks do not come before the decisions");
    if ($$(".lead .card").filter(c => /Open decisions/.test(c.querySelector("h2")?.textContent || "") && c !== wait && !wait.contains(c)).length) bad.push("waiting: a separate Open decisions card is still shown");
    const stat = document.querySelector(".stat.decide");
    if (stat && stat.getAttribute("href") !== "#decisions") bad.push("waiting: the Open decisions stat does not link to the decision list");
  }
  // decisions: collapsed, recommendation on one line.
  for (const d of $$(".drow details")) {
    if (d.open) { bad.push(\`decisions: \${d.closest(".drow").id} starts open\`); continue; }
    const rec = d.querySelector(".drec");
    if (!rec) { bad.push(\`decisions: \${d.closest(".drow").id} shows no recommendation line\`); continue; }
    if (vis(rec) && rec.getBoundingClientRect().height > parseFloat(getComputedStyle(rec).lineHeight) * 1.5) bad.push(\`decisions: \${d.closest(".drow").id} recommendation wraps\`);
  }
  // measure: one width per section for its prose, tables, code and lists.
  for (const s of $$(".sect")) {
    const ws = $$(":scope > p, :scope > .tblwrap, :scope > pre, :scope > ul, :scope > ol, :scope > h3, :scope > div:not([class])", s).filter(vis).map(e => Math.round(e.getBoundingClientRect().width));
    if (ws.length && Math.max(...ws) - Math.min(...ws) > 1) bad.push(\`measure: \${s.id} has widths \${[...new Set(ws)].join("/")}\`);
  }
  // history: dated updates fold; tall sections fold after a preview.
  const dated = /^(status|update|correction|status update)\\b[^:]*\\(/i;
  for (const s of $$(".sect")) {
    const ps = $$("p", s).filter(p => p.firstElementChild && p.firstElementChild.tagName === "B" && dated.test(p.firstElementChild.textContent) && p.firstChild === p.firstElementChild);
    if (ps.length >= 3) {
      const shown = ps.filter(p => !p.closest("details:not([open])"));
      const er = $$("details", s).find(d => /^Earlier updates \\(\\d+\\)/.test(d.querySelector("summary")?.textContent.trim() || ""));
      const raw = ((b.sections || []).find(x => x.id === s.id) || {}).html || "";
      const newest = [...raw.matchAll(/<p><b>([^<]*)<\\/b>/g)].map(m => m[1]).filter(t => dated.test(t)).pop();
      if (shown.length !== 1 || shown[0].firstElementChild.textContent !== newest) bad.push(\`history: \${s.id} shows \${shown.length} dated updates, want only the newest (\${newest})\`);
      if (!er || er.open || !er.querySelector("summary").textContent.includes(\`(\${ps.length - 1})\`)) bad.push(\`history: \${s.id} has no closed "Earlier updates (\${ps.length - 1})"\`);
    }
    const h = s.getBoundingClientRect().height;
    if (h > innerHeight * 2 + 120) bad.push(\`history: \${s.id} is \${Math.round(h)}px tall, over two screens (\${innerHeight * 2})\`);
  }
  // rail: one line each, full title as the tooltip.
  if (W >= 1024) for (const a of $$("#rail a")) {
    const t = a.querySelector("span"), h = t.getBoundingClientRect().height, lh = parseFloat(getComputedStyle(t).lineHeight) || 18;
    if (h > lh * 1.5) bad.push(\`rail: "\${t.textContent}" wraps to \${Math.round(h / lh)} lines\`);
    if (!a.title) bad.push(\`rail: "\${t.textContent}" has no tooltip\`);
  }
  // headline: one or two lines at 1440.
  const hl = document.querySelector(".hero .headline");
  if (W >= 1440 && hl) {
    const n = Math.round(hl.getBoundingClientRect().height / parseFloat(getComputedStyle(hl).lineHeight));
    const probe = hl.cloneNode(true); probe.style.cssText = "position:absolute;visibility:hidden;white-space:nowrap;max-width:none;width:auto"; hl.parentElement.append(probe);
    const natural = probe.getBoundingClientRect().width, room = hl.parentElement.getBoundingClientRect().width; probe.remove();
    if (n > 2) bad.push(\`headline: \${n} lines at \${W}\`);
    else if (n > 1 && natural <= room) bad.push(\`headline: wraps to \${n} lines although one line (\${Math.round(natural)}px) fits the \${Math.round(room)}px hero\`);
  }
  return bad;
})()`;

(async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "tb-layout-")), files = [];
  for (const f of ["board", "long"]) {
    const d = path.join(root, "demo", "audit", f); fs.mkdirSync(d, { recursive: true });
    fs.copyFileSync(path.join(dir, "fixtures", `${f}.json`), path.join(d, "board.json"));
    execFileSync(process.execPath, [path.join(dir, "board.cjs"), "render", `demo/audit/${f}`], { env: { ...process.env, OPENRIG_BOARDS_ROOT: root }, stdio: "ignore" });
    files.push([f, path.join(d, "index.html")]);
  }
  const port = 9300 + Math.floor(Math.random() * 500), udir = fs.mkdtempSync(path.join(os.tmpdir(), "tb-chrome-"));
  const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars", `--user-data-dir=${udir}`, `--remote-debugging-port=${port}`, "--allow-file-access-from-files", "about:blank"], { stdio: "ignore" });
  let bad = [];
  try {
    const c = await cdp(port);
    await c.send("Page.enable");
    if (shots) fs.mkdirSync(out, { recursive: true });
    for (const [name, file] of files) for (const [w, h] of WIDTHS) {
      await c.send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: w < 700 ? 2 : 1, mobile: w < 700 });
      await c.send("Page.navigate", { url: `file://${file}?now=2026-11-09T05:00:00Z&theme=light` }); await sleep(500);
      await c.ev("localStorage.clear(); sessionStorage.clear(); true"); await c.send("Page.reload"); await sleep(900);
      const found = (await c.ev(PROBE)).map(x => `${name} ${w}: ${x}`);
      // decisions: an opened one stays open after a reload.
      if (w === 1440) {
        const id = await c.ev(`(() => { const d = document.querySelector(".drow details"); if (!d) return ""; d.open = true; d.dispatchEvent(new Event("toggle")); return d.closest(".drow").id; })()`);
        if (id) {
          await sleep(100); await c.send("Page.reload"); await sleep(900);
          if (!(await c.ev(`document.getElementById(${JSON.stringify(id)}).querySelector("details").open`))) found.push(`${name} ${w}: decisions: ${id} did not stay open after a reload`);
        }
      }
      if (shots) { const { data } = await c.send("Page.captureScreenshot", { format: "png" }); fs.writeFileSync(path.join(out, `${name}-${w}.png`), Buffer.from(data, "base64")); }
      console.log(`${name} ${w}: ${found.length ? `${found.length} failing` : "all hold"}`);
      bad = bad.concat(found);
    }
    c.close();
  } finally { chrome.kill(); setTimeout(() => { fs.rmSync(udir, { recursive: true, force: true }); fs.rmSync(root, { recursive: true, force: true }); }, 300); }
  if (bad.length) { console.log(bad.slice(0, Number(process.env.SHOW || 40)).join("\n")); if (bad.length > 40) console.log(`... ${bad.length - 40} more`); process.exit(1); }
  console.log("layout: everything holds");
})().catch(e => { console.error(e.message); process.exit(2); });
