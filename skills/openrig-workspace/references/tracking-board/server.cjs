#!/usr/bin/env node
// Board server: static files for every board, plus per-board feedback and live events.
//   GET  /<org>/<project>/<slug>/            the board (index.html) and any page beside it
//   POST /<org>/<project>/<slug>/feedback    notes from the page -> feedback/inbox/<id>.json (needs the login cookie)
//   GET  /<org>/<project>/<slug>/events      server-sent events: hello, status, reply, reload
// Login: open any board URL with ?k=<token> once (board.cjs login prints it); the server sets an HttpOnly,
// SameSite=Strict cookie. The token lives in <root>/.board-token (mode 600). Bind is loopback only; publish with
// `tailscale serve` (serve.sh), never Funnel.
"use strict";
const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const crypto = require("node:crypto");

const root = path.resolve(process.env.OPENRIG_BOARDS_ROOT || path.join(os.homedir(), ".share", "openrig", "boards"));
const port = Number(process.env.OPENRIG_BOARDS_PORT || 47320);
const tokenFile = path.join(root, ".board-token");
fs.mkdirSync(root, { recursive: true });
if (!fs.existsSync(tokenFile)) fs.writeFileSync(tokenFile, crypto.randomBytes(24).toString("hex"), { mode: 0o600 });
const token = fs.readFileSync(tokenFile, "utf8").trim();

const types = { ".html": "text/html; charset=utf-8", ".json": "application/json", ".js": "text/javascript", ".css": "text/css", ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml", ".txt": "text/plain; charset=utf-8" };
const seg = "([a-z0-9][a-z0-9._-]*)";
const boardRoute = new RegExp(`^/${seg}/${seg}/${seg}/(feedback|events)$`);
const kinds = ["comment", "change", "question"];
const clients = new Map();
const watched = new Set();

const loggedIn = req => (req.headers.cookie || "").split(/;\s*/).includes(`board_k=${token}`);
const end = (res, code, body, type = "text/plain; charset=utf-8") => { res.writeHead(code, { "Content-Type": type, "Cache-Control": "no-store" }); res.end(body); };
const emit = (dir, event, data) => { for (const res of clients.get(dir) || []) res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`); };
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

function feedback(req, res, dir, board) {
  if (!loggedIn(req)) return end(res, 401, "Log in first: open the board's login link (board.cjs login).");
  if (!/^application\/json\b/.test(req.headers["content-type"] || "")) return end(res, 415, "JSON only");
  let body = "";
  req.on("data", chunk => { body += chunk; if (body.length > 65536) req.destroy(); });
  req.on("end", () => {
    let data;
    try { data = JSON.parse(body); } catch { return end(res, 400, "Bad JSON"); }
    const notes = (Array.isArray(data.notes) ? data.notes : []).slice(0, 50).map(n => ({
      id: String(n.id || "").slice(0, 40),
      kind: kinds.includes(n.kind) ? n.kind : "comment",
      anchor: String(n.anchor || "").slice(0, 200),
      quote: String(n.quote || "").slice(0, 500),
      text: String(n.text || "").slice(0, 4000),
    })).filter(n => n.text.trim());
    if (!notes.length) return end(res, 400, "No notes");
    const id = `${new Date().toISOString().replace(/[:.]/g, "-")}-${crypto.randomBytes(3).toString("hex")}`;
    watch(dir);
    fs.writeFileSync(path.join(dir, "feedback", "inbox", `${id}.json`), JSON.stringify({ id, board, received_at: new Date().toISOString(), notes }, null, 2));
    fs.writeFileSync(path.join(dir, "feedback", "status", `${id}.json`), JSON.stringify({ id, state: "queued", at: new Date().toISOString() }));
    end(res, 202, JSON.stringify({ id }), "application/json");
  });
}

function events(req, res, dir) {
  watch(dir);
  res.writeHead(200, { "Content-Type": "text/event-stream", "Cache-Control": "no-store", Connection: "keep-alive" });
  res.write(`event: hello\ndata: ${JSON.stringify({ auth: loggedIn(req) })}\n\n`);
  if (!clients.has(dir)) clients.set(dir, new Set());
  clients.get(dir).add(res);
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
  if (m[4] === "feedback" && req.method === "POST") return feedback(req, res, dir, `${m[1]}/${m[2]}/${m[3]}`);
  return end(res, 405, "Method not allowed");
}).listen(port, "127.0.0.1", () => console.log(`board server: http://127.0.0.1:${port}/ serving ${root}`));
