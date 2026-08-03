#!/usr/bin/env python3
"""langfuse-trace - Ship Claude Code / Codex / pi sessions to Langfuse.

Reads a session transcript, converts each completed turn into a Langfuse
observation tree (turn span -> generation + tool spans), and POSTs it as OTLP
JSON. Incremental: a state file records how many turns of each session have
shipped, so firing on every turn never duplicates work.

Invocation
    Claude Code   Stop / SessionEnd hook (transcript_path arrives on stdin)
    Codex         codex.notify hook (turn-ended payload on argv/stdin)
    pi            langfuse-pi extension, or --scan for backfill

Exit code is always 0: observability must never block an agent turn.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

import vd_langfuse as lf  # noqa: E402
import vd_transcripts as tx  # noqa: E402

STATE_ENV = "VD_LANGFUSE_STATE"
AGENT_DIRS = {
    "codex": "~/.codex/sessions",
    "pi": "~/.pi/agent/sessions",
    "claude-code": "~/.claude/projects",
}


def state_path():
    override = os.environ.get(STATE_ENV)
    if override:
        return os.path.expanduser(override)
    base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return os.path.join(base, "vd", "langfuse-turns.json")


def read_state():
    try:
        with open(state_path(), "r", encoding="utf-8") as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(state):
    path = state_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = "%s.%d.tmp" % (path, os.getpid())
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
        os.replace(tmp, path)
        return True
    except OSError:
        return False


def build_spans(session, turns, config, seed=""):
    """Turn a parsed session into OTLP spans. Root span is re-sent each flush so
    Langfuse keeps the trace's end time and name current."""
    trace_id = lf.trace_id_for(session.id, seed)
    root_id = lf.span_id_for(session.id, "root", seed)

    common = {
        "langfuse.session.id": session.id,
        "user.id": config.user_id,
        "langfuse.trace.tags": [session.agent, "vd-langfuse"],
    }
    if config.environment:
        common["langfuse.environment"] = config.environment

    project = os.path.basename(session.cwd) if session.cwd else None
    all_turns = session.turns or turns
    start_ns = min([t.start_ns for t in all_turns if t.start_ns] or [0])
    end_ns = max([t.end_ns for t in all_turns if t.end_ns] or [start_ns])

    trace_name = "%s: %s" % (session.agent, project or session.id[:8])
    spans = [lf.make_span(trace_id, root_id, trace_name, start_ns, end_ns, dict(
        common,
        **{
            "langfuse.trace.name": trace_name,
            "langfuse.trace.metadata.agent": session.agent,
            "langfuse.trace.metadata.cwd": session.cwd,
            "langfuse.trace.metadata.project": project,
            "langfuse.trace.metadata.model": session.model,
            "langfuse.observation.input": lf._truncate(
                all_turns[0].user_input if all_turns else None, config.max_chars),
            "langfuse.observation.output": lf._truncate(
                all_turns[-1].output if all_turns else None, config.max_chars),
        }
    ))]

    for turn in turns:
        turn_id = lf.span_id_for(session.id, "turn:%d" % turn.index, seed)
        spans.append(lf.make_span(
            trace_id, turn_id, "turn %d" % (turn.index + 1),
            turn.start_ns or start_ns, turn.end_ns or turn.start_ns or start_ns,
            dict(common, **{
                "langfuse.observation.input": lf._truncate(turn.user_input, config.max_chars),
                "langfuse.observation.output": lf._truncate(turn.output, config.max_chars),
                "langfuse.observation.metadata.tool_count": len(turn.tools),
            }),
            parent_span_id=root_id,
        ))

        if turn.model or turn.usage:
            generation = dict(common, **{
                "langfuse.observation.type": "generation",
                "gen_ai.request.model": turn.model,
                "langfuse.observation.input": lf._truncate(turn.user_input, config.max_chars),
                "langfuse.observation.output": lf._truncate(turn.output, config.max_chars),
            })
            generation.update(lf.usage_attributes(turn.usage))
            if turn.cost is not None:
                # Langfuse only prices models it knows; agent-reported cost wins.
                generation["langfuse.observation.cost_details"] = json.dumps(
                    {"total": float(turn.cost)})
            spans.append(lf.make_span(
                trace_id, lf.span_id_for(session.id, "gen:%d" % turn.index, seed),
                turn.model or "generation",
                turn.start_ns or start_ns, turn.end_ns or turn.start_ns or start_ns,
                generation, parent_span_id=turn_id,
            ))

        for position, call in enumerate(turn.tools):
            spans.append(lf.make_span(
                trace_id,
                lf.span_id_for(session.id, "tool:%d:%d" % (turn.index, position), seed),
                "tool: %s" % call.name,
                call.start_ns or turn.start_ns or start_ns,
                call.end_ns or call.start_ns or turn.end_ns or start_ns,
                dict(common, **{
                    "langfuse.observation.type": "span",
                    "langfuse.observation.input": lf._truncate(call.input, config.max_chars),
                    "langfuse.observation.output": lf._truncate(call.output, config.max_chars),
                    "langfuse.observation.metadata.tool_name": call.name,
                }),
                parent_span_id=turn_id,
            ))

    return trace_id, spans


