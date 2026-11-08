// Board tests: node --test skills/openrig-workspace/references/tracking-board/tests/
// Covers what a browser run cannot pin cheaply: the render contract (one data token, escaping, noscript,
// pre-rendered diagrams, render --all), the page's pure helpers, the design tokens (names, both themes, contrast)
// and the unchanged protocol surface. The page itself is checked by hand in a browser (README, "Checking a change").
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const dir = path.resolve(__dirname, "..");
const board = path.join(dir, "board.cjs");
const templateText = fs.readFileSync(path.join(dir, "template.html"), "utf8");
const fixture = JSON.parse(fs.readFileSync(path.join(dir, "fixtures", "board.json"), "utf8"));
const tmps = [];
const tmp = () => { const d = fs.mkdtempSync(path.join(os.tmpdir(), "tb-test-")); tmps.push(d); return d; };
test.after(() => { for (const d of tmps) fs.rmSync(d, { recursive: true, force: true }); });

function run(args, env = {}) {
  const r = spawnSync(process.execPath, [board, ...args], { encoding: "utf8", env: { PATH: process.env.PATH, ...env } });
  return { code: r.status, out: r.stdout, err: r.stderr };
}
function put(root, slug, data) {
  const d = path.join(root, ...slug.split("/"));
  fs.mkdirSync(d, { recursive: true });
  fs.writeFileSync(path.join(d, "board.json"), typeof data === "string" ? data : JSON.stringify(data));
  return d;
}
// The data block of a rendered page, parsed back.
function embedded(html) {
  const m = /<script id="board" type="application\/json">\n([\s\S]*?)\n<\/script>/.exec(html);
  assert.ok(m, "data block present");
  return JSON.parse(m[1]);
}
// A stand-in for pele: records what it was asked and returns small SVGs.
function fakePele(root, body) {
  const d = path.join(root, "node_modules", "pele");
  fs.mkdirSync(d, { recursive: true });
  fs.writeFileSync(path.join(d, "package.json"), JSON.stringify({ name: "pele", main: "index.js" }));
  fs.writeFileSync(path.join(d, "index.js"), body);
  return root;
}

// ---- render contract -------------------------------------------------------------------------------------------

