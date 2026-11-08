#!/usr/bin/env node
// Scaffolds a project in one step: the five files every project carries, an empty missions/ root, and its entry in
// workspace.yaml. Then runs check-resources.sh on the new project and exits with its code.
//   node new-project.cjs <org> <project> --host <machine id> [--intent "<one sentence>"] [--root <workspace root>]
// Root: --root, else $PROJECTS_ROOT, else the nearest parent of the cwd that holds workspace.yaml.
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const name = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

function fail(msg) { process.stderr.write(`new-project: ${msg}\n`); process.exit(2); }

function parse(argv) {
  const out = { pos: [], opts: {} };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--host" || a === "--intent" || a === "--root") {
      const v = argv[++i];
      if (v === undefined || v.startsWith("--")) fail(`${a} needs a value`);
      if (a.slice(2) in out.opts) fail(`${a} given twice`);
      out.opts[a.slice(2)] = v;
    } else if (a.startsWith("-")) fail(`unknown option or option-looking name ${a}`);
    else out.pos.push(a);
  }
  return out;
}

function findRoot(given) {
  const start = given || process.env.PROJECTS_ROOT;
  if (start) {
    const r = path.resolve(start);
    if (!fs.existsSync(path.join(r, "workspace.yaml"))) fail(`no workspace.yaml in ${r}`);
    return r;
  }
  for (let d = process.cwd(); ; d = path.dirname(d)) {
    if (fs.existsSync(path.join(d, "workspace.yaml"))) return d;
    if (path.dirname(d) === d) fail("no workspace.yaml above the current directory; pass --root");
  }
}

// Machine ids are the keys under `machines:` in fleet/machines.yaml, read with yq (check-resources.sh needs it too), so
// any indent or quoting works. Without that file any host is accepted, with a warning.
function machines(root) {
  const file = path.join(root, "fleet", "machines.yaml");
  if (!fs.existsSync(file)) return null;
  const r = spawnSync("yq", ["-o=json", ".machines // {} | keys", file], { encoding: "utf8" });
  if (r.error) fail("yq (mikefarah v4) is required to read fleet/machines.yaml");
  if (r.status !== 0) fail(`cannot read ${file}: ${r.stderr.trim()}`);
  return JSON.parse(r.stdout);
}

// Returns workspace.yaml with the entry added after the last project already listed, every other line as it was.
// Called before anything is written, so a workspace.yaml it cannot extend refuses the run with no files created.
function withProject(file, id, rel) {
  const lines = fs.readFileSync(file, "utf8").split("\n");
  const start = lines.findIndex(l => /^projects:\s*$/.test(l));
  if (start < 0) fail(`${file} has no block projects: list; fix it before adding a project`);
  let end = start + 1;
  for (let i = start + 1; i < lines.length; i++) {
    if (/^\s+\S/.test(lines[i])) end = i + 1;
    else if (/^\S/.test(lines[i])) break;
  }
  lines.splice(end, 0, `  - id: ${id}`, `    root: ${rel}`, "    rigs: []");
  return lines.join("\n");
}

const argv = process.argv.slice(2);
if (argv.length === 1 && (argv[0] === "--help" || argv[0] === "-h")) {
  process.stdout.write("usage: node new-project.cjs <org> <project> --host <machine id> [--intent \"<one sentence>\"] [--root <workspace root>]\n");
  process.exit(0);
}
const { pos, opts } = parse(argv);
if (pos.length !== 2) fail("give <org> and <project>; usage: new-project.cjs <org> <project> --host <machine id>");
const [org, project] = pos;
for (const [what, v] of [["org", org], ["project", project]]) {
  if (!name.test(v)) fail(`invalid ${what} name '${v}': lowercase letters, digits and single '-' between them`);
}
if (!opts.host) fail("--host <machine id> is required (the one machine this project runs on)");
if (!/^[A-Za-z0-9][\w.-]*$/.test(opts.host)) fail(`invalid host '${opts.host}'`);

const root = findRoot(opts.root);
const orgDir = path.join(root, "orgs", org);
if (!fs.existsSync(orgDir)) fail(`org '${org}' does not exist under ${path.join(root, "orgs")}; create the org first`);
const rel = `orgs/${org}/projects/${project}`;
const dir = path.join(root, rel);
if (fs.existsSync(dir)) fail(`${rel} already exists`);
const workspace = path.join(root, "workspace.yaml");
if (new RegExp(`^\\s+- id: ${org}\\.${project}\\s*$`, "m").test(fs.readFileSync(workspace, "utf8"))) fail(`${org}.${project} is already in workspace.yaml`);

const workspaceText = withProject(workspace, `${org}.${project}`, rel);
const known = machines(root);
if (known && !known.includes(opts.host)) fail(`unknown host '${opts.host}'; fleet/machines.yaml has: ${known.join(", ") || "(none)"}`);
if (!known) process.stderr.write(`new-project: warning: no fleet/machines.yaml under ${root}; host '${opts.host}' not checked\n`);

// JSON.stringify output is a valid YAML double-quoted scalar, so any quote, backslash or colon is safe.
const intent = JSON.stringify((opts.intent || `What ${project} delivers, in one sentence. Replace this before the first mission.`).replace(/\s+/g, " ").trim());
const files = {
  "AGENTS.md": `# ${project}\n\nWhat ${project} is and who it is for, in two or three lines.\n\n## Repos\n\n| Repo | Role here |\n|---|---|\n\n## Rules\n\n- Project resources (channels, meetings, dashboards, docs): \`resources.yaml\` in this folder, pointing into the org's \`../../resources.yaml\` by id. Data only, never secrets.\n- Before changing a project, mission, slice, task dir, worktree, rig or seat, load the \`openrig-workspace\` skill.\n`,
  "SPEC.md": `---\nintent: ${intent}\n---\n\n# ${project}\n\nAgent-facing context is in \`AGENTS.md\` next to this file.\n`,
  "project.yaml": `schema: openrig.project/v0alpha1\nkind: project\nmetadata:\n  id: ${org}.${project}\n  name: ${project}\ninstall:\n  intent: SPEC.md\n  context: []\n  skills: []\nmissions:\n  root: missions\n`,
  "repos.yaml": `schema: projects.project-repos/v1\n# The one machine this project runs on (fleet/machines.yaml id). Rigs, task dirs and worktrees exist only there.\nhost: ${opts.host}\nrepos: []\n`,
  "resources.yaml": "schema: projects.resources/v2\n",
  "missions/.gitkeep": "",
};

fs.mkdirSync(path.join(dir, "missions"), { recursive: true });
for (const [f, body] of Object.entries(files)) fs.writeFileSync(path.join(dir, f), body);
fs.writeFileSync(workspace, workspaceText);
process.stdout.write(`created ${rel}/ (${Object.keys(files).join(", ")}) and added ${org}.${project} to workspace.yaml\n`);

const check = spawnSync("bash", [path.join(__dirname, "check-resources.sh"), dir], { stdio: "inherit" });
process.exit(check.status === null ? 2 : check.status);
