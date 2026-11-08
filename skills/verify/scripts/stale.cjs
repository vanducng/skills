#!/usr/bin/env node
// Is a verify-<app> skill still true? Flags an old `verified` date and any listed command its repo no longer defines.
//   stale.cjs <verify-app skill dir> --repo <app repo> [--days 14]
// Exit 0 fresh, 1 stale (reasons on stdout as JSON), 2 usage.
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const [dir, ...rest] = process.argv.slice(2);
const opt = n => { const i = rest.indexOf(n); return i === -1 ? null : rest[i + 1]; };
const fail = m => { process.stderr.write(`stale: ${m}\n`); process.exit(2); };
if (!dir) fail("usage: stale.cjs <verify-app skill dir> --repo <app repo> [--days 14]");
const file = path.join(dir, "SKILL.md");
if (!fs.existsSync(file)) fail(`${file} does not exist`);
const repo = path.resolve(opt("--repo") || "."), days = Number(opt("--days") || 14);
const text = fs.readFileSync(file, "utf8");
const reasons = [];
const v = text.match(/verified:\s*"?(\d{4}-\d{2}-\d{2})/);
if (!v) reasons.push("no `verified: <date>` line");
else {
  const age = Math.floor((Date.now() - Date.parse(`${v[1]}T00:00:00Z`)) / 86400000);
  if (age > days) reasons.push(`verified ${age} days ago (${v[1]}), over ${days}`);
}
const pkgPath = path.join(repo, "package.json");
const scripts = fs.existsSync(pkgPath) ? (JSON.parse(fs.readFileSync(pkgPath, "utf8")).scripts || {}) : null;
const make = fs.existsSync(path.join(repo, "Makefile")) ? fs.readFileSync(path.join(repo, "Makefile"), "utf8") : "";
for (const [, cmd] of text.matchAll(/\|\s*`([^`]+)`\s*\|/g)) {
  let m;
  if ((m = cmd.match(/^npm (?:run )?([\w:-]+)$/)) && m[1] !== "ci" && (!scripts || !scripts[m[1]])) reasons.push(`\`${cmd}\`: package.json has no script "${m[1]}"`);
  else if ((m = cmd.match(/^make ([\w-]+)$/)) && !new RegExp(`^${m[1]}:`, "m").test(make)) reasons.push(`\`${cmd}\`: the Makefile has no target "${m[1]}"`);
  else if ((m = cmd.match(/-f (\S+)/)) && /docker compose/.test(cmd) && !fs.existsSync(path.join(repo, m[1]))) reasons.push(`\`${cmd}\`: ${m[1]} is gone`);
}
process.stdout.write(JSON.stringify({ skill: dir, stale: reasons.length > 0, reasons }) + "\n");
process.exit(reasons.length ? 1 : 0);
