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
  const match = fs.readFileSync(file, "utf8").match(/^---\r?\n([\s\S]*?)\r?\n---/);
  const fields = {};
  for (const line of match ? match[1].split(/\r?\n/) : []) {
    const pair = line.match(/^([a-z_]+):\s*(.*)$/);
    if (!pair) continue;
    const raw = pair[2].trim();
    const quoted = raw.match(/^(["'])(.*?)\1/);
    fields[pair[1]] = quoted ? quoted[2] : raw.replace(/\s+#.*$/, "");
  }
  return fields;
}

function workspaceRoot(from) {
  for (let dir = from; dir !== path.dirname(dir); dir = path.dirname(dir)) {
    if (fs.existsSync(path.join(dir, "workspace.yaml"))) return dir;
  }
  const env = process.env.PROJECTS_ROOT;
  return env && fs.existsSync(env) ? env : null;
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
const specPath = path.join(missionDir, "SPEC.md");
if (mission.code && !/^[a-z][a-z0-9]*$/.test(mission.code)) fail(`code: ${mission.code} in ${specPath} must match ^[a-z][a-z0-9]*$ (for example m2).`);
const code = mission.code || (prefix && prefix[1]);
if (!code) fail(`Set code: in ${specPath} frontmatter; the mission folder has no m<n>- prefix.`);

const [, nn, slug] = folder;
const sliceId = `${code}-s${nn}`;
const milestone = mission.milestone || (prefix ? prefix[1].slice(1) : null);
if (milestone && !/^\d+$/.test(milestone)) fail(`milestone: ${milestone} in ${specPath} must be a number.`);
const ticket = mission.ticket || null;
if (ticket && !/^[A-Za-z][A-Za-z0-9]*-\d+$/.test(ticket)) fail(`ticket: ${ticket} in ${specPath} must look like ABC-123.`);
const types = flags("--type");
if (types.length > 1) fail("Pass --type once.");
const type = types[0] || "feat";
if (!/^(feat|fix|chore|docs|test|refactor|perf)$/.test(type)) fail(`Unknown --type ${type}.`);

const root = workspaceRoot(sliceDir);
const worktrees = flags("--repo").map((repo) => {
  if (!/^[a-z0-9][a-z0-9-]*$/.test(repo)) fail(`Repo name ${repo} must be lowercase letters, digits or '-', so it works as a host label and compose project.`);
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
  if (worktrees.length && !root) lines.push("worktree root: unknown (no workspace.yaml above the slice, and PROJECTS_ROOT is unset or missing)");
  lines.push(`branch: ${result.branch}`, `follow-up branch: ${result.followUpBranch}`);
  lines.push(`pr tag: ${result.prTag || `none (set ticket: and milestone: in ${specPath})`}`);
  process.stdout.write(`${lines.join("\n")}\n`);
}
