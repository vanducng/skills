#!/usr/bin/env node
// Ship pre-flight checks on the branch's diff against its target.
//
//   preflight.cjs overlap --base <ref> [--repo <owner/name>]   other open PRs that touch the same files (warns, exit 0)
//   preflight.cjs tests --base <ref> [--run]                   the touched packages' test commands, one PR-body line each
//
// tests: each changed file (docs aside) belongs to the nearest directory that has a test command, by the table in
// references/auto-detect.md. Prints "- `<command>`" for the repository root and "- `cd <dir> && <command>`" for a
// package below it; in a pnpm workspace a package's line is "- `pnpm --filter <package.json name> test`". --run runs each and appends ": pass" or ": failed (exit n)"; any failure exits 1.
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const DOCS = /\.(md|mdx|txt|rst)$|(^|\/)docs\//i;
const a = process.argv.slice(2), opt = k => (a.includes(k) ? a[a.indexOf(k) + 1] : null);
const die = (msg, code = 2) => { process.stderr.write(`preflight: ${msg}\n`); process.exit(code); };
const sh = (cmd, args) => { const r = spawnSync(cmd, args, { encoding: "utf8", maxBuffer: 1 << 26 }); if (r.status !== 0) die(`${cmd} ${args[0]} failed: ${String(r.stderr || r.error).trim().slice(0, 200)}`); return r.stdout; };
const base = opt("--base") || die("--base <ref> is required");
const top = sh("git", ["rev-parse", "--show-toplevel"]).trim();
// The branch's changes against where it left the target, committed or not (ship includes uncommitted work), plus new files.
const fork = sh("git", ["merge-base", base, "HEAD"]).trim();
const changed = [...new Set([...sh("git", ["diff", "--name-only", fork]).split("\n"), ...sh("git", ["ls-files", "--others", "--exclude-standard"]).split("\n")])].filter(Boolean);

// The test command a directory declares, or null. First match wins, as in references/auto-detect.md.
function testCommand(dir) {
  const read = f => { try { return fs.readFileSync(path.join(top, dir, f), "utf8"); } catch { return null; } };
  const scripts = f => { try { return (JSON.parse(read(f) || "{}").scripts || {}).test; } catch { return null; } };
  if (scripts("package.json")) {
    // A pnpm workspace runs a package's tests from the root by name.
    const name = dir !== "." && fs.existsSync(path.join(top, "pnpm-workspace.yaml")) && JSON.parse(read("package.json")).name;
    return name ? { pnpm: `pnpm --filter ${name} test` } : "npm test";
  }
  if (/^test:/m.test(read("Makefile") || "")) return "make test";
  if (read("pytest.ini") != null || /\[tool\.pytest/.test(read("pyproject.toml") || "")) return "pytest";
  if (read("Cargo.toml") != null) return "cargo test";
  if (read("go.mod") != null) return "go test ./...";
  if (scripts("composer.json")) return "composer test";
  return null;
}

function tests() {
  const code = changed.filter(f => !DOCS.test(f));
  if (!code.length) { console.log("docs only: no test command needed"); return; }
  const found = new Map(), missing = new Set();
  for (const f of code) {
    let dir = path.dirname(f);
    for (;;) {
      const cmd = testCommand(dir);
      if (cmd) { found.set(dir, cmd); break; }
      if (dir === ".") { missing.add(f.includes("/") ? f.split("/")[0] : "."); break; }
      dir = path.dirname(dir);
    }
  }
  let failed = 0;
  for (const dir of [...found.keys()].sort((x, y) => (x === "." ? -1 : y === "." ? 1 : x.localeCompare(y)))) {
    const cmd = found.get(dir), shown = cmd.pnpm || (dir === "." ? cmd : `cd ${dir} && ${cmd}`);
    const [line, cwd] = cmd.pnpm ? [cmd.pnpm, top] : [cmd, path.join(top, dir)];
    if (!a.includes("--run")) { console.log(`- \`${shown}\``); continue; }
    const r = spawnSync("sh", ["-c", line], { cwd, stdio: ["ignore", "ignore", "inherit"] });
    if (r.status !== 0) failed++;
    console.log(`- \`${shown}\`: ${r.status === 0 ? "pass" : `failed (exit ${r.status})`}`);
  }
  if (missing.size) console.log(`no test command found for: ${[...missing].sort().join(", ")} (ask once, as Step 4 says)`);
  if (failed) process.exit(1);
}

function overlap() {
  const branch = sh("git", ["branch", "--show-current"]).trim(), mine = new Set(changed);
  const repo = opt("--repo") ? ["-R", opt("--repo")] : [];
  // A warning only: when gh cannot list the open PRs, say so and carry on.
  const r = spawnSync("gh", ["pr", "list", ...repo, "--state", "open", "--limit", "100", "--json", "number,title,headRefName,files"], { encoding: "utf8", maxBuffer: 1 << 26 });
  let prs = null;
  try { prs = r.status === 0 ? JSON.parse(r.stdout) : null; } catch { /* not JSON */ }
  if (!Array.isArray(prs)) {
    const why = r.status === 0 ? "gh pr list did not return a JSON list" : `gh pr list failed: ${String(r.stderr || r.error || `exit ${r.status}`).trim().slice(0, 160)}`;
    console.log(`warn: overlap unchecked: ${why}`); return;
  }
  const hits = prs.filter(p => p.headRefName !== branch)
    .map(p => [p, (p.files || []).map(f => f.path).filter(f => mine.has(f))]).filter(([, same]) => same.length);
  if (!hits.length) { console.log("no other open PR touches these files"); return; }
  for (const [p, same] of hits) console.log(`warn: #${p.number} ${p.title}: ${same.join(", ")}`);
}

if (a[0] === "tests") tests();
else if (a[0] === "overlap") overlap();
else die("usage: preflight.cjs overlap|tests --base <ref> (see the header of this file)");
