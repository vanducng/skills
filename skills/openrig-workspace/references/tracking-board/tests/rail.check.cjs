#!/usr/bin/env node
// Resizable rail check in headless Chrome, on fixtures/long.json:
//
//   node tests/rail.check.cjs
//
//   handle    a vertical separator with aria-valuemin 200, aria-valuemax and aria-valuenow, 232px by default (1440);
//   drag      a pointer drag sets the width and stores it; it stops at 200 and at the widest (480 at 1440);
//   widest    at the widest, rail labels wrap rather than cut off, and keep their tooltip;
//   keys      Right +16, Shift+Right +64, Left -16, Home the minimum, End the widest, Enter back to 232;
//   reload    a stored width is on the page before the board script runs, with no layout shift;
//   collapse  the rail button hides it to a slim strip, the bar's menu button opens the menu, and both stay on reload;
//   panels    from 1024 to 1279 the Changes sheet starts at the rail's edge;
//   phone     at 390 a stored width and collapsed state change nothing;
//   print     printing ignores the stored width.
// Exit 0 when everything holds, 1 with the failures. Chrome: $CHROME, else the macOS app path, else `google-chrome`.
"use strict";
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const dir = path.join(__dirname, "..");
const CHROME = process.env.CHROME || ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"].find(p => fs.existsSync(p)) || "google-chrome";
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

