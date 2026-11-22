// A fake GrokBotClient with the real one's method shapes. Like the real app, a send without a messageId is accepted
// but never shown in the chat, so the bot never answers it. Every call is logged to the state file.
import { existsSync, readFileSync, writeFileSync } from "node:fs";

const BOTS = [
  { id: "bot-atlas-1", name: "Atlas", sessionId: "s-atlas" },
  { id: "bot-birch-2", name: "Birch", sessionId: "s-birch" },
];
const SEED = {
  "bot-atlas-1": [
    { seq: "40", entryKind: "user_message", body: { message: "morning", timestampMs: "1795600000000" } },
    { seq: "41", entryKind: "message", body: { role: "assistant", content: "Morning. Two PRs wait on you.", timestampMs: "1795600060000" } },
  ],
  "bot-birch-2": Array.from({ length: 8 }, (_, i) => ({
    seq: String(10 + i),
    entryKind: i % 2 ? "message" : "user_message",
    body: i % 2 ? { role: "assistant", content: `birch reply ${i}`, timestampMs: String(1795600000000 + i * 1000) } : { message: `birch ask ${i}`, timestampMs: String(1795600000000 + i * 1000) },
  })),
};

const file = () => process.env.FAKE_GROK_STATE || "fake-grok-state.json";
const load = () => (existsSync(file()) ? JSON.parse(readFileSync(file(), "utf8")) : { calls: [], transcripts: structuredClone(SEED) });
const save = (s) => writeFileSync(file(), JSON.stringify(s, null, 1));
const log = (s, method, args) => s.calls.push({ method, args });

export class SDKError extends Error {}

export class GrokBotClient {
  constructor(options) {
    if (!options?.accessToken) throw new SDKError("no access token");
  }
  async getMe() {
    return { id: "me" };
  }
  async listBots() {
    const s = load();
    log(s, "listBots", {});
    save(s);
    return { bots: BOTS, truncated: false, slackConnections: [] };
  }
  async listTranscript({ botId, limit = 50 }) {
    const s = load();
    log(s, "listTranscript", { botId, limit });
    save(s);
    return { generation: 1, entries: (s.transcripts[botId] || []).slice(-limit), unreadAnchor: null };
  }
  async sendMessage({ botId, text, messageId }) {
    const s = load();
    log(s, "sendMessage", { botId, text, messageId: messageId ?? null });
    const t = (s.transcripts[botId] ||= []);
    if (messageId) {
      const next = Number(t.at(-1)?.seq ?? 0) + 1;
      t.push({ seq: String(next), entryKind: "user_message", body: { message: text, messageId, timestampMs: "1795600100000" } });
      t.push({ seq: String(next + 1), entryKind: "message", body: { role: "assistant", content: `FAKE_REPLY to: ${text}`, timestampMs: "1795600160000" } });
    }
    save(s);
    return { botId, messageId: messageId ?? `server-${s.calls.length}`, delivery: "accepted-box", dispatched: true };
  }
  async listAgentSkills(botId) {
    const s = load();
    log(s, "listAgentSkills", { botId });
    save(s);
    return { skills: s.skills ?? [{ id: "k1", name: "notes", description: "an unrelated skill", body: "keep me", source: "user" }] };
  }
  async addAgentSkill({ botId, name, description, content }) {
    return this.#writeSkill("addAgentSkill", { botId, name, description, content });
  }
  async updateAgentSkill({ botId, name, description, content }) {
    return this.#writeSkill("updateAgentSkill", { botId, name, description, content });
  }
  #writeSkill(method, args) {
    const s = load();
    log(s, method, args);
    s.skills = (s.skills ?? [{ id: "k1", name: "notes", description: "an unrelated skill", body: "keep me", source: "user" }]).filter((k) => k.name !== args.name);
    s.skills.push({ id: `k${s.calls.length}`, name: args.name, description: args.description, body: args.content, source: "user" });
    save(s);
    return { marketplace: { marketplaceId: "m", displayName: "Skills", description: "" }, plugins: [], skill: { name: args.name, description: args.description, sourcePath: "", sourceUrl: null, content: args.content, environments: [] } };
  }
  async getSendStatus({ botId, messageId }) {
    const s = load();
    log(s, "getSendStatus", { botId, messageId });
    save(s);
    return { status: "delivered", echoEntryId: null, rejectionCode: null, acceptedAtMs: "1795600100000" };
  }
}
