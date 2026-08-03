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

function debug(message: string): void {
  if (process.env.VD_LANGFUSE_DEBUG) console.error(`langfuse-trace (pi): ${message}`);
}

function exportSession(): void {
  // The candidate list is built once at module load (VD_LANGFUSE_EXPORTER is read
  // then), but existsSync runs per call, so an exporter installed mid-session is
  // picked up without restarting pi. Changing VD_LANGFUSE_EXPORTER does need one.
  const exporter = EXPORTER_CANDIDATES.find((path) => existsSync(path));
  if (!exporter) {
    debug(`no exporter found in: ${EXPORTER_CANDIDATES.join(", ")}`);
    return;
  }

  try {
    const child = spawn("python3", [exporter, "--agent", "pi", "--latest"], {
      stdio: "ignore",
      detached: true,
    });
    // Unref so a slow network call can never hold pi's event loop open on exit.
    child.unref();
    // Fires when python3 isn't on PATH — silent by default, since tracing is
    // best-effort, but diagnosable under VD_LANGFUSE_DEBUG.
    child.on("error", (error) => debug(`spawn failed: ${error.message}`));
  } catch (error) {
    debug(`spawn threw: ${error instanceof Error ? error.message : String(error)}`);
  }
}

export default function (pi: ExtensionAPI) {
  pi.on("agent_settled", () => exportSession());
}
