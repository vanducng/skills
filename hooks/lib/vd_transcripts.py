"""vd_transcripts - Normalize Claude Code / Codex / pi session transcripts.

Each agent writes JSONL but with a different record shape. Every adapter here
returns the same structure so the Langfuse exporter stays agent-agnostic:

    Session(id, agent, cwd, model, turns=[Turn])
    Turn(index, start_ns, end_ns, user_input, output, model, usage, cost, tools)
    ToolCall(name, input, output, start_ns, end_ns)

Timestamps are nanoseconds. Adapters never raise on malformed lines; a
truncated or half-written transcript yields the turns parsed so far.
"""

import json
import os
from datetime import datetime, timezone

NS = 1_000_000_000


class ToolCall:
    def __init__(self, name, tool_input=None, output=None, start_ns=0, end_ns=0):
        self.name = name
        self.input = tool_input
        self.output = output
        self.start_ns = start_ns
        self.end_ns = end_ns or start_ns


class Turn:
    def __init__(self, index, start_ns):
        self.index = index
        self.start_ns = start_ns
        self.end_ns = start_ns
        self.user_input = None
        self.output = None
        self.model = None
        self.usage = {}
        self.cost = None
        self.tools = []


class Session:
    def __init__(self, session_id, agent, cwd=None, model=None):
        self.id = session_id
        self.agent = agent
        self.cwd = cwd
        self.model = model
        self.turns = []


def _iso_to_ns(value):
    if not value:
        return 0
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * NS)
    except (ValueError, TypeError):
        return 0


def _epoch_to_ns(value):
    """Accept seconds, milliseconds, or nanoseconds and normalize to ns."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    if number <= 0:
        return 0
    if number > 1e17:
        return int(number)
    if number > 1e14:
        return int(number * 1000)
    if number > 1e11:
        return int(number * 1_000_000)
    return int(number * NS)


def _read_jsonl(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except ValueError:
                    continue
    except OSError:
        return


def _text_from_content(content):
    """Flatten an Anthropic/pi-style content array into plain text."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return None
    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text" and block.get("text"):
            parts.append(block["text"])
    return "\n".join(parts) or None


# --------------------------------------------------------------------------
# Claude Code: ~/.claude/projects/<slug>/<session>.jsonl
# --------------------------------------------------------------------------

def parse_claude(path):
    session = Session(os.path.basename(path).replace(".jsonl", ""), "claude-code")
    turn = None
    pending = {}

    for record in _read_jsonl(path):
        kind = record.get("type")
        ts = _iso_to_ns(record.get("timestamp"))
        if session.cwd is None and record.get("cwd"):
            session.cwd = record.get("cwd")
        if record.get("sessionId"):
            session.id = record["sessionId"]

        message = record.get("message") or {}

        if kind == "user":
            content = message.get("content")
            # Tool results arrive as user records; they close a pending tool span.
            if isinstance(content, list):
                closed = False
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        call = pending.pop(block.get("tool_use_id"), None)
                        if call:
                            call.output = _text_from_content(block.get("content")) or ""
                            call.end_ns = ts or call.start_ns
                            closed = True
                if closed:
                    continue
            text = _text_from_content(content)
            if text is None:
                continue
            turn = Turn(len(session.turns), ts)
            turn.user_input = text
            session.turns.append(turn)

        elif kind == "assistant":
            if turn is None:
                turn = Turn(len(session.turns), ts)
                session.turns.append(turn)
            model = message.get("model")
            if model:
                turn.model = model
                session.model = model
            usage = message.get("usage") or {}
            if usage:
                turn.usage = _merge_usage(turn.usage, {
                    "input": usage.get("input_tokens"),
                    "output": usage.get("output_tokens"),
                    "cache_read": usage.get("cache_read_input_tokens"),
                    "cache_write": usage.get("cache_creation_input_tokens"),
                })
            text = _text_from_content(message.get("content"))
            if text:
                turn.output = "\n".join(filter(None, [turn.output, text]))
            for block in message.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    call = ToolCall(block.get("name") or "tool", block.get("input"), None, ts)
                    turn.tools.append(call)
                    # An id-less call would collide with every other id-less call
                    # under a None key and silently steal their outputs.
                    if block.get("id") is not None:
                        pending[block["id"]] = call
            turn.end_ns = max(turn.end_ns, ts)

    return session


# --------------------------------------------------------------------------
# Codex: ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl
# --------------------------------------------------------------------------

def parse_codex(path):
    session = Session(os.path.basename(path).replace(".jsonl", ""), "codex")
    turn = None
    pending = {}

    for record in _read_jsonl(path):
        kind = record.get("type")
        payload = record.get("payload") or {}
        ts = _iso_to_ns(record.get("timestamp"))

        if kind == "session_meta":
            session.id = payload.get("session_id") or payload.get("id") or session.id
            session.cwd = payload.get("cwd") or session.cwd
            continue

        if kind == "turn_context":
            if payload.get("model"):
                session.model = payload["model"]
            if turn is not None and not turn.model:
                turn.model = payload.get("model")
            continue

        ptype = payload.get("type")

        if ptype == "user_message":
            turn = Turn(len(session.turns), ts)
            turn.user_input = payload.get("message")
            turn.model = session.model
            session.turns.append(turn)

        elif ptype == "agent_message" and turn is not None:
            text = payload.get("message")
            if text:
                turn.output = "\n".join(filter(None, [turn.output, text]))
            turn.end_ns = max(turn.end_ns, ts)

        elif ptype == "custom_tool_call" and turn is not None:
            call = ToolCall(payload.get("name") or "tool", payload.get("input"), None, ts)
            turn.tools.append(call)
            if payload.get("call_id") is not None:
                pending[payload["call_id"]] = call

        elif ptype == "custom_tool_call_output" and turn is not None:
            call = pending.pop(payload.get("call_id"), None)
            if call:
                call.output = payload.get("output")
                call.end_ns = ts or call.start_ns

        elif ptype == "token_count" and turn is not None:
            last = ((payload.get("info") or {}).get("last_token_usage")) or {}
            if last:
                turn.usage = _merge_usage(turn.usage, {
                    "input": last.get("input_tokens"),
                    "output": last.get("output_tokens"),
                    "cache_read": last.get("cached_input_tokens"),
                    "cache_write": last.get("cache_write_input_tokens"),
                    "reasoning": last.get("reasoning_output_tokens"),
                })

        elif ptype == "task_complete" and turn is not None:
            final = payload.get("last_agent_message")
            # last_agent_message is the turn's answer; the agent_message records
            # before it are commentary. Keep both, but don't repeat the answer
            # when it was already streamed as the final agent_message.
            if final and not (turn.output or "").rstrip().endswith(final.rstrip()):
                turn.output = "\n".join(filter(None, [turn.output, final]))
            started = _epoch_to_ns(payload.get("started_at"))
            completed = _epoch_to_ns(payload.get("completed_at"))
            if started:
                turn.start_ns = started
            turn.end_ns = max(completed or ts, turn.start_ns)

    return session


