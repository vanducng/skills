#!/usr/bin/env node
// Operator-side Grok Bot messaging from a shell: list bots, send, wait for the reply, read the chat.
// Built on grok-bot-sdk, which uses the desktop app's own signed-in session. Prints JSON, never the token.
//
//   node grok-bot.mjs bots
//   node grok-bot.mjs send <bot> <text>          [--message-id <id>]
//   node grok-bot.mjs wait <bot> --after <seq>   [--message-id <id>] [--timeout <s>] [--interval <s>]
//   node grok-bot.mjs ask  <bot> <text>          [--timeout <s>] [--interval <s>]   (send, then wait)
//   node grok-bot.mjs read <bot>                 [--limit <n>] [--since <iso>] [--jsonl]
//   node grok-bot.mjs install <bot>              [--apply]   (sync the skill's bot-side assets/*.md to the bot)
//
// Every send carries a messageId (one is made when none is given): the app accepts a send without one but never
// shows it in the chat. The SDK is loaded from GROK_BOT_SDK_DIR (default ~/.cache/grok-bot-sdk), where it is
// installed with `npm install --prefix <dir> github:RongleCat/grok-bot-sdk#<commit>`.
import { randomUUID } from "node:crypto";
import { readdirSync, readFileSync, realpathSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const USAGE = "usage: grok-bot.mjs bots | send <bot> <text> | wait <bot> --after <seq> | ask <bot> <text> | read <bot> | install <bot> [--apply]";
const ASSETS = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "assets");
const DEFAULTS = { timeout: 300, interval: 12, limit: 10 };
const BOOLEAN_FLAGS = new Set(["jsonl", "apply"]);

/** Seconds from `300`, `30s`, `5m` or `1h`; null for anything else. */
export function seconds(value) {
  const m = /^(\d+(?:\.\d+)?)([smh]?)$/.exec(String(value));
  return m ? Number(m[1]) * { "": 1, s: 1, m: 60, h: 3600 }[m[2]] : null;
}

export function parseArgs(argv) {
  const [cmd, ...rest] = argv;
  const flags = {};
  const words = [];
  for (let i = 0; i < rest.length; i++) {
    const name = rest[i].slice(2);
    if (!rest[i].startsWith("--")) words.push(rest[i]);
    else flags[name] = BOOLEAN_FLAGS.has(name) ? true : rest[++i];
  }
  return { cmd, bot: words[0], text: words.slice(1).join(" "), flags };
}

/** The SDK from an npm prefix (dir/node_modules/grok-bot-sdk) or from the package directory itself. */
async function loadSdk(dir) {
  // The package exports only an `import` condition, so require.resolve cannot find it: read its exports map instead.
  const pkgDir = [dir, path.join(dir, "node_modules", "grok-bot-sdk")].find((d) => {
    try {
      return JSON.parse(readFileSync(path.join(d, "package.json"), "utf8")).name === "grok-bot-sdk";
    } catch {
      return false;
    }
  });
  if (!pkgDir) throw Object.assign(new Error(`grok-bot-sdk is not installed in ${dir}`), { code: "NO_SDK" });
  const { exports } = JSON.parse(readFileSync(path.join(pkgDir, "package.json"), "utf8"));
  const files = [exports["."].import, exports["./desktop"].import].map((f) => path.join(pkgDir, f));
  const [sdk, desktop] = await Promise.all(files.map((f) => import(pathToFileURL(f).href)));
  return { GrokBotClient: sdk.GrokBotClient, desktopCredentials: desktop.desktopCredentials, version: desktop.version };
}

/** Replaces every credential string in `text`, raw or JSON-escaped (a quote or backslash in it is escaped once the
 *  output is serialised), so no output or error message can carry the token. */
export function redactor(creds) {
  const raw = Object.values(creds).filter((v) => typeof v === "string" && v.length >= 8);
  const secrets = [...new Set([...raw, ...raw.map((v) => JSON.stringify(v).slice(1, -1))])].sort((a, b) => b.length - a.length);
  return (text) => secrets.reduce((t, s) => t.split(s).join("[redacted]"), String(text));
}

