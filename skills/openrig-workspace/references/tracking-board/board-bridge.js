// Pi extension for a rig's human seat: delivers notes sent from a tracking board as a user message,
// then reports progress and the final reply back to the board (feedback/status and feedback/done).
// Install: ln -s <this file> ~/.pi/agent/extensions/board-bridge.js, then /reload in the human seat.
// Only boards whose board.json has "owner_seat" equal to this seat's OPENRIG_SESSION_NAME are served.
import fs from "node:fs";
import path from "node:path";
import os from "node:os";

const root = process.env.OPENRIG_BOARDS_ROOT || path.join(os.homedir(), ".share", "openrig", "boards");
const seat = process.env.OPENRIG_SESSION_NAME || "";
const render = path.join(path.dirname(fs.realpathSync(new URL(import.meta.url).pathname)), "board.cjs");

const now = () => new Date().toISOString();
const readJson = file => { try { return JSON.parse(fs.readFileSync(file, "utf8")); } catch { return null; } };
const textOf = message => (message?.content ?? []).filter(p => p?.type === "text").map(p => p.text ?? "").join("");

// Boards this seat owns, rescanned at most once a minute.
let owned = [];
let scannedAt = 0;
function boards() {
  if (Date.now() - scannedAt < 60000) return owned;
  scannedAt = Date.now();
  owned = [];
  for (const org of safeDir(root)) for (const project of safeDir(path.join(root, org))) for (const slug of safeDir(path.join(root, org, project))) {
    const dir = path.join(root, org, project, slug);
    if (readJson(path.join(dir, "board.json"))?.owner_seat === seat) owned.push(dir);
  }
  return owned;
}
function safeDir(dir) { try { return fs.readdirSync(dir).filter(n => !n.startsWith(".")); } catch { return []; } }

function write(dir, sub, data) {
  fs.mkdirSync(path.join(dir, "feedback", sub), { recursive: true });
  fs.writeFileSync(path.join(dir, "feedback", sub, `${data.id}.json`), JSON.stringify(data, null, 2));
}

function prompt(fb, dir) {
  const board = path.relative(root, dir);
  const lines = fb.notes.map((n, i) => `${i + 1}. [${n.id} · ${n.kind}] on ${n.anchor || "the board"}${n.quote ? ` (quote: "${n.quote}")` : ""}\n   ${n.text.replace(/\n/g, "\n   ")}`);
  return [
    `Board feedback from the operator, sent from the tracking board ${board} (feedback ${fb.id}).`,
    `Apply each note: change ${board}/board.json and the git records where a note asks for it, send build work to the rig's owner seat, then run \`node ${render} render ${board}\`.`,
    "End your reply with one line per note: `<note id>: applied | deferred | needs you - <why>`.",
    "",
    ...lines,
  ].join("\n");
}

export default function (pi) {
  if (!/-human@/.test(seat)) return;
  let ctxRef;
  let current = null;
  let last = "";
  let timer;

  const deliver = () => {
    if (current) return;
    for (const dir of boards()) {
      const inbox = path.join(dir, "feedback", "inbox");
      const file = safeDir(inbox).filter(f => f.endsWith(".json")).sort()[0];
      if (!file) continue;
      const fb = readJson(path.join(inbox, file));
      fs.mkdirSync(path.join(dir, "feedback", "processing"), { recursive: true });
      fs.renameSync(path.join(inbox, file), path.join(dir, "feedback", "processing", file));
      if (!fb?.id || !Array.isArray(fb.notes)) continue;
      current = { dir, id: fb.id, started: false };
      write(dir, "status", { id: fb.id, state: "delivered", at: now() });
      const text = prompt(fb, dir);
      if (ctxRef?.isIdle?.() ?? true) pi.sendUserMessage(text);
      else pi.sendUserMessage(text, { deliverAs: "followUp" });
      return;
    }
  };

  pi.on("session_start", async (_event, ctx) => {
    ctxRef = ctx;
    clearInterval(timer);
    timer = setInterval(deliver, 3000);
    deliver();
  });
  pi.on("session_shutdown", async () => clearInterval(timer));

  pi.on("before_agent_start", async event => {
    if (current && !current.started && typeof event?.prompt === "string" && event.prompt.includes(current.id)) {
      current.started = true;
      last = "";
      write(current.dir, "status", { id: current.id, state: "working", at: now() });
    }
  });
  pi.on("message_end", async event => {
    if (current?.started && event?.message?.role === "assistant") last = textOf(event.message) || last;
  });
  pi.on("agent_settled", async event => {
    if (!current?.started) return;
    const { dir, id } = current;
    write(dir, "done", { id, reply: event?.aborted ? `${last}\n\n(aborted)` : last, at: now() });
    write(dir, "status", { id, state: event?.aborted ? "aborted" : "done", at: now() });
    current = null;
    setTimeout(deliver, 500);
  });
}
