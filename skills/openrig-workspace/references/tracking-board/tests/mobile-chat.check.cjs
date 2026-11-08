#!/usr/bin/env node
// Board chat check in headless Chrome against a real server.cjs on a scratch root (synthetic board, seeded thread).
//
//   node tests/mobile-chat.check.cjs [--out <dir>] [--shots]
//
// Phones (390x844, 375x667), with the iOS keyboard simulated by a mocked visualViewport:
//   the chat opens from the bar, fills the visual viewport, and renders the seat's markdown reply (no raw HTML);
//   with the keyboard open, typing three lines holds on every frame: the chat is the visual viewport, its header and
//   the composer stay put, the textarea is focused and fully visible, it only grows (at most 6 lines), and the newest
//   message stays in view; Send queues the message and keeps the textarea focused.
// From a row (390x844): the note box's Chat kind moves the text into the chat with the row attached; Send keeps it.
// Desktop (1440x900): the sidebar is 400px, Expand widens it to half and then full width, and Collapse brings it back;
// Cmd/Ctrl+Enter sends, and a reply that arrives while the chat is closed shows as unread on the bar until it is opened.
// Exit 0 when everything holds, 1 with the failures. --shots writes PNGs to --out.
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
const PHONES = [
  { name: "390x844", w: 390, h: 844, kb: 336, scroll: 120 },
  { name: "375x667", w: 375, h: 667, kb: 301, scroll: 90 },
];
const REPLY = [
  "**Short answer:** M2.3 waits on the sandbox keys.", "",
  "What I checked:", "- the retry budget is *three* attempts, with a `30 s` backoff", "- the provider sandbox has been down since 09:10",
  "- [the run log](https://example.com/runs/42) shows two `429` responses", "",
  "Next steps:", "1. ask the provider for new sandbox keys", "2. re-run `board.cjs check` after the keys land", "3. move M2.3 to review", "",
  "```", "retry: 3", "backoff: 30s", "```", "", "Raw HTML stays text: <script>window.__pwned = 1</script> <img src=x onerror=\"window.__pwned = 1\">",
].join("\n");

// Installed before the page script: a visualViewport the check moves by hand, and a per-frame sample of the chat.
const MOCK = `(() => {
  window.__errs = []; addEventListener("error", e => window.__errs.push(e.message));
  const vv = new EventTarget(); let h = innerHeight, top = 0;
  for (const [k, get] of Object.entries({ height: () => h, offsetTop: () => top, width: () => innerWidth, offsetLeft: () => 0, scale: () => 1, pageTop: () => scrollY + top, pageLeft: () => 0 }))
    Object.defineProperty(vv, k, { get });
  Object.defineProperty(window, "visualViewport", { get: () => vv, configurable: true });
  window.__vv = (nh, nt) => { const r = nh !== h; h = nh; top = nt; if (r) vv.dispatchEvent(new Event("resize")); vv.dispatchEvent(new Event("scroll")); };
  window.__frames = []; window.__rec = false;
  const q = s => document.querySelector(s);
  const sample = () => {
    if (!window.__rec || !q("#chat")) return;
    const c = q("#chat").getBoundingClientRect(), hd = q("#chat header").getBoundingClientRect(), f = q("#chatform").getBoundingClientRect(), t = q("#chat-text").getBoundingClientRect(), th = q("#thread");
    window.__frames.push({ vt: top, vb: top + h, ct: c.top, cb: c.bottom, ht: hd.top, fb: f.bottom, tt: t.top, tb: t.bottom, th: t.height,
      focused: document.activeElement === q("#chat-text"), pinned: th.scrollHeight - th.scrollTop - th.clientHeight < 2 });
  };
  (function tick() { setTimeout(sample, 0); requestAnimationFrame(tick); })();
})();`;

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function cdp(port) {
  let ws;
  for (let i = 0; i < 50 && !ws; i++) {
    try { const t = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" })).json(); ws = t.webSocketDebuggerUrl; } catch { await sleep(100); }
  }
  if (!ws) throw new Error("Chrome did not open its debugging port");
  const sock = new WebSocket(ws); await new Promise((ok, no) => { sock.onopen = ok; sock.onerror = no; });
  let id = 0; const wait = new Map();
  sock.onmessage = m => { const d = JSON.parse(m.data); if (d.id && wait.has(d.id)) { const [ok, no] = wait.get(d.id); wait.delete(d.id); d.error ? no(new Error(d.error.message)) : ok(d.result); } };
  const send = (method, params = {}) => new Promise((ok, no) => { wait.set(++id, [ok, no]); sock.send(JSON.stringify({ id, method, params })); });
  const ev = async expr => {
    const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error(`page: ${(r.exceptionDetails.exception && r.exceptionDetails.exception.description) || r.exceptionDetails.text} in ${expr.slice(0, 80)}`);
    return r.result.value;
  };
  return { send, ev, close: () => sock.close() };
}

// A scratch boards root with the fixture board, one sent notes batch and one chat message, both answered.
function seed() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "tb-chat-"));
  const board = path.join(root, "demo", "audit", "sample");
  fs.mkdirSync(board, { recursive: true });
  fs.copyFileSync(path.join(dir, "fixtures", "board.json"), path.join(board, "board.json"));
  execFileSync(process.execPath, [path.join(dir, "board.cjs"), "render", "demo/audit/sample"], { env: { ...process.env, OPENRIG_BOARDS_ROOT: root }, stdio: "ignore" });
  const fb = path.join(board, "feedback");
  for (const sub of ["inbox", "processing", "status", "done"]) fs.mkdirSync(path.join(fb, sub), { recursive: true });
  const at = (m) => new Date(Date.now() - m * 60000).toISOString();
  const put = (sub, id, data) => fs.writeFileSync(path.join(fb, sub, `${id}.json`), JSON.stringify({ id, ...data }));
  const a = "2026-01-01T00-00-00-000Z-aaaaaa", b = "2026-01-01T00-00-01-000Z-bbbbbb";
  put("processing", a, { board: "demo/audit/sample", received_at: at(30), notes: [{ id: "n1", kind: "change", anchor: "M1 › M1.2 Ledger import", quote: "", text: "Split the import into two runs." }] });
  put("status", a, { state: "done", at: at(28) }); put("done", a, { reply: "n1: applied", at: at(28) });
  put("processing", b, { board: "demo/audit/sample", received_at: at(12), kind: "chat", text: "What is blocking **M2.3**?", anchor: "M2 › M2.3 Retry and backoff" });
  put("status", b, { state: "done", at: at(10) }); put("done", b, { reply: REPLY, at: at(10) });
  return root;
}

