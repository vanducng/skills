#!/usr/bin/env node
// Board server: static files for every board, plus per-board feedback and live events.
//   GET  /<org>/<project>/<slug>/            the board (index.html) and any page beside it
//   POST /<org>/<project>/<slug>/feedback    notes from the page -> feedback/inbox/<id>.json (needs a sign-in, below)
//   POST /<org>/<project>/<slug>/chat        one chat message {text, anchor?, quote?} -> the same inbox, kind "chat"
//   GET  /<org>/<project>/<slug>/thread      ?limit=50: notes batches and chat messages, oldest first, each with its
//                                            state and the seat's reply (needs a sign-in; others get 401)
//   GET  /<org>/<project>/<slug>/events      server-sent events: hello, status, reply, reload (status and reply go
//                                            to signed-in browsers only)
// Signed in (may send feedback) by either:
//   the token cookie: open any board URL with ?k=<token> once (board.cjs login prints it); the server sets an HttpOnly,
//   SameSite=Strict cookie. The token lives in <root>/.board-token (mode 600);
//   a tailnet identity: `tailscale serve` adds Tailscale-User-Login to each request (and strips one a client sent);
//   a login listed in <root>/.board-owners (one per line, mode 600) is signed in. No list, or one others can read or
//   write, means token only.
// Bind is loopback only; publish with `tailscale serve` (serve.sh), never Funnel.
"use strict";
const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const crypto = require("node:crypto");

const root = path.resolve(process.env.OPENRIG_BOARDS_ROOT || path.join(os.homedir(), ".share", "openrig", "boards"));
const port = Number(process.env.OPENRIG_BOARDS_PORT || 47320);
const tokenFile = path.join(root, ".board-token");
const ownersFile = path.join(root, ".board-owners");
fs.mkdirSync(root, { recursive: true });
if (!fs.existsSync(tokenFile)) fs.writeFileSync(tokenFile, crypto.randomBytes(24).toString("hex"), { mode: 0o600 });
const token = fs.readFileSync(tokenFile, "utf8").trim();