test("template keeps exactly one data token and no network dependency", () => {
  assert.equal(templateText.split("__BOARD_JSON__").length - 1, 1);
  assert.doesNotMatch(templateText, /<script[^>]+\ssrc=/i, "no external script");
  assert.doesNotMatch(templateText, /cdn\.|jsdelivr|unpkg|googleapis/i, "no CDN host");
  assert.doesNotMatch(templateText, /<link[^>]+rel=["']stylesheet/i, "no external stylesheet");
});

test("template keeps the feedback and live-event protocol", () => {
  assert.match(templateText, /fetch\("feedback", \{ method: "POST"/);
  assert.match(templateText, /new EventSource\("events"\)/);
  for (const ev of ["hello", "status", "reply", "reload"]) assert.match(templateText, new RegExp(`addEventListener\\("${ev}"`));
  assert.match(templateText, /r\.status !== 202/);
});

test("render embeds board.json plus rendered diagrams, escapes markup, fills the noscript summary", () => {
  const root = tmp();
  const evil = { ...fixture, title: "Title </script><img src=x onerror=alert(1)> <!-- x", headline: "a & b <b>bold</b>" };
  const d = put(root, "demo/audit/evil", evil);
  const r = run(["render", d], { OPENRIG_BOARDS_ROOT: root, PELE_DIR: path.join(root, "none") });
  assert.equal(r.code, 0, r.err);
  const html = fs.readFileSync(path.join(d, "index.html"), "utf8");
  assert.equal(html.includes("__BOARD_JSON__"), false);
  const data = embedded(html);
  assert.equal(data.title, evil.title, "text round-trips exactly");
  assert.deepEqual(data.missions, evil.missions);
  assert.deepEqual(data.rendered, { diagrams: {} }, "no pele: nothing pre-rendered");
  const block = html.slice(html.indexOf('<script id="board"'), html.indexOf("</script>", html.indexOf('<script id="board"')));
  assert.doesNotMatch(block, /<(?!script)/, "no raw < inside the data block");
  const ns = /<noscript id="summary">([\s\S]*?)<\/noscript>/.exec(html)[1];
  assert.match(ns, /Needs you/);
  assert.match(ns, /Approve the retry-budget/);
  assert.doesNotMatch(ns, /<img|<b>bold/, "summary is escaped");
  assert.match(r.err, /pele not installed/);
});

test("render without a fixture-like board still works (init output)", () => {
  const root = tmp();
  const r = run(["init", "demo/audit/new", "--title", "New one"], { OPENRIG_BOARDS_ROOT: root, OPENRIG_BOARDS_URL: "https://x.test/boards" });
  assert.equal(r.code, 0, r.err);
  const html = fs.readFileSync(path.join(root, "demo/audit/new/index.html"), "utf8");
  assert.equal(embedded(html).title, "New one");
  assert.match(html, /<noscript id="summary">[\s\S]*Nothing is waiting on you/);
  assert.equal(run(["init", "demo/audit/new"], { OPENRIG_BOARDS_ROOT: root }).code, 2, "init refuses to overwrite");
});

test("diagrams are drawn at render time: ids prefixed, a top-down variant for LR, unsafe markup refused", () => {
  const root = tmp();
  const pele = fakePele(path.join(root, "pele"), `
    exports.render = src => {
      if (src.includes("EVIL")) return { svg: '<svg><script>alert(1)</script></svg>' };
      if (src.includes("BROKEN")) throw new Error("parse error line 2\\nmore");
      const dir = /^(?:flowchart|graph)\\s+(\\w+)/.exec(src.trim());
      return { svg: '<svg class="pele" viewBox="0 0 10 10"><defs><marker id="ah"/></defs><a href="javascript:x"><path marker-end="url(#ah)"/></a><a href="https://ok.test/"><g>' + (dir ? dir[1] : "seq") + '</g></a></svg>' };
    };`);
  const d = put(root, "demo/audit/dg", {
    ...fixture,
    diagrams: { flow: "flowchart LR\n A-->B", seq: "sequenceDiagram\n A->>B: hi", bad: "BROKEN", evil: "EVIL" },
  });
  const r = run(["render", d], { OPENRIG_BOARDS_ROOT: root, PELE_DIR: pele });
  assert.equal(r.code, 0, r.err);
  const dg = embedded(fs.readFileSync(path.join(d, "index.html"), "utf8")).rendered.diagrams;
  assert.match(dg.flow.svg, /<g>LR<\/g>/);
  assert.match(dg.flow.tall, /<g>TB<\/g>/, "LR flowcharts also get a top-down drawing");
  assert.equal(dg.seq.tall, undefined);
  assert.match(dg.flow.svg, /id="d0w-ah"/);
  assert.match(dg.flow.tall, /id="d0t-ah"/);
  assert.match(dg.seq.svg, /id="d1w-ah"/);
  assert.match(dg.flow.svg, /url\(#d0w-ah\)/);
  assert.doesNotMatch(dg.flow.svg, /javascript:/, "script URLs are dropped");
  assert.match(dg.flow.svg, /href="https:\/\/ok\.test\/"/, "safe links stay");
  assert.equal(dg.bad, undefined);
  assert.equal(dg.evil, undefined);
  assert.match(r.err, /bad: parse error line 2/);
  assert.match(r.err, /evil: diagram markup was refused/);
});

test("render --all re-renders every board, skips the token file, reports a bad board and exits 1", () => {
  const root = tmp();
  const a = put(root, "demo/audit/one", fixture), b = put(root, "demo/portal/two", { ...fixture, title: "Two" });
  put(root, "demo/aaa/nokey", { missions: [], decisions: [] }); // a required key missing, first in directory order
  put(root, "demo/portal/bad", "{ not json");
  fs.writeFileSync(path.join(root, ".board-token"), "secret");
  fs.mkdirSync(path.join(root, "demo", "audit", "one", "feedback"), { recursive: true });
  const env = { OPENRIG_BOARDS_ROOT: root, PELE_DIR: path.join(root, "none") };
  const r = run(["render", "--all"], env);
  assert.equal(r.code, 1);
  assert.match(r.out, /2 of 4 board\(s\) rendered/, "a bad board does not stop the ones after it");
  assert.match(r.err, /demo\/portal\/bad/);
  assert.match(r.err, /demo\/aaa\/nokey: .*has no "title"/);
  assert.equal(embedded(fs.readFileSync(path.join(a, "index.html"), "utf8")).title, fixture.title);
  assert.equal(embedded(fs.readFileSync(path.join(b, "index.html"), "utf8")).title, "Two");
  const l = run(["list"], env);
  assert.equal(l.code, 1, "list reports the unreadable board instead of hiding it");
  fs.rmSync(path.join(root, "demo", "portal", "bad"), { recursive: true }); fs.rmSync(path.join(root, "demo", "aaa"), { recursive: true });
  const ok = run(["render", "--all"], env);
  assert.equal(ok.code, 0);
  assert.match(ok.out, /2 of 2 board\(s\) rendered/);
  const list = run(["list"], env);
  assert.equal(list.code, 0, list.err);
  assert.equal(list.out.trim().split("\n").length, 2);
});

test("render of one bad board says why and exits 2 without a stack trace", () => {
  const root = tmp();
  const d = put(root, "demo/audit/nokey", { missions: [] });
  const r = run(["render", d], { OPENRIG_BOARDS_ROOT: root });
  assert.equal(r.code, 2);
  assert.match(r.err, /^board: .*has no "title"/);
  assert.doesNotMatch(r.err, /\n\s+at /);
});

test("render --all on an empty root renders nothing and succeeds", () => {
  const r = run(["render", "--all"], { OPENRIG_BOARDS_ROOT: path.join(tmp(), "missing") });
  assert.equal(r.code, 0);
  assert.match(r.out, /0 of 0/);
});

test("check keeps its diagram lint and roles", () => {
  const root = tmp();
  const env = { OPENRIG_BOARDS_ROOT: root, PELE_DIR: path.join(root, "none") };
  put(root, "demo/audit/good", fixture);
  const good = run(["check", "demo/audit/good"], env);
  assert.equal(good.code, 0, good.out);
  assert.match(good.out, /check: ok/);
  put(root, "demo/audit/lint", { ...fixture, diagrams: { flow: "flowchart LR\n A[\"x\"]:::nonsense\n style A fill:#fff" } });
  const bad = run(["check", "demo/audit/lint"], env);
  assert.equal(bad.code, 1);
  assert.match(bad.out, /unknown role nonsense/);
  assert.match(bad.out, /sets colors/);
  put(root, "demo/audit/click", { ...fixture, diagrams: { flow: "flowchart LR\n A-->B\n click A \"https://x.example.test\"" } });
  const click = run(["check", "demo/audit/click"], env);
  assert.equal(click.code, 1);
  assert.match(click.out, /flow: click/);
});

// A chart as the statechart skill writes it (upstream corpus CounterDeadlock, cursor/plugins pstack/skills/statechart,
// MIT), plus phase colors from its view module: groups are color classes, broken states have a classDef.
const STATECHART = `stateDiagram-v2
  state "Legend" as legend {
    lg0: Intake
    lg1: Delivery
    lg2: Breaks NoDeadlock or NotThree
    lg3: Path to the NoDeadlock or NotThree bug
  }
  class lg0 blue
  class lg1 teal
  class lg2 breaks
  class lg3 bugPath
  s0: 0
  s1: 1
  s2: 3
  s3: 2
  [*] --> s0
  s0 --> s1: Inc
  s0 --> s2: Jump
  s1 --> s3: Inc
  s3 --> s2: Inc
  classDef breaks fill:#ffecee,stroke:#e72e3b,stroke-width:2.5px,color:#cd2834
  classDef mayBreak fill:#fff3e6,stroke:#e8730c,stroke-width:2.5px,color:#b85a06
  class s0 blue
  class s0 bugPath
  class s1 bugPath
  class s2 breaks
  class s2 bugPath
  class s3 teal
  class s3 mayBreak
  class s3 repeats`;

test("a statechart passes check: phase colors map to roles, breaks and mayBreak to risk, and it can sit on a slice", () => {
  const root = tmp();
  const env = { OPENRIG_BOARDS_ROOT: root, PELE_DIR: path.join(root, "none") };
  const missions = structuredClone(fixture.missions);
  missions[0].slices[0].diagram = "chart";
  put(root, "demo/audit/sc", { ...fixture, missions, diagrams: { ...fixture.diagrams, chart: STATECHART } });
  const r = run(["check", "demo/audit/sc"], env);
  assert.equal(r.code, 0, r.out);
  put(root, "demo/audit/sc2", { ...fixture, diagrams: { ...fixture.diagrams, chart: `${STATECHART}\n  classDef extra fill:#000` } });
  const bad = run(["check", "demo/audit/sc2"], env);
  assert.equal(bad.code, 1, "only the statechart's own breaks and mayBreak classDefs are dropped");
  assert.match(bad.out, /chart: sets colors/);
  assert.match(bad.out, /chart: not placed/);
  const ghost = structuredClone(fixture.missions);
  ghost[0].slices[0].diagram = "nope";
  put(root, "demo/audit/sc3", { ...fixture, missions: ghost });
  const missing = run(["check", "demo/audit/sc3"], env);
  assert.equal(missing.code, 1, "a slice naming a missing diagram fails check");
  assert.match(missing.out, new RegExp(`slice ${ghost[0].slices[0].id.replace(".", "\\.")} names unknown diagram nope`));
});

test("render draws a statechart in the role palette: no inline colors reach pele", () => {
  const root = tmp();
  const seen = path.join(root, "seen.txt");
  const pele = fakePele(path.join(root, "pele"), `
    exports.render = src => { require("fs").appendFileSync(${JSON.stringify(seen)}, src + "\\n---\\n"); return { svg: '<svg class="pele"></svg>' }; };`);
  const d = put(root, "demo/audit/sc", { ...fixture, diagrams: { chart: STATECHART, flow: "flowchart LR\n A:::ours-->B" } });
  const r = run(["render", d], { OPENRIG_BOARDS_ROOT: root, PELE_DIR: pele });
  assert.equal(r.code, 0, r.err);
  const src = fs.readFileSync(seen, "utf8").split("\n---\n")[0];
  assert.doesNotMatch(src, /classDef|fill:/);
  for (const line of ["class s0 ours", "class s0 bugPath", "class s2 risk", "class s3 done", "class s3 risk", "class s3 repeats", "class lg0 ours", "class lg2 risk"])
    assert.match(src, new RegExp(`^\\s*${line}$`, "m"), line);
  assert.equal(embedded(fs.readFileSync(path.join(d, "index.html"), "utf8")).diagrams.chart, STATECHART, "board.json keeps the chart as written");
});

// ---- the page's pure helpers --------------------------------------------------------------------------------------

const helperSrc = /\/\* tb:helpers:start[^\n]*\n([\s\S]*?)\/\* tb:helpers:end \*\//.exec(templateText)[1];
const H = new Function(`${helperSrc}\nreturn { esc, safeHref, parseWhen, relTime, prLabel, pillClass, sliceSig, decSig, diffBoard, snapshot, idOf, orderMissions, STATUSES };`)();

test("esc escapes the five HTML characters", () => {
  assert.equal(H.esc(`<a href="x" onclick='y'>&</a>`), "&lt;a href=&quot;x&quot; onclick=&#39;y&#39;&gt;&amp;&lt;/a&gt;");
  assert.equal(H.esc(null), "");
  assert.equal(H.esc(0), "0");
});

test("safeHref allows http(s), mailto, anchors and relative paths, and nothing else", () => {
  for (const ok of ["https://example.test/a?b=1#c", "http://example.test", "mailto:a@example.test", "#dec-Q1", "#M2.4", "report.html", "../x/y.html", "/boards/a/b/"]) assert.equal(H.safeHref(ok), ok, ok);
  for (const bad of ["javascript:alert(1)", " JavaScript:alert(1)", "java\nscript:alert(1)", "java\tscript:alert(1)", "data:text/html;base64,AA", "vbscript:x", "file:///etc/passwd", "//evil.test/x", "/\\evil.test", "\u0001javascript:x", "ftp://example.test", "", "   ", null, undefined])
    assert.equal(H.safeHref(bad), "", JSON.stringify(bad));
});

test("parseWhen reads the board's time formats and relTime words them", () => {
  const t = H.parseWhen("2026-11-08 10:30");
  assert.equal(new Date(t).getHours(), 10);
  assert.equal(new Date(t).getMinutes(), 30);
  assert.equal(H.parseWhen("2026-11-08T10:30:00Z"), Date.parse("2026-11-08T10:30:00Z"));
  assert.equal(H.parseWhen("2026-11-08"), new Date(2026, 10, 8).getTime());
  assert.ok(Number.isNaN(H.parseWhen("yesterday")));
  assert.ok(Number.isNaN(H.parseWhen("")));
  const m = 60000, h = 60 * m, d = 24 * h;
  assert.equal(H.relTime(10 * 1000), "just now");
  assert.equal(H.relTime(-5 * m), "just now", "a clock slightly behind never shows the future");
  assert.equal(H.relTime(5 * m), "5 min ago");
  assert.equal(H.relTime(2 * h), "2 h ago");
  assert.equal(H.relTime(30 * h), "yesterday");
  assert.equal(H.relTime(4 * d), "4 days ago");
  assert.equal(H.relTime(21 * d), "3 weeks ago");
  assert.equal(H.relTime(120 * d), "4 months ago");
});

test("prLabel names the pull request number and falls back to PR", () => {
  assert.equal(H.prLabel("https://git.example.test/o/r/pull/101"), "PR #101");
  assert.equal(H.prLabel("https://git.example.test/o/r/merge_requests/7/"), "PR #7");
  assert.equal(H.prLabel("owner/repo#55"), "PR #55");
  assert.equal(H.prLabel("https://example.test/anything"), "PR");
  assert.equal(H.prLabel(undefined), "PR");
});

test("status pills: known statuses keep their class, unknown ones are shown as planned", () => {
  for (const s of ["done", "doing", "planned", "blocked", "decide", "accepted"]) assert.equal(H.pillClass(s), s);
  assert.equal(H.pillClass("weird"), "planned");
  assert.equal(H.pillClass(undefined), "planned");
});

test("changed-since: new or different slices and decisions and new log rows are found", () => {
  const before = H.snapshot(fixture);
  assert.deepEqual(H.diffBoard(before, H.snapshot(fixture)), { slices: [], decisions: [], log: [] });
  assert.deepEqual(H.diffBoard(null, H.snapshot(fixture)), { slices: [], decisions: [], log: [] }, "first visit marks nothing");
  const next = JSON.parse(JSON.stringify(fixture));
  next.missions[1].slices[2].progress = 80;
  next.missions[1].slices.push({ id: "M1.9", name: "New", owner: "x", status: "planned", progress: 0, note: "" });
  next.decisions.find(x => x.id === "Q1").status = "accepted";
  next.log.unshift(["2026-11-09 09:00", "Something new", "e"]);
  const diff = H.diffBoard(before, H.snapshot(next));
  assert.deepEqual(diff.slices.sort(), ["M1.3", "M1.9"]);
  assert.deepEqual(diff.decisions, ["Q1"]);
  assert.equal(diff.log.length, 1);
});

test("orderMissions lists open missions first and finished ones after, keeping board order in each group", () => {
  const ms = [{ id: "A", status: "done" }, { id: "B", status: "doing" }, { id: "C", status: "done" }, { id: "D", status: "blocked" }, { id: "E", status: "planned" }];
  assert.deepEqual(H.orderMissions(ms).map(m => m.id), ["B", "D", "E", "A", "C"]);
  assert.deepEqual(H.orderMissions([]), []);
});

test("section placement keeps the old default: no place is before the missions", () => {
  assert.match(templateText, /before = sections\.filter\(s => s\.place !== "after" && s\.place !== "bottom"\)/);
  assert.match(templateText, /lead \+ sect\(before\) \+ toolbar \+ missionsBlock \+ sect\(upper\)/);
  assert.ok(fixture.sections.some(s => s.place === "after"), "the fixture uses the opt-in value");
});

test("mission anchors are keyed on the mission id and the old #mission-N form is kept as an alias", () => {
  assert.match(templateText, /idOf\(`m-\$\{m\.id\}`, used\)/);
  assert.match(templateText, /\^mission-\(\\d\+\)\$/);
  assert.doesNotMatch(templateText, /id="mission-\$\{i\}"/);
});

test("idOf makes unique DOM ids from any text", () => {
  const used = new Set(["needs"]);
  assert.equal(H.idOf("M2.4", used), "M2.4");
  assert.equal(H.idOf("M2.4", used), "M2.4-2");
  assert.equal(H.idOf("needs", used), "needs-2");
  assert.equal(H.idOf("a b<c>", used), "a_b_c_");
  assert.equal(H.idOf("", used), "x");
});

// ---- design tokens --------------------------------------------------------------------------------------------------

function tokenBlocks() {
  const css = /<style>([\s\S]*?)<\/style>/.exec(templateText)[1];
  const grab = re => { const m = re.exec(css); assert.ok(m, String(re)); return Object.fromEntries([...m[1].matchAll(/(--[\w-]+):\s*([^;]+);/g)].map(x => [x[1], x[2].trim()])); };
  const light = grab(/\n  :root \{([\s\S]*?)\n  \}/);
  const dark = grab(/:root\[data-theme="dark"\] \{([\s\S]*?)\n  \}/);
  const media = grab(/:root:not\(\[data-theme="light"\]\) \{([\s\S]*?)\n    \}/);
  return { light, dark: { ...light, ...dark }, darkOnly: dark, media };
}
const rgb = hex => { const h = hex.replace("#", ""); return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16)); };
const lum = c => { const [r, g, b] = c.map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
const mix = (a, b, pct) => a.map((v, i) => Math.round(v * pct + b[i] * (1 - pct)));

test("the token names the board index page copies are all present", () => {
  const { light } = tokenBlocks();
  const need = ["font", "mono", "fs-xs", "fs-sm", "fs-md", "fs-lg", "fs-xl", "fs-2xl", "fs-3xl", "lh-tight", "lh-body", "sp-1", "sp-2", "sp-3", "sp-4", "sp-5", "sp-6", "sp-7",
    "r-sm", "r-md", "r-lg", "r-pill", "tap", "bar-h", "rail-w", "sheet-w", "bg", "surface", "surface-2", "line", "line-strong", "text", "muted", "accent", "accent-ink", "accent-soft",
    "focus", "scrim", "shadow", "shadow-up", "new", "ok", "ok-soft", "ok-bar", "doing", "doing-soft", "blocked", "blocked-soft", "decide", "decide-soft", "planned", "planned-soft"];
  for (const n of [...need, "fs-meta"]) assert.ok(`--tb-${n}` in light, `--tb-${n}`);
  for (const r of ["ours", "provider", "person", "store", "legacy", "risk", "done"]) for (const k of ["fill", "line"]) assert.ok(`--role-${r}-${k}` in light, `--role-${r}-${k}`);
  assert.equal(light["--tb-tap"], "44px");
  assert.equal(light["--tb-fs-md"], "15px");
  assert.equal(light["--tb-fs-xs"], "12px");
});

test("both dark blocks (manual and system) define the same values and cover every themed token", () => {
  const { light, darkOnly, media } = tokenBlocks();
  assert.deepEqual(media, darkOnly);
  for (const k of Object.keys(darkOnly)) assert.ok(k in light, k);
  const themed = Object.keys(light).filter(k => /^--(tb-(bg|surface|surface-2|line|line-strong|text|muted|accent|accent-ink|accent-soft|focus|scrim|shadow|shadow-up|new|ok|ok-soft|ok-bar|doing|doing-soft|blocked|blocked-soft|decide|decide-soft|planned|planned-soft)|role-.*)$/.test(k));
  for (const k of themed) assert.ok(k in darkOnly, `dark value for ${k}`);
});

test("text and control contrast meets WCAG AA in light and dark", () => {
  const { light, dark } = tokenBlocks();
  for (const [name, t] of [["light", light], ["dark", dark]]) {
    const c = k => rgb(t[`--tb-${k}`]);
    const text = [
      ["text/bg", "text", "bg"], ["text/surface", "text", "surface"], ["muted/bg", "muted", "bg"], ["muted/surface", "muted", "surface"], ["muted/surface-2", "muted", "surface-2"],
      ["accent/surface", "accent", "surface"], ["accent/accent-soft", "accent", "accent-soft"], ["accent-ink/accent", "accent-ink", "accent"], ["new/surface", "new", "surface"], ["new/bg", "new", "bg"],
      ["ok/ok-soft", "ok", "ok-soft"], ["doing/doing-soft", "doing", "doing-soft"], ["blocked/blocked-soft", "blocked", "blocked-soft"], ["decide/decide-soft", "decide", "decide-soft"],
      ["planned/planned-soft (also the disabled button)", "planned", "planned-soft"], ["blocked/surface", "blocked", "surface"], ["decide/surface", "decide", "surface"], ["ok/surface", "ok", "surface"],
    ];
    for (const [label, fg, bg] of text) assert.ok(ratio(c(fg), c(bg)) >= 4.5, `${name} ${label} ${ratio(c(fg), c(bg)).toFixed(2)}`);
    // The Needs-you card and the blocked/decide stat tiles sit on a tint of their soft colour.
    const needsBg = mix(c("decide-soft"), c("surface"), 0.55);
    for (const fg of ["text", "decide", "muted"]) assert.ok(ratio(c(fg), needsBg) >= 4.5, `${name} ${fg} on the needs card ${ratio(c(fg), needsBg).toFixed(2)}`);
    const clearBg = mix(c("ok-soft"), c("surface"), 0.55);
    assert.ok(ratio(c("text"), clearBg) >= 4.5, `${name} text on the clear needs card`);
    // Non-text: control borders, focus ring and the decide dot on the card they sit on.
    for (const bg of ["bg", "surface"]) { assert.ok(ratio(c("line-strong"), c(bg)) >= 3, `${name} line-strong/${bg}`); assert.ok(ratio(c("focus"), c(bg)) >= 3, `${name} focus/${bg}`); }
    assert.ok(ratio(c("ok-bar"), c("surface")) >= 3, `${name} progress fill`);
    for (const r of ["ours", "provider", "person", "store", "legacy", "risk", "done"]) assert.ok(ratio(rgb(t[`--role-${r}-line`]), rgb(t[`--role-${r}-fill`])) >= 3, `${name} role ${r} outline`);
    assert.ok(ratio(c("text"), c("accent")) >= 1, "sanity");
  }
});

test("sizes: tap targets, input font and minimum text size are in the stylesheet", () => {
  const css = /<style>([\s\S]*?)<\/style>/.exec(templateText)[1];
  assert.match(css, /\.search input \{[^}]*font-size: 16px/, "16px inputs so iOS does not zoom");
  assert.match(css, /\.composer textarea \{[^}]*font-size: 16px/);
  assert.match(css, /\.chip \{[^}]*min-height: var\(--tb-tap\)/);
  assert.match(css, /@media \(prefers-reduced-motion: no-preference\)/);
  assert.match(css, /:focus-visible \{ outline: 3px solid var\(--tb-focus\)/);
  assert.match(css, /env\(safe-area-inset-bottom\)/);
  assert.match(css, /@media print/);
  assert.match(css, /forced-colors/);
  const px = [...css.matchAll(/font-size:\s*(\d+(?:\.\d+)?)px/g)].map(m => +m[1]);
  assert.ok(px.every(v => v >= 12), `no literal font-size under 12px: ${px.filter(v => v < 12)}`);
  assert.match(templateText, /<noscript id="summary">/);
  assert.match(templateText, /<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">/);
});

// ---- fixtures --------------------------------------------------------------------------------------------------------

test("the fixture is a synthetic board that covers every state the page draws", () => {
  assert.ok(fixture.missions.length >= 3);
  assert.ok(fixture.missions.some(m => m.status === "done"), "a done mission, so the collapse shows");
  for (const s of ["planned", "doing", "blocked", "done", "decide"]) assert.ok(fixture.missions.some(m => m.slices.some(x => x.status === s)), s);
  assert.equal(fixture.decisions.length, 6);
  assert.ok(fixture.decisions.some(d => d.status === "accepted") && fixture.decisions.some(d => d.status === "decide"));
  assert.ok(fixture.needs.some(n => typeof n === "object" && n.href) && fixture.log.length && fixture.facts.length && fixture.links.length);
  assert.ok(Object.keys(fixture.diagrams).length >= 2);
  assert.ok(fixture.missions.some(m => m.slices.some(x => x.diagram && /^stateDiagram/.test(fixture.diagrams[x.diagram]))), "a slice shows a statechart");
  const text = JSON.stringify(fixture);
  assert.doesNotMatch(text, /@(?!demo-rig)\w+\.\w+/, "no real mail or seat domains");
  assert.doesNotMatch(text, /https?:\/\/(?!\w+\.example\.test)/, "only example.test URLs");
  const empty = JSON.parse(fs.readFileSync(path.join(dir, "fixtures", "empty.json"), "utf8"));
  assert.deepEqual([empty.missions, empty.decisions, empty.needs, empty.log], [[], [], [], []]);
});

// ---- server sign-in ----------------------------------------------------------------------------------------------

// Start server.cjs on a scratch root with one synthetic board; owners (if given) is the .board-owners text.
async function server(owners, mode = 0o600) {
  const root = tmp();
  put(root, "demo/audit/sample", { title: "Sample", org: "demo", project: "audit", slug: "sample" });
  if (owners !== undefined) fs.writeFileSync(path.join(root, ".board-owners"), owners, { mode });
  if (owners !== undefined) fs.chmodSync(path.join(root, ".board-owners"), mode);
  const port = 47900 + Math.floor(Math.random() * 900);
  const child = require("node:child_process").spawn(process.execPath, [path.join(dir, "server.cjs")], { env: { PATH: process.env.PATH, OPENRIG_BOARDS_ROOT: root, OPENRIG_BOARDS_PORT: String(port) }, stdio: ["ignore", "pipe", "inherit"] });
  await new Promise(ok => child.stdout.once("data", ok));
  const base = `http://127.0.0.1:${port}/demo/audit/sample`;
  const post = headers => fetch(`${base}/feedback`, { method: "POST", headers: { "content-type": "application/json", ...headers }, body: JSON.stringify({ notes: [{ id: "n1", kind: "change", anchor: "M1", text: "x" }] }) });
  const hello = async headers => {
    const ac = new AbortController(); const r = await fetch(`${base}/events`, { headers, signal: ac.signal });
    const reader = r.body.getReader(); let text = "";
    while (!/\n\n/.test(text)) text += new TextDecoder().decode((await reader.read()).value);
    ac.abort(); return JSON.parse(/data: (.*)/.exec(text)[1]);
  };
  const token = fs.readFileSync(path.join(root, ".board-token"), "utf8").trim();
  return { root, post, hello, token, stop: () => child.kill() };
}

test("sign-in: an allowlisted Tailscale login sends feedback, and hello names the person", async () => {
  const s = await server("# owners\nowner@example.com\n");
  try {
    const r = await s.post({ "tailscale-user-login": "Owner@Example.com", "tailscale-user-name": "Sample Owner" });
    assert.equal(r.status, 202);
    assert.equal(fs.readdirSync(path.join(s.root, "demo/audit/sample/feedback/inbox")).length, 1);
    assert.deepEqual(await s.hello({ "tailscale-user-login": "owner@example.com", "tailscale-user-name": "Sample Owner" }), { auth: true, who: "Sample Owner" });
  } finally { s.stop(); }
});

test("sign-in: refused for an unlisted login, for no header and no cookie, and for a header with an empty or missing list", async () => {
  for (const owners of ["owner@example.com\n", "", undefined]) {
    const s = await server(owners);
    try {
      if (owners) assert.equal((await s.post({ "tailscale-user-login": "other@example.com" })).status, 401);
      else assert.equal((await s.post({ "tailscale-user-login": "owner@example.com" })).status, 401, `owners ${JSON.stringify(owners)}`);
      assert.equal((await s.post({})).status, 401);
      assert.deepEqual(await s.hello({ "tailscale-user-login": "other@example.com" }), { auth: false });
    } finally { s.stop(); }
  }
});

test("sign-in: an allowlist others can read or write is ignored, and the token cookie still works", async () => {
  const s = await server("owner@example.com\n", 0o644);
  try {
    assert.equal((await s.post({ "tailscale-user-login": "owner@example.com" })).status, 401);
    assert.equal((await s.post({ cookie: `board_k=${s.token}` })).status, 202);
    assert.deepEqual(await s.hello({ cookie: `board_k=${s.token}` }), { auth: true });
  } finally { s.stop(); }
});