const seqOf = (entry) => BigInt(entry?.seq ?? 0);
const lastSeq = (entries) => entries.reduce((max, e) => (seqOf(e) > max ? seqOf(e) : max), 0n);

/** One transcript entry as {seq, ts, from, text}: `from` is "bot" or "operator" (the person's own sends have a
 *  different body from the bot's messages). */
export function line(entry) {
  const b = entry.body || {};
  const raw = entry.entryKind === "message" ? b.content : b.message;
  const text = typeof raw === "string" ? raw : JSON.stringify(raw ?? "");
  const from = entry.entryKind === "message" && b.role !== "user" ? "bot" : "operator";
  const ts = b.timestampMs ? new Date(Number(b.timestampMs)).toISOString() : null;
  return { seq: String(entry.seq), ts, from, text, streaming: Boolean(b.isStreaming) };
}

const isReply = (entry, after) =>
  seqOf(entry) > after && entry.entryKind === "message" && (entry.body || {}).role !== "user" && !(entry.body || {}).isStreaming;

async function findBot(client, name) {
  const { bots } = await client.listBots();
  const bot = bots.find((b) => b.name === name) ?? bots.find((b) => b.name.toLowerCase() === String(name).toLowerCase());
  if (!bot) throw Object.assign(new Error(`no bot named ${name}; known: ${bots.map((b) => b.name).join(", ")}`), { code: "NO_BOT" });
  return bot;
}

async function send(client, bot, text, messageId) {
  if (!text) throw Object.assign(new Error("nothing to send"), { code: "USAGE" });
  const { entries } = await client.listTranscript({ botId: bot.id, limit: 1 });
  const id = messageId || randomUUID();
  const sent = await client.sendMessage({ botId: bot.id, messageId: id, text });
  return { bot: bot.name, messageId: id, after: String(lastSeq(entries)), delivery: sent.delivery, dispatched: sent.dispatched };
}

async function wait(client, bot, after, messageId, { timeout, interval, sleep }) {
  const deadline = Date.now() + timeout * 1000;
  for (;;) {
    if (messageId) {
      const status = await client.getSendStatus({ botId: bot.id, messageId }).catch(() => null);
      if (status?.rejectionCode) throw Object.assign(new Error(`the app rejected the send: ${status.rejectionCode}`), { code: "REJECTED" });
    }
    const { entries } = await client.listTranscript({ botId: bot.id, limit: 20 });
    const reply = entries.find((e) => isReply(e, BigInt(after)));
    if (reply) return { bot: bot.name, reply: line(reply) };
    if (Date.now() >= deadline) throw Object.assign(new Error(`no reply within ${timeout}s`), { code: "TIMEOUT" });
    await sleep(interval * 1000);
  }
}

/** The bot-side library skills: every assets/*.md with a `name:` and `description:` in its frontmatter. */
export function botAssets(dir = ASSETS) {
  return readdirSync(dir)
    .filter((f) => f.endsWith(".md"))
    .sort()
    .map((f) => {
      const content = readFileSync(path.join(dir, f), "utf8");
      const front = content.match(/^---\n([\s\S]*?)\n---\n/)?.[1] ?? "";
      const field = (k) => front.match(new RegExp(`^${k}:\\s*(.+)$`, "m"))?.[1].trim().replace(/^"(.*)"$/, "$1");
      return { file: f, name: field("name"), description: field("description"), content };
    })
    .filter((a) => a.name && a.description);
}

/** Adds each asset the bot lacks and updates each one whose text differs; never removes a skill. Dry run unless apply. */
async function install(client, bot, apply) {
  const { skills } = await client.listAgentSkills(bot.id);
  const plan = botAssets().map((a) => {
    const have = skills.find((k) => k.name === a.name);
    const same = have && [a.content, a.content.replace(/^---\n[\s\S]*?\n---\n+/, "")].includes(have.body);
    return { ...a, action: !have ? "add" : same ? "unchanged" : "update" };
  });
  for (const a of plan.filter((p) => apply && p.action !== "unchanged")) {
    const write = a.action === "add" ? client.addAgentSkill.bind(client) : client.updateAgentSkill.bind(client);
    await write({ botId: bot.id, name: a.name, description: a.description, content: a.content });
  }
  return { bot: bot.name, applied: apply, skills: plan.map(({ name, file, action }) => ({ name, file, action })) };
}

