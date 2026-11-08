#!/usr/bin/env node
// Phone note-box check in headless Chrome, with the iOS keyboard simulated by a mocked visualViewport.
//
//   node tests/mobile-composer.check.cjs <rendered index.html> [--out <dir>] [--shots]
//
// For 390x844 and 375x667 it long-presses a slice row, opens the keyboard (visualViewport shrinks and, as on iOS,
// scrolls down inside the layout viewport), then types three lines while iOS-style visualViewport scroll events
// fire on every key. Each animation frame asserts:
//   the note box sits exactly on the visual viewport above the keyboard (top = offsetTop, height = height);
//   the textarea is focused, fully inside the box and the visual viewport, and its height never changes.
// Exit 0 when every frame holds, 1 with the first failures. --shots writes keyboard-open PNGs to --out.
// Chrome: $CHROME, else the macOS app path, else `google-chrome` on PATH. Needs Node 22 (global WebSocket).
"use strict";
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");

const args = process.argv.slice(2);
const html = args.find(a => !a.startsWith("--"));
const out = args.includes("--out") ? args[args.indexOf("--out") + 1] : os.tmpdir();
const shots = args.includes("--shots");
if (!html) { console.error("usage: mobile-composer.check.cjs <index.html> [--out <dir>] [--shots]"); process.exit(2); }
const CHROME = process.env.CHROME || ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"].find(p => fs.existsSync(p)) || "google-chrome";

// Phones: layout viewport, keyboard height (with the accessory bar), and how far iOS scrolls the visual viewport.
const PHONES = [
  { name: "390x844", w: 390, h: 844, kb: 336, scroll: 120 },
  { name: "375x667", w: 375, h: 667, kb: 301, scroll: 90 },
];

// Installed before the page script: a visualViewport the check moves by hand.
const MOCK = `(() => {
  const vv = new EventTarget(); let h = innerHeight, top = 0;
  for (const [k, get] of Object.entries({ height: () => h, offsetTop: () => top, width: () => innerWidth, offsetLeft: () => 0, scale: () => 1, pageTop: () => scrollY + top, pageLeft: () => 0 }))
    Object.defineProperty(vv, k, { get });
  Object.defineProperty(window, "visualViewport", { get: () => vv, configurable: true });
  window.__vv = (nh, nt) => { const r = nh !== h; h = nh; top = nt; if (window.__rec) window.__n.vv += r ? 2 : 1; if (r) vv.dispatchEvent(new Event("resize")); vv.dispatchEvent(new Event("scroll")); };
  window.__frames = []; window.__rec = false; window.__n = { vv: 0, writes: 0, scrolls: 0 };
  const sp = CSSStyleDeclaration.prototype.setProperty;
  CSSStyleDeclaration.prototype.setProperty = function (k, ...r) { if (window.__rec && /^--tb-(kb|vv-)/.test(k)) window.__n.writes++; return sp.call(this, k, ...r); };
  const sb = window.scrollBy; window.scrollBy = function (...a) { if (window.__rec) window.__n.scrolls++; return sb.apply(this, a); };
  const box = () => document.getElementById("composer"), ta = () => document.getElementById("cmp-text");
  // Sampled once per frame, after that frame's animation callbacks ran: the state that frame painted.
  const sample = () => {
    if (!window.__rec || !box()) return;
    const b = box().getBoundingClientRect(), t = ta().getBoundingClientRect();
    window.__frames.push({ vt: top, vb: top + h, bt: b.top, bb: b.bottom, tt: t.top, tb: t.bottom, th: t.height, focused: document.activeElement === ta() });
  };
  (function tick() { setTimeout(sample, 0); requestAnimationFrame(tick); })();
})();`;

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

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
  return { send, close: () => sock.close() };
}

