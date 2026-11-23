import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { cpSync, mkdtempSync, readFileSync, symlinkSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { beforeEach, test } from "node:test";
import { fileURLToPath } from "node:url";
import { botAssets, parseArgs, redactor, run, seconds, SKILL_MARK } from "./grok-bot.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const FAKE = path.join(here, "../evals/fake-sdk");
const TOKEN = "FAKE-TOKEN-7f3a9c2e5b1d4086";
const env = { GROK_BOT_SDK_DIR: FAKE };
const noSleep = async () => {};
const calls = () => JSON.parse(readFileSync(process.env.FAKE_GROK_STATE, "utf8")).calls;

beforeEach(() => {
  process.env.FAKE_GROK_STATE = path.join(mkdtempSync(path.join(os.tmpdir(), "grok-bot-")), "state.json");
});

test("bots lists names only", async () => {
  const { code, out } = await run(["bots"], { env });
  assert.equal(code, 0);
  assert.deepEqual(out.bots, ["Atlas", "Birch"]);
  assert.equal(out.appVersion, "1.2.3");
});

test("every send carries a messageId, made when none is given", async () => {
  const { out } = await run(["send", "Atlas", "status?"], { env });
  assert.match(out.messageId, /^[0-9a-f-]{36}$/);
  assert.equal(out.after, "41");
  await run(["send", "Atlas", "again", "--message-id", "m-1"], { env });
  const sends = calls().filter((c) => c.method === "sendMessage");
  assert.deepEqual(sends.map((c) => c.args.messageId), [out.messageId, "m-1"]);
});

test("ask sends and returns the bot's reply after the send", async () => {
  const { code, out } = await run(["ask", "atlas", "What", "is", "waiting?", "--interval", "0"], { env, sleep: noSleep });
  assert.equal(code, 0);
  assert.equal(out.reply.text, "FAKE_REPLY to: What is waiting?");
  assert.equal(out.reply.from, "bot");
});

test("wait ignores replies at or before --after and times out", async () => {
  const { code, out } = await run(["wait", "Atlas", "--after", "41", "--timeout", "0"], { env, sleep: noSleep });
  assert.equal(code, 1);
  assert.equal(out.error, "TIMEOUT");
});

test("read shows the chat, newest last, filtered by --since", async () => {
  const all = (await run(["read", "Birch", "--limit", "5"], { env })).out.entries;
  assert.equal(all.length, 5);
  assert.deepEqual(all.at(-1), { seq: "17", ts: "2026-11-25T09:46:47.000Z", from: "bot", text: "birch reply 7", streaming: false });
  const late = (await run(["read", "Birch", "--since", "2026-11-25T09:46:45.000Z"], { env })).out.entries;
  assert.deepEqual(late.map((e) => e.seq), ["16", "17"]);
});

test("read --jsonl prints one {seq, ts, from, text} per line from the CLI", () => {
  const out = execFileSync("node", [path.join(here, "grok-bot.mjs"), "read", "Atlas", "--jsonl"], { env: { ...process.env, ...env } }).toString();
  const rows = out.trim().split("\n").map((l) => JSON.parse(l));
  assert.deepEqual(rows.map((r) => Object.keys(r)), [["seq", "ts", "from", "text"], ["seq", "ts", "from", "text"]]);
  assert.deepEqual(rows.map((r) => r.from), ["operator", "bot"]);
});

test("no output carries the token, errors included", async () => {
  assert.equal(redactor({ accessToken: TOKEN })(`bad ${TOKEN}`), "bad [redacted]");
  for (const argv of [["bots"], ["send", "Atlas", TOKEN], ["read", "nobody"]]) {
    const { out } = await run(argv, { env });
    assert.ok(!JSON.stringify(out).includes(TOKEN), argv.join(" "));
  }
});

test("the default npm prefix loads an import-only package", async () => {
  const prefix = mkdtempSync(path.join(os.tmpdir(), "grok-bot-prefix-"));
  cpSync(FAKE, path.join(prefix, "node_modules", "grok-bot-sdk"), { recursive: true });
  const { code, out } = await run(["bots"], { env: { GROK_BOT_SDK_DIR: prefix } });
  assert.equal(code, 0, JSON.stringify(out));
  assert.deepEqual(out.bots, ["Atlas", "Birch"]);
  assert.equal((await run(["bots"], { env: { GROK_BOT_SDK_DIR: os.tmpdir() } })).out.error, "NO_SDK");
});

test("a token with a quote or a backslash is redacted in the serialised output too", async () => {
  const token = 'tok"en\\with-quote-and-backslash';
  const sdk = {
    desktopCredentials: async () => ({ accessToken: token }),
    version: () => "1.2.3",
    GrokBotClient: class {
      async listBots() {
        return { bots: [{ id: "b", name: token }], truncated: false };
      }
    },
  };
  for (const argv of [["bots"], ["read", "nobody"]]) {
    const { out } = await run(argv, { env, sdk });
    const text = JSON.stringify(out);
    assert.ok(!text.includes(token) && !text.includes(JSON.stringify(token).slice(1, -1)), `${argv[0]}: ${text}`);
  }
});

test("install saves each asset through the chat with a messageId, even on a bot not shared with a team", async () => {
  const names = botAssets().map((a) => a.name);
  assert.deepEqual(names, ["grokbot-format", "openrig-host-rules", "openrig-team"]);
  const dry = (await run(["install", "Atlas"], { env })).out;
  assert.equal(dry.applied, false);
  assert.equal(dry.shared, false);
  assert.deepEqual(dry.skills.map((k) => k.action), ["send", "send", "send"]);
  assert.equal(calls().filter((c) => c.method === "sendMessage").length, 0);
  const { code, out } = await run(["install", "Atlas", "--apply", "--interval", "0"], { env, sleep: noSleep });
  assert.equal(code, 0, JSON.stringify(out));
  assert.deepEqual(out.skills.map((k) => [k.name, k.saved, k.verified]), names.map((n) => [n, true, null]));
  const sends = calls().filter((c) => c.method === "sendMessage");
  assert.equal(sends.length, 3);
  assert.ok(sends.every((c) => c.args.messageId && c.args.text.includes(SKILL_MARK)));
  assert.ok(!calls().some((c) => /^(add|update|remove)AgentSkill$/.test(c.method)));
});

test("on a team-shared bot install skips an unchanged skill and verifies what it saved", async () => {
  const first = await run(["install", "Birch", "--apply", "--interval", "0"], { env, sleep: noSleep });
  assert.equal(first.out.shared, true);
  assert.deepEqual(first.out.skills.map((k) => k.verified), [true, true, true]);
  const state = JSON.parse(readFileSync(process.env.FAKE_GROK_STATE, "utf8"));
  state.skills.find((k) => k.name === "openrig-team").body = "an older text";
  writeFileSync(process.env.FAKE_GROK_STATE, JSON.stringify(state));
  const again = await run(["install", "Birch", "--apply", "--interval", "0"], { env, sleep: noSleep });
  assert.deepEqual(again.out.skills.map((k) => k.action), ["unchanged", "unchanged", "send"]);
  assert.ok(JSON.parse(readFileSync(process.env.FAKE_GROK_STATE, "utf8")).skills.some((k) => k.name === "notes"));
});

test("install fails when the bot does not confirm the save", async () => {
  const sdk = await import(path.join(FAKE, "sdk.mjs"));
  class Mute extends sdk.GrokBotClient {
    async sendMessage(args) {
      return super.sendMessage({ ...args, text: "just chatting" });
    }
  }
  const desktop = await import(path.join(FAKE, "desktop.mjs"));
  const { code, out } = await run(["install", "Atlas", "--apply", "--interval", "0"], {
    env,
    sleep: noSleep,
    sdk: { GrokBotClient: Mute, desktopCredentials: desktop.desktopCredentials, version: desktop.version },
  });
  assert.equal(code, 1);
  assert.equal(out.error, "NOT_SAVED");
  assert.match(out.skills[0].reply, /FAKE_REPLY/);
});

test("runs as a command through a symlinked skill folder", () => {
  const link = path.join(mkdtempSync(path.join(os.tmpdir(), "grok-bot-link-")), "grok-bot");
  symlinkSync(path.dirname(here), link);
  const out = execFileSync("node", [path.join(link, "scripts", "grok-bot.mjs"), "bots"], { env: { ...process.env, ...env } }).toString();
  assert.deepEqual(JSON.parse(out).bots, ["Atlas", "Birch"]);
});

test("--timeout takes seconds or s/m/h, and a bad --timeout or --since exits 2", async () => {
  assert.deepEqual(["300", "30s", "5m", "1h", "5x", "m"].map(seconds), [300, 30, 300, 3600, null, null]);
  const bad = await run(["wait", "Atlas", "--after", "41", "--timeout", "5 minutes"], { env, sleep: noSleep });
  assert.equal(bad.code, 2);
  assert.match(bad.out.message, /--timeout/);
  const late = await run(["wait", "Atlas", "--after", "41", "--timeout", "0m"], { env, sleep: noSleep });
  assert.equal(late.out.error, "TIMEOUT");
  const since = await run(["read", "Atlas", "--since", "yesterday-ish"], { env });
  assert.equal(since.code, 2);
  assert.match(since.out.message, /--since/);
});

test("usage errors exit 2", async () => {
  assert.equal((await run(["send"], { env })).code, 2);
  assert.equal((await run(["wait", "Atlas"], { env })).code, 2);
  assert.deepEqual(parseArgs(["read", "Atlas", "--jsonl", "--limit", "3"]).flags, { jsonl: true, limit: "3" });
});