# --------------------------------------------------------------------------
# pi: ~/.pi/agent/sessions/<slug>/<timestamp>_<uuid>.jsonl
# --------------------------------------------------------------------------

def parse_pi(path):
    session = Session(os.path.basename(path).split("_")[-1].replace(".jsonl", ""), "pi")
    turn = None

    for record in _read_jsonl(path):
        kind = record.get("type")
        ts = _iso_to_ns(record.get("timestamp"))

        if kind == "session":
            session.id = record.get("id") or session.id
            session.cwd = record.get("cwd") or session.cwd
            continue

        if kind == "model_change":
            session.model = record.get("modelId") or session.model
            continue

        if kind != "message":
            continue

        message = record.get("message") or {}
        role = message.get("role")
        content = message.get("content") or []

        if role == "user":
            turn = Turn(len(session.turns), ts)
            turn.user_input = _text_from_content(content)
            turn.model = session.model
            session.turns.append(turn)

        elif role == "assistant":
            if turn is None:
                turn = Turn(len(session.turns), ts)
                session.turns.append(turn)
            if message.get("model"):
                turn.model = message["model"]
                session.model = message["model"]
            usage = message.get("usage") or {}
            if usage:
                turn.usage = _merge_usage(turn.usage, {
                    "input": usage.get("input"),
                    "output": usage.get("output"),
                    "cache_read": usage.get("cacheRead"),
                    "cache_write": usage.get("cacheWrite"),
                    "reasoning": usage.get("reasoning"),
                })
                total_cost = (usage.get("cost") or {}).get("total")
                if isinstance(total_cost, (int, float)):
                    turn.cost = (turn.cost or 0) + total_cost
            text = _text_from_content(content)
            if text:
                turn.output = "\n".join(filter(None, [turn.output, text]))
            for block in content:
                if isinstance(block, dict) and block.get("type") == "toolCall":
                    turn.tools.append(
                        ToolCall(block.get("name") or "tool", block.get("arguments"), None, ts))
            turn.end_ns = max(turn.end_ns, ts)

        elif role == "toolResult" and turn is not None:
            # pi emits tool results in call order and never echoes a call id, so
            # positional matching is the only option. A tool whose result is
            # genuinely absent would shift every later result by one; pi always
            # emits a result per call (errors included), so that stays theoretical.
            text = _text_from_content(content)
            for call in turn.tools:
                if call.output is None:
                    call.output = text if text is not None else ""
                    call.end_ns = ts or call.start_ns
                    break
            turn.end_ns = max(turn.end_ns, ts)

    return session


def _merge_usage(existing, incoming):
    """Accumulate token counts. Accepts int or float (bool excluded: it is an int
    subclass and would silently count as 1); anything else is dropped rather than
    corrupting the total."""
    merged = dict(existing or {})
    for key, value in (incoming or {}).items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if value >= 0:
            merged[key] = merged.get(key, 0) + int(value)
    return merged


PARSERS = {"claude-code": parse_claude, "codex": parse_codex, "pi": parse_pi}


def detect_agent(path):
    """Infer the agent from a transcript path. Returns None when unknown."""
    resolved = os.path.realpath(path).replace(os.sep, "/")
    if "/.codex/sessions/" in resolved or os.path.basename(resolved).startswith("rollout-"):
        return "codex"
    if "/.pi/" in resolved:
        return "pi"
    if "/.claude/projects/" in resolved:
        return "claude-code"
    return None


def detect_agent_by_content(path, max_records=25):
    """Infer the agent from record shape, for transcripts outside the default
    directories (custom --session-dir, relocated projects, temp copies)."""
    for index, record in enumerate(_read_jsonl(path)):
        if index >= max_records:
            break
        kind = record.get("type")
        if kind in ("session_meta", "turn_context") or (
                kind in ("event_msg", "response_item") and "payload" in record):
            return "codex"
        if kind in ("model_change", "thinking_level_change"):
            return "pi"
        if kind == "session" and "cwd" in record:
            return "pi"
        if kind == "message" and isinstance(record.get("message"), dict):
            # pi nests role inside `message`; Claude Code puts type at top level.
            return "pi"
        if kind in ("user", "assistant") and ("sessionId" in record or "message" in record):
            return "claude-code"
    return None


def parse(path, agent=None):
    agent = agent or detect_agent(path) or detect_agent_by_content(path)
    parser = PARSERS.get(agent)
    if parser is None:
        raise ValueError("unknown agent for transcript: %s" % path)
    return parser(path)