async function phone(c, base, p) {
  const { send, ev } = c, bad = [];
  await send("Emulation.setDeviceMetricsOverride", { width: p.w, height: p.h, deviceScaleFactor: 2, mobile: true });
  await send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
  await send("Page.navigate", { url: `${base}/` }); await sleep(600);
  await ev("localStorage.clear(); sessionStorage.clear(); true"); await send("Page.reload"); await sleep(1200);
  await ev(`__vv(${p.h}, 0); true`); await sleep(100); // the mock read innerHeight before the phone viewport applied
  const shown = await ev(`!document.getElementById("chatbtn").hidden`);
  if (!shown) return [`${p.name}: the chat button is hidden for a signed-in browser (${await ev(`fetch("thread").then(r => r.status + " " + window.__errs.join(" | "))`)})`];
  const tap = async sel => {
    const r = await ev(`(() => { const r = document.querySelector(${JSON.stringify(sel)}).getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
    await send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [r] }); await sleep(40);
    await send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] }); await sleep(250);
  };
  await tap("#chatbtn"); await sleep(400);
  const st = await ev(`(() => { const c = document.getElementById("chat").getBoundingClientRect(), th = document.getElementById("thread");
    return { on: document.getElementById("chat").classList.contains("on"), top: c.top, bottom: c.bottom, w: c.width,
      strong: th.querySelectorAll(".seat strong").length, li: th.querySelectorAll(".seat li").length, pre: th.querySelectorAll(".seat pre").length,
      links: [...th.querySelectorAll("a")].map(a => a.getAttribute("href")), raw: th.querySelectorAll("script, img, iframe").length, pwned: !!window.__pwned,
      pinned: th.scrollHeight - th.scrollTop - th.clientHeight < 2, msgs: th.querySelectorAll(".msg").length }; })()`);
  if (!st.on) return [`${p.name}: the chat did not open from the bar`];
  if (Math.abs(st.top) > 1 || Math.abs(st.bottom - p.h) > 1 || Math.abs(st.w - p.w) > 1) bad.push(`${p.name}: chat ${st.top}..${st.bottom} x ${st.w} is not the full screen`);
  if (st.strong < 1 || st.li < 6 || st.pre !== 1) bad.push(`${p.name}: markdown not rendered (strong ${st.strong}, li ${st.li}, pre ${st.pre})`);
  if (st.raw || st.pwned || st.links.some(h => !/^https:\/\//.test(h))) bad.push(`${p.name}: raw HTML or a non-https link reached the thread`);
  if (!st.pinned) bad.push(`${p.name}: the newest message is not in view on open`);
  if (st.msgs < 4 || st.msgs % 2) bad.push(`${p.name}: expected the 2 seeded exchanges (4 messages) or more, got ${st.msgs}`);
  if (shots) await shot(c, p, path.join(out, `chat-${p.name}-reply.png`), false);
  // Keyboard: focus the textarea, the visual viewport shrinks, then iOS scrolls it.
  await tap("#chat-text");
  await ev(`window.__frames = []; window.__rec = true; true`);
  await ev(`__vv(${p.h - p.kb}, 0); true`); await sleep(120);
  await ev(`__vv(${p.h - p.kb}, ${p.scroll}); true`); await sleep(300);
  for (const line of ["Can you check the sandbox keys", "and tell me when M2.3 can move", "to review?"]) {
    for (const ch of line) { await send("Input.insertText", { text: ch }); await ev(`__vv(${p.h - p.kb}, ${p.scroll}); true`); await sleep(6); }
    if (line !== "to review?") {
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13, text: "\r" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13 });
    }
    await ev(`__vv(${p.h - p.kb}, ${p.scroll}); true`); await sleep(40);
  }
  await sleep(200);
  if (shots) await shot(c, p, path.join(out, `chat-${p.name}-typing.png`), true);
  const frames = (await ev(`window.__rec = false; window.__frames`)).filter(f => f.vt === p.scroll);
  const text = await ev(`document.getElementById("chat-text").value`);
  if (text.split("\n").length !== 3) bad.push(`${p.name}: typed text did not reach the textarea (${JSON.stringify(text)})`);
  if (!frames.length) bad.push(`${p.name}: no frames recorded with the keyboard open`);
  const heights = new Set(), line = 1.4 * 16, maxH = 6 * line + 16 + 2;
  let prev = 0;
  for (const [i, f] of frames.entries()) {
    const why = [];
    if (Math.abs(f.ct - f.vt) > 1 || Math.abs(f.cb - f.vb) > 1) why.push(`chat ${f.ct.toFixed(0)}..${f.cb.toFixed(0)} is not the visual viewport ${f.vt}..${f.vb}`);
    if (Math.abs(f.ht - f.vt) > 1) why.push(`header moved to ${f.ht.toFixed(0)}`);
    if (Math.abs(f.fb - f.vb) > 1) why.push(`composer bottom ${f.fb.toFixed(0)} is off the keyboard ${f.vb}`);
    if (!f.focused) why.push("textarea not focused");
    if (f.tt < f.vt - 1 || f.tb > f.vb + 1) why.push(`textarea ${f.tt.toFixed(0)}..${f.tb.toFixed(0)} not fully visible`);
    if (f.th < prev - 1) why.push(`textarea shrank from ${prev.toFixed(0)} to ${f.th.toFixed(0)}`);
    if (f.th > maxH + 1) why.push(`textarea ${f.th.toFixed(0)}px is over 6 lines`);
    if (!f.pinned) why.push("newest message scrolled out of view");
    heights.add(Math.round(f.th)); prev = f.th;
    if (why.length) bad.push(`${p.name} frame ${i}/${frames.length}: ${why.join("; ")}`);
  }
  if (heights.size > 3) bad.push(`${p.name}: textarea took ${heights.size} heights for 3 lines (${[...heights].join(", ")})`);
  // Send: the message joins the thread, the textarea empties and keeps the focus.
  await tap("#chatsend"); await sleep(600);
  const sent = await ev(`({ msgs: document.querySelectorAll("#thread .msg").length, value: document.getElementById("chat-text").value, focused: document.activeElement === document.getElementById("chat-text") })`);
  if (sent.msgs !== st.msgs + 2 || sent.value || !sent.focused) bad.push(`${p.name}: after Send ${JSON.stringify(sent)}`);
  console.log(`${p.name}: ${frames.length} frames, textarea heights ${[...heights].join("/")}px; ${bad.length ? `${bad.length} failing` : "all hold"}`);
  return bad;
}

// From a row: long-press a slice row, pick the Chat kind, and the text moves to the chat with the row as context.
async function fromRow(c, base, p) {
  const { send, ev } = c, bad = [];
  await send("Emulation.setDeviceMetricsOverride", { width: p.w, height: p.h, deviceScaleFactor: 2, mobile: true });
  await send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
  await send("Page.navigate", { url: `${base}/` }); await sleep(600);
  await ev("localStorage.clear(); sessionStorage.clear(); true"); await send("Page.reload"); await sleep(1200);
  await ev(`__vv(${p.h}, 0); true`);
  const at = await ev(`(() => { const row = [...document.querySelectorAll(".srow")].find(r => r.getBoundingClientRect().height > 0);
    row.scrollIntoView({ block: "center", behavior: "instant" }); const r = row.getBoundingClientRect(); return { x: r.left + Math.min(r.width / 2, 120), y: r.top + Math.min(r.height / 2, 18), label: row.dataset.label }; })()`);
  await sleep(150);
  await send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: at.x, y: at.y }] }); await sleep(700);
  await send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] }); await sleep(300);
  await ev(`document.querySelector('#cmp-kind [data-k="chat"]').click(); true`);
  await send("Input.insertText", { text: "Why is this one late?" }); await sleep(100);
  const label = await ev(`document.getElementById("cmpsave").textContent`);
  await ev(`document.getElementById("cmpsave").click(); true`); await sleep(400);
  const st = await ev(`({ chat: document.getElementById("chat").classList.contains("on"), box: document.getElementById("composer").classList.contains("on"),
    text: document.getElementById("chat-text").value, ctx: document.getElementById("chatctx").hidden ? "" : document.getElementById("chatctx-t").textContent,
    focused: document.activeElement === document.getElementById("chat-text") })`);
  if (label !== "To chat" || !st.chat || st.box || st.text !== "Why is this one late?" || !st.ctx.includes(at.label) || !st.focused) bad.push(`from a row: ${JSON.stringify({ label, ...st })}`);
  await ev(`document.getElementById("chatform").requestSubmit(); true`); await sleep(600);
  const sent = await ev(`(() => { const m = [...document.querySelectorAll("#thread .msg.me")].pop(); return { text: m.textContent, ctx: document.getElementById("chatctx").hidden }; })()`);
  if (!sent.text.includes(`On ${at.label}`) || !sent.ctx) bad.push(`from a row, after Send: ${JSON.stringify(sent)}`);
  console.log(`${p.name} from a row: ${bad.length ? `${bad.length} failing` : "all hold"}`);
  return bad;
}

async function desktop(c, base, root) {
  const { send, ev } = c, bad = [];
  await send("Emulation.setTouchEmulationEnabled", { enabled: false });
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  await send("Page.navigate", { url: `${base}/` }); await sleep(600);
  await ev("localStorage.clear(); sessionStorage.clear(); true"); await send("Page.reload"); await sleep(1200);
  await ev(`document.getElementById("chatbtn").click(); true`); await sleep(400);
  const widths = [];
  for (const name of ["sidebar", "half", "full", "collapsed"]) {
    widths.push(await ev(`Math.round(document.getElementById("chat").getBoundingClientRect().width)`));
    if (shots && name !== "collapsed") { const { data } = await send("Page.captureScreenshot", { format: "png" }); fs.writeFileSync(path.join(out, `chat-1440-${name}.png`), Buffer.from(data, "base64")); }
    await ev(`document.getElementById("chatsize").click(); true`); await sleep(300);
  }
  const want = [400, 720, 1440, 400];
  if (widths.some((w, i) => Math.abs(w - want[i]) > 2)) bad.push(`desktop: chat widths ${widths.join(", ")}, want ${want.join(", ")}`);
  // Cmd/Ctrl+Enter sends.
  await ev(`document.getElementById("chat-text").focus(); true`);
  await send("Input.insertText", { text: "Sent with the keyboard" });
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13, modifiers: 2 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13, modifiers: 2 }); await sleep(600);
  const last = await ev(`[...document.querySelectorAll("#thread .msg.me")].pop().textContent`);
  if (!/Sent with the keyboard/.test(last)) bad.push(`desktop: Ctrl+Enter did not send (last message ${JSON.stringify(last.slice(0, 60))})`);
  // A reply that arrives while the chat is closed shows as unread on the bar, live; opening the chat reads it.
  await ev(`document.getElementById("chatclose").click(); true`); await sleep(200);
  const fb = path.join(root, "demo", "audit", "sample", "feedback"), id = fs.readdirSync(path.join(fb, "inbox")).sort().pop().replace(/\.json$/, "");
  fs.writeFileSync(path.join(fb, "done", `${id}.json`), JSON.stringify({ id, reply: "On it: **keys** requested.", at: new Date().toISOString() }));
  fs.writeFileSync(path.join(fb, "status", `${id}.json`), JSON.stringify({ id, state: "done", at: new Date().toISOString() })); await sleep(900);
  const badge = await ev(`(() => { const b = document.getElementById("chatbadge"); return b.classList.contains("on") ? b.textContent : ""; })()`);
  await ev(`document.getElementById("chatbtn").click(); true`); await sleep(300);
  const after = await ev(`({ badge: document.getElementById("chatbadge").classList.contains("on"), reply: [...document.querySelectorAll("#thread .msg.seat")].pop().textContent })`);
  if (badge !== "1" || after.badge || !/On it: keys requested/.test(after.reply)) bad.push(`desktop: unread ${JSON.stringify(badge)} then ${JSON.stringify(after)}`);
  console.log(`1440: widths ${widths.join(" → ")}; ${bad.length ? `${bad.length} failing` : "all hold"}`);
  return bad;
}

async function shot(c, p, file, keyboard) {
  if (!keyboard) { const { data } = await c.send("Page.captureScreenshot", { format: "png" }); fs.writeFileSync(file, Buffer.from(data, "base64")); return; }
  // What the phone shows: the visual viewport, then the keyboard under it.
  const vh = p.h - p.kb, y = (await c.ev("scrollY")) + p.scroll;
  const top = (await c.send("Page.captureScreenshot", { format: "png", clip: { x: 0, y, width: p.w, height: vh, scale: 1 } })).data;
  await c.ev(`(() => { const o = document.createElement("div"); o.id = "__shot";
    o.style.cssText = "position:fixed;inset:0;z-index:2147483647;background:#cfd3d9;display:flex;flex-direction:column";
    o.innerHTML = '<img style="width:${p.w}px;height:${vh}px;display:block" src="data:image/png;base64,${top}"><div style="flex:1;display:flex;align-items:center;justify-content:center;font:600 14px system-ui;color:#555">keyboard (simulated)</div>';
    document.body.append(o); return o.querySelector("img").decode(); })()`);
  const { data } = await c.send("Page.captureScreenshot", { format: "png" });
  await c.ev(`document.getElementById("__shot").remove()`);
  fs.writeFileSync(file, Buffer.from(data, "base64"));
}

(async () => {
  const root = seed(), port = 47400 + Math.floor(Math.random() * 400), cport = 9300 + Math.floor(Math.random() * 500);
  const server = spawn(process.execPath, [path.join(dir, "server.cjs")], { env: { PATH: process.env.PATH, OPENRIG_BOARDS_ROOT: root, OPENRIG_BOARDS_PORT: String(port) }, stdio: ["ignore", "pipe", "inherit"] });
  await new Promise(ok => server.stdout.once("data", ok));
  const token = fs.readFileSync(path.join(root, ".board-token"), "utf8").trim(), base = `http://127.0.0.1:${port}/demo/audit/sample`;
  const udir = fs.mkdtempSync(path.join(os.tmpdir(), "tb-chrome-"));
  const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars", `--user-data-dir=${udir}`, `--remote-debugging-port=${cport}`, "about:blank"], { stdio: "ignore" });
  let bad = [];
  try {
    const c = await cdp(cport);
    await c.send("Page.enable");
    await c.send("Page.addScriptToEvaluateOnNewDocument", { source: MOCK });
    await c.send("Page.navigate", { url: `${base}/?k=${token}` }); await sleep(800); // sets the sign-in cookie
    if (shots) fs.mkdirSync(out, { recursive: true });
    bad = bad.concat(await desktop(c, base, root));
    for (const p of PHONES) bad = bad.concat(await phone(c, base, p));
    bad = bad.concat(await fromRow(c, base, PHONES[0]));
    c.close();
  } finally {
    chrome.kill(); server.kill();
    setTimeout(() => { fs.rmSync(udir, { recursive: true, force: true }); fs.rmSync(root, { recursive: true, force: true }); }, 300);
  }
  if (bad.length) { console.log(bad.slice(0, 12).join("\n")); if (bad.length > 12) console.log(`... ${bad.length - 12} more`); process.exit(1); }
  console.log("board chat: everything holds");
})().catch(e => { console.error(e.message); process.exit(2); });
