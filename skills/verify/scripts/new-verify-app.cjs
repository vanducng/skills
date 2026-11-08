#!/usr/bin/env node
// Write a verify-<app> skill: the commands that boot, check and test one app, read from the repo itself.
//   new-verify-app.cjs <app> --repo <app repo> --out <skills dir> [--force]
// Sources, in order: package.json scripts, a Makefile, docker-compose.yml. Each command is listed only if the repo
// defines it. The skill carries `verified: <date> at <sha>`, which stale.cjs ages.
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const [app, ...rest] = process.argv.slice(2);
const opt = n => { const i = rest.indexOf(n); return i === -1 ? null : rest[i + 1]; };
const fail = m => { process.stderr.write(`new-verify-app: ${m}\n`); process.exit(2); };
if (!app || !/^[a-z0-9][a-z0-9-]*$/.test(app)) fail("usage: new-verify-app.cjs <app, kebab-case> --repo <dir> --out <skills dir> [--force]");
const repo = path.resolve(opt("--repo") || "."), out = opt("--out");
if (!out) fail("--out <skills dir> is required");
const target = path.join(out, `verify-${app}`, "SKILL.md");
if (fs.existsSync(target) && !rest.includes("--force")) fail(`${target} exists; pass --force to rewrite it`);

const rows = [];
const add = (purpose, cmd, source) => rows.push({ purpose, cmd, source });
const pkg = path.join(repo, "package.json");
if (fs.existsSync(pkg)) {
  const scripts = (JSON.parse(fs.readFileSync(pkg, "utf8")).scripts) || {};
  const run = n => (n === "start" || n === "test" ? `npm ${n}` : `npm run ${n}`);
  const pick = (purpose, names) => { const n = names.find(x => scripts[x]); if (n) add(purpose, run(n), `package.json scripts.${n}`); };
  if (fs.existsSync(path.join(repo, "package-lock.json"))) add("install", "npm ci", "package-lock.json");
  pick("boot", ["start", "dev", "serve"]);
  pick("health", ["health", "healthcheck", "smoke"]);
  pick("test", ["test"]);
  pick("e2e", ["e2e", "test:e2e"]);
}
const mk = path.join(repo, "Makefile");
if (fs.existsSync(mk)) for (const t of ["up", "run", "health", "test", "e2e"]) if (new RegExp(`^${t}:`, "m").test(fs.readFileSync(mk, "utf8"))) add(t === "up" || t === "run" ? "boot" : t, `make ${t}`, `Makefile ${t}`);
for (const f of ["docker-compose.yml", "compose.yaml", "compose.yml"]) if (fs.existsSync(path.join(repo, f))) { add("boot", `docker compose -f ${f} up -d`, f); add("teardown", `docker compose -f ${f} down -v`, f); break; }
if (!rows.length) fail(`found no package.json scripts, Makefile targets or compose file in ${repo}: write the commands by hand`);

const sha = (spawnSync("git", ["rev-parse", "--short", "HEAD"], { cwd: repo, encoding: "utf8" }).stdout || "").trim() || "unknown";
const today = new Date().toISOString().slice(0, 10);
const body = `---
name: verify-${app}
description: "Boots, checks and tests ${app} so a change can be proved on its parent and its head. Use when verifying, QA-ing or proving a change to ${app}."
license: MIT
metadata:
  verified: "${today} at ${sha}"
---

# verify-${app}

The commands that prove ${app} works, read from the repo. Run them through the verify skill's \`both.sh\` to compare parent and head.

| Purpose | Command | Defined in |
|---|---|---|
${rows.map(r => `| ${r.purpose} | \`${r.cmd}\` | ${r.source} |`).join("\n")}

## Upkeep

\`verified\` is the last date these commands were run green. Re-run them and update it after any change to the files in "Defined in"; the verify skill's \`stale.cjs\` flags this skill when it is old or a command is gone.
`;
fs.mkdirSync(path.dirname(target), { recursive: true });
fs.writeFileSync(target, body);
process.stdout.write(JSON.stringify({ file: target, commands: rows.length, verified: `${today} at ${sha}` }) + "\n");
