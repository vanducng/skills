// node --test skills/openrig-workspace/scripts/private-terms.test.cjs
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const P = path.join(__dirname, "private-terms.cjs");
const ENV = { PATH: process.env.PATH, HOME: os.tmpdir(), GIT_CONFIG_GLOBAL: "/dev/null", GIT_CONFIG_SYSTEM: "/dev/null",
  GIT_AUTHOR_NAME: "t", GIT_AUTHOR_EMAIL: "t@example.test", GIT_COMMITTER_NAME: "t", GIT_COMMITTER_EMAIL: "t@example.test" };
const run = (args, { env = {}, input } = {}) => {
  const r = spawnSync(process.execPath, [P, ...args], { env: { ...ENV, ...env }, encoding: "utf8", input });
  return { code: r.status, out: r.stdout, err: r.stderr, json: () => JSON.parse(r.stdout) };
};
const put = (root, rel, body) => { fs.mkdirSync(path.dirname(path.join(root, rel)), { recursive: true }); fs.writeFileSync(path.join(root, rel), body); };
const git = (cwd, ...a) => { const r = spawnSync("git", a, { cwd, env: ENV, encoding: "utf8" }); assert.equal(r.status, 0, r.stderr); return r.stdout; };

// Synthetic workspace: own org "mine" (public), client org "acme" with a person, a hyphenated repo and a host.
function workspace() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "terms-ws-"));
  put(root, "workspace.yaml", "schema: x\norgs:\n  - id: acme\n  - id: mine\nprojects:\n  - id: acme.billing-hub\n    root: orgs/acme/projects/billing-hub\n    rigs: [acme-team]\n  - id: acme.ops\n    root: orgs/acme/projects/ops\n");
  put(root, "orgs/acme/org.yaml", "schema: x\nid: acme\nname: \"Acme Widgets\"   # the client\ngithub_owner: acme-corp\n");
  put(root, "orgs/acme/repos.yaml", "schema: x\nclient: acme\nrepos:\n  - id: acme-ds-astro\n    origin: git@github.com:acme-corp/acme-ds-astro.git\n    paths:\n      lab: ~/git/acme-ds-astro\n  - id: ledgerline\n    origin: https://github.com/acme-corp/ledgerline\n");
  put(root, "orgs/acme/contacts.yaml", "schema: x\norg: acme\ncontacts:\n  priya:\n    name: Priya Raman\n    topics: [billing]\n");
  put(root, "orgs/acme/projects/billing-hub/repos.yaml", "host: lab-mini\nrepos:\n  - ledgerline\n");
  put(root, "orgs/acme/projects/ops/AGENTS.md", "x\n");
  put(root, "orgs/mine/org.yaml", "schema: x\nid: mine\nname: Mine\ngithub_owner: mine-dev\n");
  put(root, "orgs/mine/repos.yaml", "repos:\n  - id: toolbox\n    origin: git@github.com:mine-dev/toolbox.git\n");
  put(root, "orgs/mine/contacts.yaml", "contacts:\n  teo:\n    name: Teo Okafor\n");
  put(root, "fleet/machines.yaml", "schema: x\nmachines:\n  lab:\n    ssh_alias: lab-mini\n    hostname: labbox\n    openrig_id: lab-01\n    openrig_url: http://labbox-pro.tailabc123.ts.net:7433\n");
  git(root, "init", "-q", "-b", "main");
  git(root, "add", "-A");
  git(root, "commit", "-q", "-m", "records\n\nHost: buildhost9");
  return root;
}
const scan = (root, text, ...args) => run(["scan", "-", "--json", ...args], { env: { PROJECTS_ROOT: root }, input: text });
const hitTerms = r => [...new Set(r.json().hits.map(h => h.term.toLowerCase()))].sort();

