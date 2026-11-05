#!/usr/bin/env node
// Tracking boards: one HTML page per initiative, rendered from board.json.
//   board.cjs init <org>/<project>/<slug> [--title "..."]   create board.json and index.html
//   board.cjs render <org>/<project>/<slug> | <dir>          rebuild index.html from board.json
//   board.cjs url <org>/<project>/<slug>                     print the tailnet URL
//   board.cjs list                                           list boards with their headline
// Root: $OPENRIG_BOARDS_ROOT (default ~/.share/openrig/boards). URL base: $OPENRIG_BOARDS_URL, else the
// tailnet name from `tailscale status --json` plus /boards (see serve.sh).
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const { execFileSync } = require("node:child_process");

const root = process.env.OPENRIG_BOARDS_ROOT || path.join(os.homedir(), ".share", "openrig", "boards");
const template = path.join(__dirname, "template.html");
const slugRe = /^[a-z0-9][a-z0-9._-]*\/[a-z0-9][a-z0-9._-]*\/[a-z0-9][a-z0-9._-]*$/;

function die(msg) { console.error(`board: ${msg}`); process.exit(2); }

function boardDir(arg) {
  if (!arg) die("give <org>/<project>/<slug> or a board directory");
  if (fs.existsSync(path.join(arg, "board.json"))) return path.resolve(arg);
  if (!slugRe.test(arg)) die(`not <org>/<project>/<slug> (lowercase, digits, . _ -): ${arg}`);
  return path.join(root, arg);
}

function now() {
  const d = new Date();
  const pad = n => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function render(dir) {
  const file = path.join(dir, "board.json");
  const data = JSON.parse(fs.readFileSync(file, "utf8"));
  for (const key of ["title", "missions", "decisions"]) if (!(key in data)) die(`${file} has no "${key}"`);
  const json = JSON.stringify(data, null, 2).replace(/<\//g, "<\\/");
  fs.writeFileSync(path.join(dir, "index.html"), fs.readFileSync(template, "utf8").replace("__BOARD_JSON__", () => json));
  return path.join(dir, "index.html");
}

function base() {
  if (process.env.OPENRIG_BOARDS_URL) return process.env.OPENRIG_BOARDS_URL.replace(/\/$/, "");
  for (const bin of ["tailscale", "/Applications/Tailscale.app/Contents/MacOS/Tailscale"]) {
    try {
      const self = JSON.parse(execFileSync(bin, ["status", "--json"], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] })).Self;
      return `https://${self.DNSName.replace(/\.$/, "")}/boards`;
    } catch { /* try the next binary */ }
  }
  return "?/boards";
}

const [cmd, arg, ...rest] = process.argv.slice(2);
if (cmd === "init") {
  const dir = boardDir(arg);
  if (fs.existsSync(path.join(dir, "board.json"))) die(`${dir}/board.json exists; edit it and run render`);
  const titleAt = rest.indexOf("--title");
  const [org, project, slug] = arg.split("/");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "board.json"), JSON.stringify({
    title: titleAt >= 0 ? rest[titleAt + 1] : `${org} ${project}: ${slug}`,
    org, project, slug, updated: now(), headline: "", phase: "Started",
    needs: [], sections: [], diagrams: {}, missions: [], log: [], decisions: [], facts: [], links: [],
  }, null, 2) + "\n");
  console.log(render(dir));
  console.log(`${base()}/${arg}/`);
} else if (cmd === "render") {
  console.log(render(boardDir(arg)));
} else if (cmd === "url") {
  boardDir(arg);
  console.log(`${base()}/${arg}/`);
} else if (cmd === "list") {
  if (!fs.existsSync(root)) process.exit(0);
  for (const org of fs.readdirSync(root)) for (const project of fs.readdirSync(path.join(root, org)))
    for (const slug of fs.readdirSync(path.join(root, org, project))) {
      const file = path.join(root, org, project, slug, "board.json");
      if (!fs.existsSync(file)) continue;
      const data = JSON.parse(fs.readFileSync(file, "utf8"));
      console.log(`${org}/${project}/${slug}\t${data.updated || "?"}\t${data.headline || data.title}`);
    }
} else {
  die("usage: board.cjs init|render|url <org>/<project>/<slug> [--title \"...\"] | list");
}