async function run(c, phone, quoted) {
  const { send } = c;
  await send("Emulation.setDeviceMetricsOverride", { width: phone.w, height: phone.h, deviceScaleFactor: 2, mobile: true });
  await send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
  await send("Page.navigate", { url: `file://${path.resolve(html)}?now=2026-11-08T12:00:00Z` }); await sleep(900);
  const ev = async expr => (await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true })).result.value;
  await ev("localStorage.clear(); sessionStorage.clear(); true");
  await send("Page.reload"); await sleep(900);
  // Long-press the first slice row.
  const at = await ev(`(() => {
    const row = [...document.querySelectorAll(".srow")].find(r => r.getBoundingClientRect().height > 0);
    row.scrollIntoView({ block: "center", behavior: "instant" }); const r = row.getBoundingClientRect();
    return { x: r.left + Math.min(r.width / 2, 120), y: r.top + Math.min(r.height / 2, 18) };
  })()`);
  await sleep(150);
  const pt = [{ x: at.x, y: at.y }];
  if (quoted) {
    // A note with a quote, opened from a gesture like a tap with Annotate on: the tallest box a phone gets.
    // Annotate on, then select a slice row's text on a touch screen: the page quotes it after the selection settles.
    await ev(`document.getElementById("annot").click(); document.querySelector('#seg button[data-v="on"]').click(); document.getElementById("sheetclose").click(); true`);
    await sleep(200);
    await send("Runtime.evaluate", { userGesture: true, expression: `(() => { const row = [...document.querySelectorAll(".srow")].find(r => r.getBoundingClientRect().height > 0);
      const r = document.createRange(); r.selectNodeContents(row); getSelection().removeAllRanges(); getSelection().addRange(r); })()` });
    await sleep(1100);
  } else {
    await send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: pt }); await sleep(700);
    await send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] }); await sleep(300);
  }
  const name = `${phone.name}${quoted ? " quoted" : ""}`;
  const opened = await ev(`document.getElementById("composer").classList.contains("on")`);
  if (!opened) return [`${name}: the note box did not open`];
  // The keyboard opens: the visual viewport shrinks, then iOS scrolls it down to show the focused field.
  await ev(`window.__frames = []; window.__n = { vv: 0, writes: 0, scrolls: 0 }; window.__rec = true; true`);
  await ev(`__vv(${phone.h - phone.kb}, 0); true`); await sleep(120);
  await ev(`__vv(${phone.h - phone.kb}, ${phone.scroll}); true`); await sleep(300);
  if (shots) await shot(c, phone, path.join(out, `composer-${phone.name}${quoted ? "-quoted" : ""}.png`));
  // Type three lines; every key is followed by the caret-move scroll events iOS sends.
  for (const line of ["Move the retry budget to three", "and add the 30 s backoff note", "before the next review"]) {
    for (const ch of line) { await send("Input.insertText", { text: ch }); await ev(`__vv(${phone.h - phone.kb}, ${phone.scroll}); true`); await sleep(8); }
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13, text: "\r" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13 });
    await ev(`__vv(${phone.h - phone.kb}, ${phone.scroll + 4}); true`); await sleep(40);
    await ev(`__vv(${phone.h - phone.kb}, ${phone.scroll}); true`); await sleep(40);
  }
  await sleep(200);
  const frames = (await ev(`window.__rec = false; window.__frames`)).filter(f => f.vt === phone.scroll);
  const n = await ev(`window.__n`);
  const text = await ev(`document.getElementById("cmp-text").value`);
  const bad = [];
  if (text.split("\n").length < 3) bad.push(`${name}: typed text did not reach the textarea (${JSON.stringify(text)})`);
  if (!frames.length) bad.push(`${name}: no frames recorded with the keyboard open`);
  const th0 = frames.length ? frames[0].th : 0;
  for (const [i, f] of frames.entries()) {
    const why = [];
    if (Math.abs(f.bt - f.vt) > 1 || Math.abs(f.bb - f.vb) > 1) why.push(`box ${f.bt.toFixed(0)}..${f.bb.toFixed(0)} is not the visual viewport ${f.vt}..${f.vb}`);
    if (!f.focused) why.push("textarea not focused");
    if (f.tt < Math.max(f.bt, f.vt) - 1 || f.tb > Math.min(f.bb, f.vb) + 1) why.push(`textarea ${f.tt.toFixed(0)}..${f.tb.toFixed(0)} not fully visible`);
    if (Math.abs(f.th - th0) > 1) why.push(`textarea height ${f.th.toFixed(0)} changed from ${th0.toFixed(0)}`);
    if (f.th < 4 * 22) why.push(`textarea ${f.th.toFixed(0)}px is under 4 lines`);
    if (why.length) bad.push(`${name} frame ${i}/${frames.length}: ${why.join("; ")}`);
  }
  console.log(`${name}: ${frames.length} frames, textarea ${th0.toFixed(0)}px; while open ${n.vv} visualViewport events, ${n.writes} box position writes, ${n.scrolls} page scrolls; ${bad.length ? `${bad.length} failing` : "all hold"}`);
  return bad;
}

async function shot(c, phone, file) {
  // What the phone shows: the visual viewport, then the keyboard under it. The visible part is captured, then drawn
  // over a full-screen overlay above a grey keyboard block, and that overlay is captured.
  const vh = phone.h - phone.kb, ev = expr => c.send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
  const y = (await ev("scrollY")).result.value + phone.scroll;
  const top = (await c.send("Page.captureScreenshot", { format: "png", clip: { x: 0, y, width: phone.w, height: vh, scale: 1 } })).data;
  await ev(`(() => { const o = document.createElement("div"); o.id = "__shot";
    o.style.cssText = "position:fixed;inset:0;z-index:2147483647;background:#cfd3d9;display:flex;flex-direction:column";
    o.innerHTML = '<img style="width:${phone.w}px;height:${vh}px;display:block" src="data:image/png;base64,${top}"><div style="flex:1;display:flex;align-items:center;justify-content:center;font:600 14px system-ui;color:#555">keyboard (simulated)</div>';
    document.body.append(o); return o.querySelector("img").decode(); })()`);
  const { data } = await c.send("Page.captureScreenshot", { format: "png" });
  await ev(`document.getElementById("__shot").remove()`);
  fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, Buffer.from(data, "base64"));
}

(async () => {
  const port = 9300 + Math.floor(Math.random() * 500);
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "tb-chrome-"));
  const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars", `--user-data-dir=${dir}`, `--remote-debugging-port=${port}`, "--allow-file-access-from-files", "about:blank"], { stdio: "ignore" });
  let bad = [];
  try {
    const c = await cdp(port);
    await c.send("Page.enable");
    await c.send("Page.addScriptToEvaluateOnNewDocument", { source: MOCK });
    for (const phone of PHONES) for (const quoted of [false, true]) bad = bad.concat(await run(c, phone, quoted));
    c.close();
  } finally { chrome.kill(); setTimeout(() => fs.rmSync(dir, { recursive: true, force: true }), 300); }
  if (bad.length) { console.log(bad.slice(0, Number(process.env.SHOW || 12)).join("\n")); if (bad.length > 12) console.log(`... ${bad.length - 12} more`); process.exit(1); }
  console.log("mobile composer: every frame holds");
})().catch(e => { console.error(e.message); process.exit(2); });