test("terms come from every source, with their kinds", () => {
  const r = run(["terms", "--json"], { env: { PROJECTS_ROOT: workspace() } });
  assert.equal(r.code, 0, r.err);
  const got = Object.fromEntries(r.json().terms.map(t => [t.term.toLowerCase(), t.kind]));
  for (const [term, kind] of Object.entries({ acme: "org", "acme widgets": "org", "acme-corp": "owner", "acme-ds-astro": "repo",
    ledgerline: "repo", "billing-hub": "project", priya: "person", "priya raman": "person", raman: "person", "lab-mini": "host",
    labbox: "host", "lab-01": "host", "labbox-pro": "host", tailabc123: "host", buildhost9: "host", "mine-dev": "owner", toolbox: "repo" }))
    assert.equal(got[term], kind, term);
});

test("the two real escapes, as synthetic text: a hyphenated repo id, a lone surname, a DB__ORG_TABLE name", () => {
  const root = workspace();
  const r = scan(root, "fixed acme-ds-astro#12\nthanks Raman\nloaded MYSQL__ACME_LEDGERLINE\n");
  assert.equal(r.code, 1, r.out);
  assert.deepEqual(hitTerms(r), ["acme", "acme-ds-astro", "ledgerline", "raman"]);
  assert.deepEqual(r.json().hits.filter(h => h.term.toLowerCase() === "raman").map(h => h.line), [2]);
});

test("a longer word is not a hit, and multi-word names match with space, hyphen, underscore or joined", () => {
  const root = workspace();
  assert.equal(scan(root, "acmes and ledgerlines and toolboxes, priyanka\n", "--own", "mine").code, 0);
  for (const t of ["Acme Widgets", "acme-widgets", "ACME_WIDGETS", "acmewidgets"])
    assert.ok(hitTerms(scan(root, `${t}\n`, "--own", "mine")).includes("acme widgets"), t);
});

test("--own drops that org's names and repo ids, never its people or hosts", () => {
  const root = workspace();
  assert.equal(scan(root, "mine-dev/toolbox, by Mine\n", "--own", "mine").code, 0);
  assert.deepEqual(hitTerms(scan(root, "Teo Okafor on labbox\n", "--own", "mine")), ["labbox", "teo okafor"]);
  assert.equal(scan(root, "toolbox\n").code, 1); // without --own it is a repo id like any other
});

test("an allowed or own name is not reported in part: the client org inside an allowed repo id stays quiet", () => {
  const root = workspace();
  assert.equal(scan(root, "acme-ds-astro\n", "--own", "mine", "--allow", "acme-ds-astro").code, 0);
  assert.deepEqual(hitTerms(scan(root, "acme-ds-astro and acme\n", "--own", "mine", "--allow", "acme-ds-astro")), ["acme"]);
});

test("--allow takes only org, project, repo and owner names from the records, and says what it ignored", () => {
  const root = workspace();
  const r = scan(root, "acme-ds-astro by Priya\n", "--own", "mine", "--allow", "acme-ds-astro,priya,nosuch"); // Title case: rule (iii)
  assert.equal(r.code, 1);
  assert.deepEqual(hitTerms(r), ["priya"]);
  assert.deepEqual(r.json().allowed, ["acme-ds-astro"]);
  assert.deepEqual(r.json().ignored_allow, ["nosuch", "priya"]);
});

test("generic words drop only project ids, and every drop is listed", () => {
  const r = run(["terms", "--json"], { env: { PROJECTS_ROOT: workspace() } });
  const out = r.json();
  assert.ok(!out.terms.some(t => t.term === "ops"));
  assert.deepEqual(out.dropped, [{ term: "ops", kind: "project", org: "acme", source: "orgs/acme/projects/ops", why: "generic word" }]);
  const { GENERIC_PROJECT_WORDS } = require(P);
  assert.deepEqual([...GENERIC_PROJECT_WORDS].sort(), ["api", "app", "conductor", "dashboard", "data", "devlog", "docs", "infra", "ops", "platform", "products", "web", "workspace"]);
});

test("no records fails closed: exit 2", () => {
  assert.equal(run(["scan", "-", "--json"], { input: "acme\n" }).code, 2);
  assert.equal(run(["terms", "--json"], { env: { PROJECTS_ROOT: "/nonexistent" } }).code, 2);
});