(async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "tb-rail-")), d = path.join(root, "demo", "audit", "long");
  fs.mkdirSync(d, { recursive: true });
  fs.copyFileSync(path.join(dir, "fixtures", "long.json"), path.join(d, "board.json"));
  execFileSync(process.execPath, [path.join(dir, "board.cjs"), "render", "demo/audit/long"], { env: { ...process.env, OPENRIG_BOARDS_ROOT: root }, stdio: "ignore" });
  const url = `file://${path.join(d, "index.html")}?now=2026-11-09T05:00:00Z&theme=light`;
  const port = 9300 + Math.floor(Math.random() * 500), udir = fs.mkdtempSync(path.join(os.tmpdir(), "tb-chrome-"));
  const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars", `--user-data-dir=${udir}`, `--remote-debugging-port=${port}`, "--allow-file-access-from-files", "about:blank"], { stdio: "ignore" });
  const bad = [], ok = (cond, msg) => { if (!cond) bad.push(msg); };
  try {
    const c = await cdp(port);
    await c.send("Page.enable");
    // Before the board script runs: the rail width the page starts with, and every layout shift after.
    await c.send("Page.addScriptToEvaluateOnNewDocument", { source: `
      new MutationObserver((_, o) => { if (document.getElementById("page")) { window.__railAtParse = getComputedStyle(document.body).getPropertyValue("--tb-rail-w").trim(); o.disconnect(); } }).observe(document, { childList: true, subtree: true });
      window.__cls = 0; new PerformanceObserver(l => { for (const e of l.getEntries()) window.__cls += e.value; }).observe({ type: "layout-shift", buffered: true });` });
    const size = (w, h) => c.send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: w < 700 });
    const load = async (fresh) => {
      await c.send("Page.navigate", { url }); await sleep(500);
      if (fresh) { await c.ev("localStorage.clear(); sessionStorage.clear(); true"); await c.send("Page.navigate", { url }); }
      await sleep(800);
    };
    const railW = () => c.ev(`Math.round(document.getElementById("rail").getBoundingClientRect().width)`);
    const grip = (k) => c.ev(`document.getElementById("railgrip")?.getAttribute(${JSON.stringify(k)}) ?? null`);
    const mouse = (type, x, y) => c.send("Input.dispatchMouseEvent", { type, x, y, button: "left", buttons: type === "mouseReleased" ? 0 : 1, clickCount: 1 });
    const drag = async to => {
      const x = await c.ev(`(() => { const r = document.getElementById("railgrip").getBoundingClientRect(); return Math.round(r.left + r.width / 2); })()`);
      await mouse("mousePressed", x, 400); await mouse("mouseMoved", (x + to) / 2, 400); await mouse("mouseMoved", to, 400); await mouse("mouseReleased", to, 400); await sleep(150);
    };
    const key = async (k, shift) => {
      const code = { ArrowLeft: 37, ArrowRight: 39, Home: 36, End: 35, Enter: 13 }[k];
      for (const type of ["rawKeyDown", "keyUp"]) await c.send("Input.dispatchKeyEvent", { type, key: k, code: k, windowsVirtualKeyCode: code, modifiers: shift ? 8 : 0 });
      await sleep(60);
    };

    // handle
    await size(1440, 900); await load(true);
    ok(await grip("role") === "separator" && await grip("aria-orientation") === "vertical", "handle: no vertical separator on the rail edge");
    ok(await grip("aria-valuemin") === "200" && await grip("aria-valuemax") === "480" && await grip("aria-valuenow") === "232", `handle: aria values ${await grip("aria-valuemin")}/${await grip("aria-valuenow")}/${await grip("aria-valuemax")}, want 200/232/480`);
    ok(await railW() === 232, `handle: default width ${await railW()}, want 232`);
    if (await grip("role") === "separator") {
      // drag
      await drag(360);
      ok(await railW() === 360, `drag: width ${await railW()} after a drag to 360`);
      ok(await c.ev(`localStorage.getItem("tb-rail-w")`) === "360", "drag: width not stored");
      await drag(1000); ok(await railW() === 480, `drag: width ${await railW()} after a drag to 1000, want the widest 480`);
      // widest
      const cut = await c.ev(`[...document.querySelectorAll("#rail a > span:first-child")].filter(s => s.scrollWidth > s.clientWidth + 1).map(s => s.textContent)`);
      ok(!cut.length, `widest: labels still cut off: ${cut.join(" | ")}`);
      ok(await c.ev(`getComputedStyle(document.querySelector("#rail a > span")).whiteSpace`) === "normal", "widest: labels do not wrap");
      ok(await c.ev(`[...document.querySelectorAll("#rail a")].every(a => a.title)`), "widest: a label lost its tooltip");
      await drag(40); ok(await railW() === 200, `drag: width ${await railW()} after a drag to 40, want the minimum 200`);
      ok(await c.ev(`getComputedStyle(document.querySelector("#rail a > span")).whiteSpace`) === "nowrap", "widest: labels still wrap below the widest");
      // keys
      await c.ev(`document.getElementById("railgrip").focus(); true`);
      const steps = [["Enter", 0, 232], ["ArrowRight", 0, 248], ["ArrowRight", 1, 312], ["ArrowLeft", 0, 296], ["Home", 0, 200], ["End", 0, 480], ["Enter", 0, 232]];
      for (const [k, sh, want] of steps) { await key(k, sh); const w = await railW(); ok(w === want, `keys: ${sh ? "Shift+" : ""}${k} gives ${w}, want ${want}`); }
      ok(await c.ev(`localStorage.getItem("tb-rail-w")`) === null, "keys: Enter did not clear the stored width");
      await c.ev(`document.getElementById("railgrip").dispatchEvent(new MouseEvent("dblclick", { bubbles: true })); true`);
      // reload
      await c.ev(`localStorage.setItem("tb-rail-w", "360"); true`); await load(false);
      ok(await railW() === 360, `reload: width ${await railW()}, want the stored 360`);
      ok(await c.ev("window.__railAtParse") === "360px", `reload: the page started at ${await c.ev("window.__railAtParse")}, not the stored 360px`);
      ok(await c.ev("window.__cls") === 0, `reload: layout shift ${await c.ev("window.__cls")}`);
      // collapse
      await c.ev(`document.querySelector(".railtog").click(); true`); await sleep(100);
      ok(await railW() <= 60, `collapse: rail is ${await railW()}px wide`);
      ok(await c.ev(`getComputedStyle(document.getElementById("menubtn")).display !== "none"`), "collapse: the menu button is hidden");
      await c.ev(`document.getElementById("menubtn").click(); true`); await sleep(100);
      ok(await c.ev(`document.getElementById("menu").classList.contains("open") && document.querySelectorAll("#menu a").length > 3`), "collapse: the menu button does not open the menu");
      await load(false);
      ok(await railW() <= 60 && await c.ev("window.__railAtParse") === "54px", "collapse: not kept on reload");
      await c.ev(`document.querySelector(".railtog").click(); true`); await sleep(100);
      ok(await railW() === 360, `collapse: reopened at ${await railW()}, want the stored 360`);
      // panels
      await size(1100, 800); await load(false);
      ok(await c.ev(`getComputedStyle(document.getElementById("sheet")).left`) === "360px", `panels: the Changes sheet starts at ${await c.ev(`getComputedStyle(document.getElementById("sheet")).left`)}, want 360px`);
      // print
      await size(1440, 900); await c.send("Emulation.setEmulatedMedia", { media: "print" });
      ok(await c.ev(`getComputedStyle(document.body).display`) === "block" && await c.ev(`getComputedStyle(document.getElementById("railgrip")).display`) === "none", "print: the stored width still lays out the page");
      await c.send("Emulation.setEmulatedMedia", { media: "" });
    }
    // phone
    await size(390, 844);
    const shape = `JSON.stringify([...document.querySelectorAll(".bar, #page, #menubtn, #rail")].map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.width), getComputedStyle(e).display]; }))`;
    await load(true); const plain = await c.ev(shape);
    await c.ev(`localStorage.setItem("tb-rail-w", "420"); localStorage.setItem("tb-rail-off", "1"); true`); await load(false);
    ok(await c.ev(shape) === plain, `phone: a stored rail changes the 390 layout: ${plain} -> ${await c.ev(shape)}`);
    c.close();
  } finally { chrome.kill(); setTimeout(() => { fs.rmSync(udir, { recursive: true, force: true }); fs.rmSync(root, { recursive: true, force: true }); }, 300); }
  if (bad.length) { console.log(bad.join("\n")); process.exit(1); }
  console.log("rail: everything holds");
})().catch(e => { console.error(e.message); process.exit(2); });