const types = { ".html": "text/html; charset=utf-8", ".json": "application/json", ".js": "text/javascript", ".css": "text/css", ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml", ".txt": "text/plain; charset=utf-8" };
const seg = "([a-z0-9][a-z0-9._-]*)";
const boardRoute = new RegExp(`^/${seg}/${seg}/${seg}/(feedback|chat|thread|events)$`);
const kinds = ["comment", "change", "question"];
const clients = new Map();
const watched = new Set();

// Read on each check, so adding a login needs no restart.
function owners() {
  try {
    if (fs.statSync(ownersFile).mode & 0o077) return new Set();
    return new Set(fs.readFileSync(ownersFile, "utf8").split("\n").map(l => l.trim().toLowerCase()).filter(l => l && !l.startsWith("#")));
  } catch { return new Set(); }
}
// Tailscale sends a non-ASCII display name as an RFC 2047 word (=?utf-8?q?...?= or =?utf-8?b?...?=).
function headerText(v) {
  const m = /^=\?utf-8\?([qb])\?(.*)\?=$/i.exec(String(v || "").trim());
  if (!m) return String(v || "").trim();
  if (m[1].toLowerCase() === "b") return Buffer.from(m[2], "base64").toString("utf8");
  return Buffer.from(m[2].replace(/_/g, " ").replace(/=([0-9a-f]{2})/gi, (_, h) => String.fromCharCode(parseInt(h, 16))), "latin1").toString("utf8");
}
// null when not signed in; who is the display name for a tailnet sign-in.
function signedIn(req) {
  if ((req.headers.cookie || "").split(/;\s*/).includes(`board_k=${token}`)) return {};
  const login = String(req.headers["tailscale-user-login"] || "").trim().toLowerCase();
  if (login && owners().has(login)) return { who: headerText(req.headers["tailscale-user-name"]) || login };
  return null;
}
const end = (res, code, body, type = "text/plain; charset=utf-8") => { res.writeHead(code, { "Content-Type": type, "Cache-Control": "no-store" }); res.end(body); };
// status and reply carry the thread, so only signed-in browsers get them; reload goes to every open page.
const emit = (dir, event, data) => {
  for (const [res, authed] of clients.get(dir) || []) if (authed || event === "reload") res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
};
const readJson = file => { try { return JSON.parse(fs.readFileSync(file, "utf8")); } catch { return null; } };

// Watch a board once: index.html changes reload open pages; status/ and done/ files become events.
function watch(dir) {
  if (watched.has(dir)) return;
  watched.add(dir);
  for (const sub of ["inbox", "processing", "status", "done"]) fs.mkdirSync(path.join(dir, "feedback", sub), { recursive: true });
  let pending;
  fs.watch(dir, (_e, file) => { if (file === "index.html") { clearTimeout(pending); pending = setTimeout(() => emit(dir, "reload", {}), 400); } });
  for (const [sub, event] of [["status", "status"], ["done", "reply"]]) {
    fs.watch(path.join(dir, "feedback", sub), (_e, file) => {
      if (!file || !file.endsWith(".json")) return;
      const data = readJson(path.join(dir, "feedback", sub, file));
      if (data) emit(dir, event, data);
    });
  }
}

let lastMs = 0;
const notSignedIn = res => end(res, 401, "Not signed in: open the board through its tailnet address as a listed owner, or open its login link (board.cjs login).");

// Read a JSON body and queue what build() makes of it as feedback/inbox/<id>.json, status "queued". File names sort in
// send order, and the bridge delivers them in that order.
function enqueue(req, res, dir, board, build) {
  const me = signedIn(req);
  if (!me) return notSignedIn(res);
  if (!/^application\/json\b/.test(req.headers["content-type"] || "")) return end(res, 415, "JSON only");
  let body = "";
  req.on("data", chunk => { body += chunk; if (body.length > 65536) req.destroy(); });
  req.on("end", () => {
    let data;
    try { data = JSON.parse(body); } catch { return end(res, 400, "Bad JSON"); }
    const item = build(data || {}, me);
    if (typeof item === "string") return end(res, 400, item);
    lastMs = Math.max(Date.now(), lastMs + 1); // strictly increasing, so two sends in one millisecond keep their order
    const id = `${new Date(lastMs).toISOString().replace(/[:.]/g, "-")}-${crypto.randomBytes(3).toString("hex")}`;
    watch(dir);
    fs.writeFileSync(path.join(dir, "feedback", "inbox", `${id}.json`), JSON.stringify({ id, board, received_at: new Date().toISOString(), ...item }, null, 2));
    fs.writeFileSync(path.join(dir, "feedback", "status", `${id}.json`), JSON.stringify({ id, state: "queued", at: new Date().toISOString() }));
    end(res, 202, JSON.stringify({ id }), "application/json");
  });
}
const clip = (v, n) => String(v || "").slice(0, n);
function notesItem(data) {
  const notes = (Array.isArray(data.notes) ? data.notes : []).slice(0, 50).map(n => ({
    id: clip(n.id, 40), kind: kinds.includes(n.kind) ? n.kind : "comment", anchor: clip(n.anchor, 200), quote: clip(n.quote, 500), text: clip(n.text, 4000),
  })).filter(n => n.text.trim());
  return notes.length ? { notes } : "No notes";
}
function chatItem(data, me) {
  const text = clip(data.text, 8000);
  if (!text.trim()) return "Empty message";
  const item = { kind: "chat", text };
  if (data.anchor) item.anchor = clip(data.anchor, 200);
  if (data.quote) item.quote = clip(data.quote, 500);
  if (me.who) item.who = me.who;
  return item;
}

// The board's thread: every request still in inbox/ or processing/ (the bridge keeps delivered ones there), newest
// `limit`, oldest first, joined with its latest status and reply.
function thread(req, res, dir, url) {
  if (!signedIn(req)) return notSignedIn(res);
  watch(dir);
  const fb = path.join(dir, "feedback"), limit = Math.min(200, Math.max(1, parseInt(url.searchParams.get("limit"), 10) || 50));
  const files = [];
  for (const sub of ["inbox", "processing"]) for (const f of fs.readdirSync(path.join(fb, sub))) if (f.endsWith(".json")) files.push([f, sub]);
  const items = files.sort((a, b) => (a[0] < b[0] ? -1 : 1)).slice(-limit).flatMap(([f, sub]) => {
    const d = readJson(path.join(fb, sub, f));
    if (!d || !d.id) return [];
    const st = readJson(path.join(fb, "status", f)) || {}, done = readJson(path.join(fb, "done", f));
    const it = { id: d.id, kind: d.kind === "chat" ? "chat" : "notes", at: d.received_at, state: st.state || "queued", state_at: st.at || d.received_at };
    if (it.kind === "chat") Object.assign(it, { text: d.text, anchor: d.anchor, quote: d.quote });
    else it.notes = Array.isArray(d.notes) ? d.notes : [];
    if (done) Object.assign(it, { reply: String(done.reply || ""), reply_at: done.at });
    return [it];
  });
  end(res, 200, JSON.stringify({ items }), "application/json");
}

function events(req, res, dir) {
  watch(dir);
  res.writeHead(200, { "Content-Type": "text/event-stream", "Cache-Control": "no-store", Connection: "keep-alive" });
  const me = signedIn(req);
  res.write(`event: hello\ndata: ${JSON.stringify(me ? { auth: true, ...me } : { auth: false })}\n\n`);
  if (!clients.has(dir)) clients.set(dir, new Map());
  clients.get(dir).set(res, !!me);
  const beat = setInterval(() => res.write(": beat\n\n"), 25000);
  req.on("close", () => { clearInterval(beat); clients.get(dir).delete(res); });
}

function staticFile(req, res, url) {
  const p = decodeURIComponent(url.pathname);
  if (url.searchParams.get("k") === token) {
    // Set the cookie, then drop the token from the address bar and history.
    res.writeHead(302, { "Set-Cookie": `board_k=${token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=31536000`, Location: p.endsWith("/") ? "./" : path.basename(p) });
    return res.end();
  }
  if (p.split("/").some(s => s.startsWith(".")) || p.includes("/feedback/")) return end(res, 404, "Not found");
  let file = path.join(root, p);
  if (file !== root && !file.startsWith(root + path.sep)) return end(res, 403, "Forbidden");
  let stat;
  try { stat = fs.statSync(file); } catch { return end(res, 404, "Not found"); }
  if (stat.isDirectory()) {
    if (!p.endsWith("/")) { res.writeHead(301, { Location: `${path.basename(p)}/${url.search}` }); return res.end(); }
    file = path.join(file, "index.html");
    if (!fs.existsSync(file)) return end(res, 404, "Not found");
  }
  res.writeHead(200, { "Content-Type": types[path.extname(file)] || "application/octet-stream", "Cache-Control": "no-cache" });
  fs.createReadStream(file).pipe(res);
}

http.createServer((req, res) => {
  const url = new URL(req.url, "http://board.local");
  const m = decodeURIComponent(url.pathname).match(boardRoute);
  if (!m) return req.method === "GET" || req.method === "HEAD" ? staticFile(req, res, url) : end(res, 405, "Method not allowed");
  const dir = path.join(root, m[1], m[2], m[3]);
  if (!fs.existsSync(path.join(dir, "board.json"))) return end(res, 404, "No such board");
  if (m[4] === "events" && req.method === "GET") return events(req, res, dir);
  const board = `${m[1]}/${m[2]}/${m[3]}`;
  if (m[4] === "feedback" && req.method === "POST") return enqueue(req, res, dir, board, notesItem);
  if (m[4] === "chat" && req.method === "POST") return enqueue(req, res, dir, board, chatItem);
  if (m[4] === "thread" && req.method === "GET") return thread(req, res, dir, url);
  return end(res, 405, "Method not allowed");
}).listen(port, "127.0.0.1", () => console.log(`board server: http://127.0.0.1:${port}/ serving ${root}`));