test("--shapes adds private paths, tailnet hosts and emails, reported by label only", () => {
  const root = workspace();
  const text = `see ${["", "Users", "someone", "x"].join("/")} and box.tail.ts.net, mail a@b.test\n`;
  assert.equal(scan(root, text, "--own", "mine").code, 0);
  const r = scan(root, text, "--own", "mine", "--shapes");
  assert.deepEqual(r.json().hits.map(h => h.term).sort(), ["/Users/", "email", "tailnet host"]);
});

test("scan-repo checks the tracked tree and, with --history, every commit, naming file and commit", () => {
  const root = workspace();
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), "terms-repo-"));
  git(repo, "init", "-q", "-b", "main");
  put(repo, "README.md", "a public toolbox\n");
  put(repo, "notes.md", "built for acme-ds-astro\n");
  git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", "first");
  fs.rmSync(path.join(repo, "notes.md"));
  git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", "drop the client note");
  const tree = run(["scan-repo", repo, "--own", "mine", "--json"], { env: { PROJECTS_ROOT: root } });
  assert.equal(tree.code, 0, tree.out);
  const hist = run(["scan-repo", repo, "--own", "mine", "--history", "--json"], { env: { PROJECTS_ROOT: root } });
  assert.equal(hist.code, 1, hist.out);
  const hits = hist.json().hits;
  assert.deepEqual([...new Set(hits.map(h => h.term))], ["acme-ds-astro"]); // added lines only: the removal is not a second hit
  assert.ok(hits.every(h => h.file === "notes.md" && /^[0-9a-f]{12}$/.test(h.commit)));
});

test("the library call matches the CLI", () => {
  const root = workspace();
  const { load, scanText } = require(P);
  const t = load(root, { own: "mine" });
  assert.deepEqual([...new Set(scanText("thanks Raman", t).map(h => h.term))], ["Raman"]);
});

test("the YAML reader handles flow maps and lists, quotes with commas, and comments", () => {
  const { yaml } = require(P);
  const d = yaml('contacts:\n  ann: {name: "Ann Lee, PhD", handles: {chat: {dm: x}}, topics: [a, "b, c"]}  # note\n  bo:\n    name: Bo Ek # trailing\nlist: [one, two]\n');
  assert.deepEqual(d, { contacts: { ann: { name: "Ann Lee, PhD", handles: { chat: { dm: "x" } }, topics: ["a", "b, c"] }, bo: { name: "Bo Ek" } }, list: ["one", "two"] });
});

test("placeholder host values are not terms", () => {
  const root = workspace();
  fs.appendFileSync(path.join(root, "fleet/machines.yaml"), "  spare:\n    openrig_host: local\n    hostname: localhost\n    ssh_alias: 127.0.0.1\n");
  const terms = run(["terms", "--json"], { env: { PROJECTS_ROOT: root } }).json().terms.map(t => t.term);
  for (const p of ["local", "localhost", "127.0.0.1"]) assert.ok(!terms.includes(p), p);
  assert.ok(terms.includes("spare"));
});

test("a host that equals the own org's name or owner is masked; a longer host that contains it is not", () => {
  const root = workspace();
  fs.appendFileSync(path.join(root, "fleet/machines.yaml"), "  laptop:\n    hostname: mine-dev\n    ssh_alias: mine-dev-laptop\n");
  assert.equal(scan(root, "by mine-dev\n", "--own", "mine").code, 0);
  assert.deepEqual(hitTerms(scan(root, "ssh mine-dev-laptop\n", "--own", "mine")), ["mine-dev-laptop"]);
  assert.deepEqual(hitTerms(scan(root, "by mine-dev\n")), ["mine-dev"]); // without --own it is a name like any other
});

