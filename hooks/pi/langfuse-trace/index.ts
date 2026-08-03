// Langfuse tracing for pi.
//
// pi has no hook system, so this extension supplies the trigger that Claude Code
// and Codex get from theirs: when an agent run settles, spawn the shared Python
// exporter (hooks/langfuse-trace.py), which reads pi's own session JSONL and
// ships new turns to Langfuse.
//
// The exporter is incremental and idempotent, so firing on every settle is safe.
// It is spawned detached with output ignored: tracing must never slow down or
// break a pi turn. With no LANGFUSE_* credentials the exporter exits 0 silently.
//
// Verified against pi 0.83.0: `agent_settled` marks one logical agent run
// finishing (the pi analogue of a Stop hook) and carries no payload, and
// `SessionStartEvent` exposes only `previousSessionFile` — neither gives the
// active session path. So the exporter resolves it itself with `--latest`,
// which picks the most recently written pi session file: the live one.
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { type ExtensionAPI } from "@earendil-works/pi-coding-agent";

const EXPORTER_CANDIDATES = [
  process.env.VD_LANGFUSE_EXPORTER,
  join(homedir(), "skills", "hooks", "langfuse-trace.py"),
  join(homedir(), ".claude", "hooks", "langfuse-trace.py"),
].filter((path): path is string => Boolean(path));

function exportSession(): void {
  const exporter = EXPORTER_CANDIDATES.find((path) => existsSync(path));
  if (!exporter) return;

  try {
    const child = spawn("python3", [exporter, "--agent", "pi", "--latest"], {
      stdio: "ignore",
      detached: true,
    });
    // Unref so a slow network call can never hold pi's event loop open on exit.
    child.unref();
    child.on("error", () => {});
  } catch {
    // Tracing is best-effort; a spawn failure must not surface to the user.
  }
}

export default function (pi: ExtensionAPI) {
  pi.on("agent_settled", () => exportSession());
}
