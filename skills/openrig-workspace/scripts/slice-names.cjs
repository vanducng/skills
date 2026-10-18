#!/usr/bin/env node
// Prints every name a slice uses (slice id, worktrees, branch, PR tag), derived from its folder and its mission's
// SPEC.md frontmatter, so no name is typed by hand.

const fs = require("fs");
const path = require("path");

const args = process.argv.slice(2);
const json = args.includes("--json");

function fail(message) {
  if (json) process.stdout.write(`${JSON.stringify({ ok: false, error: message })}\n`);
  else process.stderr.write(`${message}\n`);
  process.exit(1);
}

function flags(name) {
  const values = [];
  args.forEach((arg, i) => {
    if (arg === name) {
      const value = args[i + 1];
      if (!value || value.startsWith("--")) fail(`${name} needs a value.`);
      values.push(value);
    }
  });
  return values;
}

function frontmatter(file) {
  if (!fs.existsSync(file)) return {};
  const match = fs.readFileSync(file, "utf8").match(/^---\n([\s\S]*?)\n---/);
  const fields = {};
  for (const line of match ? match[1].split("\n") : []) {
    const pair = line.match(/^([a-z_]+):\s*(.*)$/);
    if (pair) fields[pair[1]] = pair[2].replace(/^["']|["']$/g, "").trim();
  }
  return fields;
}

function workspaceRoot(from) {
  for (let dir = from; dir !== path.dirname(dir); dir = path.dirname(dir)) {
    if (fs.existsSync(path.join(dir, "workspace.yaml"))) return dir;
  }
  return process.env.PROJECTS_ROOT || null;
}

const positional = args.filter((arg, i) => !arg.startsWith("--") && !["--repo", "--type"].includes(args[i - 1]));
if (positional.length !== 1) fail("Usage: slice-names.cjs <slice dir> [--repo <repo>]... [--type feat|fix|chore|docs|test|refactor|perf] [--json]");

const sliceDir = path.resolve(positional[0]);
const folder = path.basename(sliceDir).match(/^(\d{2})-([a-z0-9][a-z0-9-]*)$/);
if (!folder) fail(`${path.basename(sliceDir)} is not a slice folder (<nn>-<slug>).`);
if (path.basename(path.dirname(sliceDir)) !== "slices") fail(`${sliceDir} is not under a mission's slices/ folder.`);

const missionDir = path.dirname(path.dirname(sliceDir));
const mission = frontmatter(path.join(missionDir, "SPEC.md"));
const prefix = path.basename(missionDir).match(/^(m\d+)-/);
const code = (mission.code || (prefix && prefix[1]) || "").toLowerCase();
if (!/^[a-z][a-z0-9]*$/.test(code)) fail(`Set code: in ${path.join(missionDir, "SPEC.md")} frontmatter (the mission folder has no m<n>- prefix).`);

const [, nn, slug] = folder;
const sliceId = `${code}-s${nn}`;
const milestone = mission.milestone || (code.match(/^m(\d+)$/) || [])[1] || null;
const ticket = mission.ticket || null;
const type = flags("--type")[0] || "feat";
if (!/^(feat|fix|chore|docs|test|refactor|perf)$/.test(type)) fail(`Unknown --type ${type}.`);

const root = workspaceRoot(sliceDir);
const worktrees = flags("--repo").map((repo) => {
  if (!/^[a-z0-9][a-z0-9._-]*$/.test(repo)) fail(`Repo name ${repo} must be lowercase letters, digits, '.', '_' or '-'.`);
  const name = `${repo}-${sliceId}`;
  if (name.length > 63) fail(`${name} is longer than a 63-character host label; shorten the mission code.`);
  return { repo, name, path: root ? path.join(root, ".worktrees", name) : null };
});

const branch = `${type}/${ticket ? `${ticket}-` : ""}${sliceId}-${slug}`;
const result = {
  sliceId,
  worktrees,
  branch,
  followUpBranch: `${branch}-2`,
  prTag: ticket && milestone ? `[${ticket}|M${milestone}|S${Number(nn)}]` : null,
};

if (json) {
  process.stdout.write(`${JSON.stringify({ ok: true, ...result })}\n`);
} else {
  const lines = [`slice id: ${sliceId}`];
  for (const w of worktrees) lines.push(`worktree: ${w.name}${w.path ? ` (${w.path})` : ""}`);
  lines.push(`branch: ${result.branch}`, `follow-up branch: ${result.followUpBranch}`);
  lines.push(`pr tag: ${result.prTag || `none (set ticket: and milestone: in ${path.join(missionDir, "SPEC.md")})`}`);
  process.stdout.write(`${lines.join("\n")}\n`);
}