def export_transcript(path, agent=None, config=None, force=False, seed=""):
    """Export unshipped turns of one transcript. Returns a result dict."""
    config = config or lf.load_config()
    if not config.enabled:
        return {"ok": False, "reason": "langfuse credentials not set", "path": path}

    try:
        session = tx.parse(path, agent)
    except (ValueError, OSError) as exc:
        return {"ok": False, "reason": str(exc), "path": path}

    if not session.turns:
        return {"ok": True, "reason": "no turns", "path": path, "exported": 0}

    state = read_state()
    key = "%s:%s" % (session.agent, session.id)
    already = 0 if force else int((state.get(key) or {}).get("turns") or 0)
    pending = [t for t in session.turns if t.index >= already]
    if not pending:
        return {"ok": True, "reason": "up to date", "path": path, "exported": 0,
                "trace_id": lf.trace_id_for(session.id, seed)}

    trace_id, spans = build_spans(session, pending, config, seed)
    ok, status, detail = lf.export_spans(config, spans)
    if ok:
        state[key] = {"turns": len(session.turns), "trace_id": trace_id, "path": path}
        write_state(state)
    return {"ok": ok, "status": status, "detail": detail, "path": path,
            "agent": session.agent, "session_id": session.id, "trace_id": trace_id,
            "exported": len(pending) if ok else 0, "spans": len(spans)}


def newest_transcript(agent):
    root = os.path.expanduser(AGENT_DIRS[agent])
    newest, newest_mtime = None, -1
    for directory, _, files in os.walk(root):
        for name in files:
            if not name.endswith(".jsonl"):
                continue
            full = os.path.join(directory, name)
            try:
                mtime = os.path.getmtime(full)
            except OSError:
                continue
            if mtime > newest_mtime:
                newest, newest_mtime = full, mtime
    return newest


def scan(agent, limit, config, seed=""):
    root = os.path.expanduser(AGENT_DIRS[agent])
    found = []
    for directory, _, files in os.walk(root):
        for name in files:
            if name.endswith(".jsonl"):
                full = os.path.join(directory, name)
                try:
                    found.append((os.path.getmtime(full), full))
                except OSError:
                    continue
    found.sort(reverse=True)
    return [export_transcript(p, agent, config, seed=seed) for _, p in found[:limit]]


def transcript_from_stdin():
    """Claude Code hooks deliver JSON on stdin; Codex notify may too."""
    if sys.stdin is None or sys.stdin.isatty():
        return None, None
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return None, None
    if not raw.strip():
        return None, None
    try:
        payload = json.loads(raw)
    except ValueError:
        return None, None
    if not isinstance(payload, dict):
        return None, None
    return payload.get("transcript_path"), payload.get("session_id")


def main():
    parser = argparse.ArgumentParser(description="Export agent sessions to Langfuse")
    parser.add_argument("--agent", choices=sorted(AGENT_DIRS), help="agent that produced the transcript")
    parser.add_argument("--transcript", help="explicit transcript path")
    parser.add_argument("--latest", action="store_true", help="use the newest transcript for --agent")
    parser.add_argument("--scan", action="store_true", help="backfill recent transcripts for --agent")
    parser.add_argument("--limit", type=int, default=20, help="max transcripts for --scan")
    parser.add_argument("--force", action="store_true", help="re-export turns already shipped")
    parser.add_argument("--seed", default=os.environ.get("VD_LANGFUSE_TRACE_SEED", ""),
                        help="salt for trace ids (use to start a fresh trace)")
    parser.add_argument("--json", action="store_true", help="print machine-readable results")
    args = parser.parse_args()

    config = lf.load_config()
    if not config.enabled:
        if args.json:
            print(json.dumps({"ok": False, "reason": "langfuse credentials not set"}))
        elif config.debug:
            sys.stderr.write("langfuse-trace: LANGFUSE_PUBLIC_KEY/SECRET_KEY not set, skipping\n")
        return 0

    if args.scan:
        if not args.agent:
            parser.error("--scan requires --agent")
        results = scan(args.agent, args.limit, config, args.seed)
    else:
        path = args.transcript
        if not path:
            path, _ = transcript_from_stdin()
        if not path and args.latest and args.agent:
            path = newest_transcript(args.agent)
        if not path:
            if args.json:
                print(json.dumps({"ok": False, "reason": "no transcript"}))
            return 0
        results = [export_transcript(path, args.agent, config, args.force, args.seed)]

    if args.json:
        print(json.dumps(results, indent=2))
    elif config.debug:
        for result in results:
            sys.stderr.write("langfuse-trace: %s\n" % json.dumps(result))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # observability must never break a turn
        if os.environ.get("VD_LANGFUSE_DEBUG"):
            sys.stderr.write("langfuse-trace: %s\n" % exc)
        sys.exit(0)
