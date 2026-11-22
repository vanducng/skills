import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { beforeEach, test } from "node:test";
import { fileURLToPath } from "node:url";
import { parseArgs, redactor, run } from "./grok-bot.mjs";

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
  assert.deepEqual(out.bots, ["CNB", "ABS"]);
  assert.equal(out.appVersion, "1.2.3");
});

test("every send carries a messageId, made when none is given", async () => {
  const { out } = await run(["send", "CNB", "status?"], { env });
  assert.match(out.messageId, /^[0-9a-f-]{36}$/);
  assert.equal(out.after, "41");
  await run(["send", "CNB", "again", "--message-id", "m-1"], { env });
  const sends = calls().filter((c) => c.method === "sendMessage");
  assert.deepEqual(sends.map((c) => c.args.messageId), [out.messageId, "m-1"]);
});

test("ask sends and returns the bot's reply after the send", async () => {
  const { code, out } = await run(["ask", "cnb", "What", "is", "waiting?", "--interval", "0"], { env, sleep: noSleep });
  assert.equal(code, 0);
  assert.equal(out.reply.text, "FAKE_REPLY to: What is waiting?");
  assert.equal(out.reply.from, "bot");
});

test("wait ignores replies at or before --after and times out", async () => {
  const { code, out } = await run(["wait", "CNB", "--after", "41", "--timeout", "0"], { env, sleep: noSleep });
  assert.equal(code, 1);
  assert.equal(out.error, "TIMEOUT");
});

test("read shows the chat, newest last, filtered by --since", async () => {
  const all = (await run(["read", "ABS", "--limit", "5"], { env })).out.entries;
  assert.equal(all.length, 5);
  assert.deepEqual(all.at(-1), { seq: "17", ts: "2026-11-25T09:46:47.000Z", from: "bot", text: "abs reply 7", streaming: false });
  const late = (await run(["read", "ABS", "--since", "2026-11-25T09:46:45.000Z"], { env })).out.entries;
  assert.deepEqual(late.map((e) => e.seq), ["16", "17"]);
});

test("read --jsonl prints one {seq, ts, from, text} per line from the CLI", () => {
  const out = execFileSync("node", [path.join(here, "grok-bot.mjs"), "read", "CNB", "--jsonl"], { env: { ...process.env, ...env } }).toString();
  const rows = out.trim().split("\n").map((l) => JSON.parse(l));
  assert.deepEqual(rows.map((r) => Object.keys(r)), [["seq", "ts", "from", "text"], ["seq", "ts", "from", "text"]]);
  assert.deepEqual(rows.map((r) => r.from), ["operator", "bot"]);
});

test("no output carries the token, errors included", async () => {
  assert.equal(redactor({ accessToken: TOKEN })(`bad ${TOKEN}`), "bad [redacted]");
  for (const argv of [["bots"], ["send", "CNB", TOKEN], ["read", "nobody"]]) {
    const { out } = await run(argv, { env });
    assert.ok(!JSON.stringify(out).includes(TOKEN), argv.join(" "));
  }
});

test("usage errors exit 2", async () => {
  assert.equal((await run(["send"], { env })).code, 2);
  assert.equal((await run(["wait", "CNB"], { env })).code, 2);
  assert.deepEqual(parseArgs(["read", "CNB", "--jsonl", "--limit", "3"]).flags, { jsonl: true, limit: "3" });
});