test("a single-word person term matches only in Title case; a full name matches in any case", () => {
  const root = workspace();
  assert.equal(scan(root, "set raman=1 and RAMAN, priya_mode\n", "--own", "mine").code, 0);
  assert.deepEqual(hitTerms(scan(root, "thanks Raman and Priya\n", "--own", "mine")), ["priya", "raman"]);
  assert.deepEqual(hitTerms(scan(root, "PRIYA RAMAN and priya-raman\n", "--own", "mine")), ["priya raman"]);
});

test("--group lists each term once with its count and its first three places", () => {
  const root = workspace();
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), "terms-repo-"));
  git(repo, "init", "-q", "-b", "main");
  put(repo, "a.md", "acme\nacme\nx\nacme\nacme\n");
  git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", "a");
  const r = run(["scan-repo", repo, "--own", "mine", "--group", "--json"], { env: { PROJECTS_ROOT: root } });
  assert.equal(r.code, 1);
  assert.deepEqual(r.json().groups, [{ term: "acme", kind: "org", count: 4, first: ["a.md:1", "a.md:2", "a.md:4"] }]);
});

test("scan-repo reads untracked files too (not ignored ones), and --history scans the working tree as well", () => {
  const root = workspace();
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), "terms-repo-"));
  git(repo, "init", "-q", "-b", "main");
  put(repo, ".gitignore", "build/\n");
  put(repo, "README.md", "public\n");
  git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", "first");
  put(repo, "new.md", "for acme-ds-astro\n");      // untracked, not ignored
  put(repo, "build/out.md", "ledgerline\n");       // ignored
  const tree = run(["scan-repo", repo, "--own", "mine", "--json"], { env: { PROJECTS_ROOT: root } });
  assert.equal(tree.code, 1, tree.out);
  assert.deepEqual(tree.json().hits.map(h => `${h.file}:${h.term}`), ["new.md:acme-ds-astro"]);
  const hist = run(["scan-repo", repo, "--own", "mine", "--history", "--json"], { env: { PROJECTS_ROOT: root } });
  assert.equal(hist.code, 1, hist.out);
  assert.deepEqual(hist.json().hits.map(h => `${h.file}:${h.term}`), ["new.md:acme-ds-astro"]);
});

test("an unknown flag is a usage error, never a silent default", () => {
  const root = workspace();
  for (const a of [["scan-repo", root, "--histroy"], ["scan", "-", "--shaps"], ["terms", "--alow", "x"]])
    assert.equal(run(a, { env: { PROJECTS_ROOT: root }, input: "x\n" }).code, 2, a.join(" "));
});

test("a person word stored in capitals still matches its Title case form", () => {
  const root = workspace();
  fs.writeFileSync(path.join(root, "orgs/acme/contacts.yaml"), "contacts:\n  ines:\n    name: Ines OKAFOR\n  rua:\n    name: Rua McDonald\n");
  assert.deepEqual(hitTerms(scan(root, "thanks Okafor\n", "--own", "mine")), ["okafor"]);             // stored in capitals
  assert.deepEqual(hitTerms(scan(root, "McDonald, Mcdonald\n", "--own", "mine")), ["mcdonald"]);      // as written and canonical
  assert.equal(scan(root, "okafor_mode OKAFOR\n", "--own", "mine").code, 0);
});

test("a source that could not be read is reported, not silently dropped", () => {
  const root = workspace();
  fs.rmSync(path.join(root, ".git"), { recursive: true });
  const t = run(["terms", "--json"], { env: { PROJECTS_ROOT: root } }).json();
  assert.deepEqual(t.warnings, ["git log Host trailers: not read (not a git repository?)"]);
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), "terms-repo-"));
  git(repo, "init", "-q", "-b", "main");
  put(repo, "a.md", "x\n"); put(repo, "b.md", "y\n");
  git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", "a");
  fs.rmSync(path.join(repo, "b.md"));
  fs.mkdirSync(path.join(repo, "b.md"));            // tracked path now unreadable as a file
  const r = run(["scan-repo", repo, "--json"], { env: { PROJECTS_ROOT: root } }).json();
  assert.deepEqual(r.skipped, ["b.md"]);
});