export async function run(argv, opts = {}) {
  const result = await dispatch(argv, opts);
  return { code: result.code, out: JSON.parse(result.redact(JSON.stringify(result.out))), jsonl: Boolean(result.jsonl) };
}

async function dispatch(argv, { env = process.env, sdk, sleep = (ms) => new Promise((r) => setTimeout(r, ms)) }) {
  const { cmd, bot: botName, text, flags } = parseArgs(argv);
  let redact = (t) => String(t);
  if (!["bots", "send", "wait", "ask", "read", "install"].includes(cmd) || (cmd !== "bots" && !botName)) return { redact, code: 2, out: { ok: false, error: "USAGE", message: USAGE } };
  const usage = (message) => ({ redact, code: 2, out: { ok: false, error: "USAGE", message } });
  for (const k of ["timeout", "interval"]) {
    if (flags[k] !== undefined && seconds(flags[k]) === null) return usage(`--${k} takes seconds, or a number with s, m or h: ${flags[k]}`);
  }
  if (flags.since !== undefined && Number.isNaN(Date.parse(flags.since))) return usage(`--since takes an ISO time: ${flags.since}`);
  const dir = env.GROK_BOT_SDK_DIR || path.join(os.homedir(), ".cache", "grok-bot-sdk");
  try {
    const { GrokBotClient, desktopCredentials, version } = sdk ?? (await loadSdk(dir));
    const creds = await desktopCredentials();
    redact = redactor(creds);
    let appVersion = "unknown";
    try { appVersion = version(); } catch {}
    const client = new GrokBotClient({ ...creds, version: appVersion });
    const opt = (k) => Number(flags[k] ?? DEFAULTS[k]);
    const timing = { timeout: seconds(flags.timeout ?? DEFAULTS.timeout), interval: seconds(flags.interval ?? DEFAULTS.interval), sleep };
    if (cmd === "bots") {
      const { bots, truncated } = await client.listBots();
      return { redact, code: 0, out: { ok: true, appVersion, bots: bots.map((b) => b.name), truncated } };
    }
    const bot = await findBot(client, botName);
    if (cmd === "install") return { redact, code: 0, out: { ok: true, ...(await install(client, bot, flags.apply === true)) } };
    if (cmd === "send") return { redact, code: 0, out: { ok: true, ...(await send(client, bot, text, flags["message-id"])) } };
    if (cmd === "wait") {
      if (flags.after === undefined) return { redact, code: 2, out: { ok: false, error: "USAGE", message: "wait needs --after <seq> from send" } };
      return { redact, code: 0, out: { ok: true, ...(await wait(client, bot, flags.after, flags["message-id"], timing)) } };
    }
    if (cmd === "ask") {
      const sent = await send(client, bot, text, flags["message-id"]);
      return { redact, code: 0, out: { ok: true, ...sent, ...(await wait(client, bot, sent.after, sent.messageId, timing)) } };
    }
    const { entries } = await client.listTranscript({ botId: bot.id, limit: opt("limit") });
    const since = flags.since ? Date.parse(flags.since) : null;
    const shown = entries.map(line).filter((e) => since === null || (e.ts !== null && Date.parse(e.ts) > since));
    return { redact, code: 0, out: { ok: true, bot: bot.name, entries: shown }, jsonl: flags.jsonl !== undefined };
  } catch (e) {
    return { redact, code: 1, out: { ok: false, error: e.code || "ERROR", message: redact(e.message).slice(0, 300) } };
  }
}

// Run as a command, also through a symlink (the skills install links the skill folder): compare real paths.
const isMain = () => {
  try {
    return realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url));
  } catch {
    return false;
  }
};
if (isMain()) {
  const { code, out, jsonl } = await run(process.argv.slice(2));
  const rows = jsonl && out.ok ? out.entries.map(({ seq, ts, from, text }) => ({ seq, ts, from, text })) : [out];
  process.stdout.write(rows.map((r) => JSON.stringify(r) + "\n").join(""));
  process.exitCode = code;
}
