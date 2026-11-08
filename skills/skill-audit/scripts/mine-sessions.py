#!/usr/bin/env python3
"""Mine Claude Code, Codex, pi and Cursor transcripts into per-invocation skill-usage aggregates."""

from __future__ import annotations

import argparse
import bisect
try:
    import fcntl
except ImportError:  # no flock on this platform: concurrent writers are then not serialised
    fcntl = None
import glob
import json
import os
import re
import socket
import sys
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

HOME = os.path.expanduser("~")
CLAUDE_PROJECTS = os.path.join(HOME, ".claude", "projects")
CODEX_SESSIONS = os.path.join(HOME, ".codex", "sessions")
PI_SESSIONS = os.path.join(HOME, ".pi", "agent", "sessions")
# OpenRig pi-tui seats keep their own agent dir: <seat>/sessions/<ts>_<uuid>.jsonl.
PI_SEAT_SESSIONS = os.path.join(HOME, ".openrig", "state", "pi-tui")
CURSOR_PROJECTS = os.path.join(HOME, ".cursor", "projects")
RUNTIMES = ("claude", "codex", "pi", "cursor")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_DIRS = (
    os.path.join(HOME, ".claude", "skills"),
    os.path.join(HOME, ".agents", "skills"),
    os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..")),
)

NONE = "(none)"
MAX_LINE = 4_000_000
ID_MAP_CAP = 20_000

COMMAND_RE = re.compile(r"<command-name>/?([a-z][a-z0-9:_-]{1,40})</command-name>")
DOLLAR_RE = re.compile(r"(?:^|\s)\$([a-z][a-z0-9:_-]{1,40})")
SLASH_RE = re.compile(r"(?:^|\s)/([a-z][a-z0-9:_-]{1,40})")
SKILLMD_RE = re.compile(r"skills/([a-z0-9_-]+)/SKILL\.md")
CURSOR_TS_RE = re.compile(
    r"<timestamp>\s*\w+,\s*(\w+ \d+, \d+, \d+:\d+ [AP]M)\s*\(UTC([+-]\d+)(?::(\d\d))?\)"
)
CURSOR_QUERY_RE = re.compile(r"<user_query>(.*?)</user_query>", re.S)
CORRECTION_RE = re.compile(
    r"^(no[,. ]|nope\b|wrong\b|not what|that'?s not|revert\b|undo\b|you broke|"
    r"still (fail|broken|wrong)|didn'?t work|doesn'?t work|try again)",
    re.I,
)
INTERRUPT_MARK = "[Request interrupted by user"

HARNESS_COMMANDS = frozenset(
    """model effort clear login logout compact cost help resume exit status config init
    doctor bug upgrade permissions hooks mcp agents context todos plugin reload-plugins
    reload-skills memory ide vim terminal-setup release-notes add-dir output-style
    statusline privacy-settings feedback pr-comments migrate-installer install-github-app
    export rewind usage think todo""".split()
)

COUNTER_KEYS = (
    "invocations", "tool_calls", "tool_errors", "probes", "corrections", "interrupts",
    "aborts", "tokens", "agents", "agent_tool_calls", "agent_tool_errors", "agent_tokens",
)


# Per invocation window counters, kept beside the per-skill ones so one outcome row can be written per window.
WINDOW_KEYS = ("tool_calls", "tool_errors", "probes", "corrections", "interrupts", "aborts", "tokens")
# Outcome of a window (a coarse, labelled heuristic): failed on any abort, or on at least this many tool errors at
# this error rate; corrected on any correction or interrupt; else pass.
FAILED_MIN_ERRORS = 2
FAILED_ERROR_RATE = 0.5
OUTCOMES_DIR = os.path.join(HOME, ".share", "openrig", "skill-outcomes")

# A shell command whose last stage is one of these exits 1 to answer "nothing matched": the harness flags it as a
# tool error, but nothing failed. It counts as a probe, not an error, only when the command is a plain pipeline
# (no `&&`, `||`, `;`, `cd`, subshell or background job that could have failed first) ending in a probe tool, and
# its output is empty or one number (`grep -c`): any other text may be an earlier stage's diagnostic.
PROBE_TOOLS = frozenset({"grep", "egrep", "fgrep", "rg", "diff", "cmp", "pgrep", "test", "["})
SHELL_TOOLS = frozenset({"bash", "Bash"})
_EXIT1_HEAD = re.compile(r"\AExit code:? 1\b")
_EXIT1_TAIL = re.compile(r"Command exited with code 1\s*\Z")
_QUOTED = re.compile(r"'[^']*'|\"(?:[^\"\\]|\\.)*\"")
_REDIRECT = re.compile(r"\d*>&\d+|&>\S*|\d*>>?\s*\S+")
_COMPOUND = re.compile(r"&&|\|\||[;&\n`(){}]|\$\(")


def command_of(arguments):
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except ValueError:
            return ""
    command = arguments.get("command") if isinstance(arguments, dict) else None
    return command if isinstance(command, str) else ""


def probe_pipeline_tool(command):
    """Program name of the last stage of a plain pipeline, or '' when the command is anything more."""
    plain = _REDIRECT.sub(" ", _QUOTED.sub("Q", command))
    if _COMPOUND.search(plain):
        return ""
    stages = [x.strip() for x in plain.split("|") if x.strip()]
    for word in stages[-1].split() if stages else []:
        if word in ("!", "command", "builtin", "sudo", "env") or re.match(r"[A-Za-z_]\w*=", word):
            continue
        return os.path.basename(word)
    return ""


def is_probe_exit(tool, command, content):
    """True for an error result that is only a probe's exit 1 (no match), not a failure."""
    if tool not in SHELL_TOOLS or probe_pipeline_tool(command) not in PROBE_TOOLS:
        return False
    text = "\n".join(texts_of(content)).strip()
    if _EXIT1_HEAD.search(text):
        text = _EXIT1_HEAD.sub("", text, count=1).strip()
    elif _EXIT1_TAIL.search(text):
        text = _EXIT1_TAIL.sub("", text, count=1).strip()
    else:
        return False
    return text == "" or text.isdigit()


def load_registry(dirs=REGISTRY_DIRS):
    names = set()
    for root in dirs:
        if not os.path.isdir(root):
            continue
        for entry in os.listdir(root):
            if entry.startswith("."):
                continue
            if os.path.isfile(os.path.join(root, entry, "SKILL.md")):
                names.add(entry)
    return names


def normalize(raw, registry):
    name = raw.split(":")[-1].strip("-_")
    if not name or name in HARNESS_COMMANDS:
        return None
    if not registry:
        return name
    return name if name in registry else None


def new_row(runtime, path):
    return {
        "runtime": runtime,
        "session": os.path.basename(path).removesuffix(".jsonl"),
        "project": None,
        "first_ts": None,
        "last_ts": None,
        "models": set(),
        "skills": Counter(),
        "skillmd_reads": Counter(),
        "aborts_by_reason": Counter(),
        "errors_by_tool": Counter(),
        "usage_by_tool": Counter(),
        "attr": defaultdict(lambda: defaultdict(int)),
        "windows": [],
        "user_msgs": 0,
        "malformed_lines": 0,
    }


def begin_window(row, skill, ts):
    row["windows"].append({"skill": skill, "start": ts or "", "end": None, "counts": dict.fromkeys(WINDOW_KEYS, 0)})


def end_window(row, ts):
    if row["windows"] and row["windows"][-1]["end"] is None:
        row["windows"][-1]["end"] = ts or ""


def interrupt_window(row, skill):
    """A Codex abort whose reason is `interrupted` is the user's Ctrl+C: in the window it is an interrupt, as pi's
    aborted turn already is, so the same act gives the same outcome on every runtime. The per-skill aggregate keeps it
    as an abort."""
    window = last_window(row, skill)
    if window is not None and window["counts"]["aborts"]:
        window["counts"]["aborts"] -= 1
        window["counts"]["interrupts"] += 1


def last_window(row, skill):
    return next((w for w in reversed(row["windows"]) if w["skill"] == skill), None)


def bump(row, skill, key, n=1):
    if n:
        row["attr"][skill][key] += n
        if key in WINDOW_KEYS and (window := last_window(row, skill)) is not None:
            window["counts"][key] += n


def iter_lines(path):
    with open(path, errors="replace") as fh:
        for line in fh:
            if len(line) > MAX_LINE:
                line = line[:MAX_LINE]
            try:
                yield json.loads(line)
            except Exception:
                yield None


def stamp(row, ts):
    if not ts:
        return
    if row["first_ts"] is None or ts < row["first_ts"]:
        row["first_ts"] = ts
    if row["last_ts"] is None or ts > row["last_ts"]:
        row["last_ts"] = ts


def timestamp_epoch(ts):
    if not ts:
        return None
    try:
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except (TypeError, ValueError, OverflowError):
        return None


def in_window(ts, cutoff_epoch, already_in_scope=False):
    if not cutoff_epoch:
        return True
    epoch = timestamp_epoch(ts)
    return already_in_scope if epoch is None else epoch >= cutoff_epoch


def texts_of(content):
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [c.get("text") or "" for c in content if isinstance(c, dict) and c.get("type") == "text"]
    return []


def mine_claude_session(path, registry, cutoff_epoch=0):
    row = new_row("claude", path)
    row["project"] = os.path.basename(os.path.dirname(path))
    marks = []
    cur = NONE
    id2call = {}
    corrections_seen = set()

    def invoke(name, ts, included, reset_unknown=False):
        nonlocal cur
        skill = normalize(name, registry)
        if not skill:
            if reset_unknown:
                cur = NONE
                marks.append((ts or "", NONE))
                end_window(row, ts)
            return
        cur = skill
        marks.append((ts or "", skill))
        if included:
            row["skills"][skill] += 1
            bump(row, skill, "invocations")
            begin_window(row, skill, ts)

    in_scope = not cutoff_epoch
    for d in iter_lines(path):
        if d is None:
            if in_scope:
                row["malformed_lines"] += 1
            continue
        ts = d.get("timestamp")
        included = in_window(ts, cutoff_epoch, in_scope)
        if included:
            in_scope = True
            stamp(row, ts)
        kind = d.get("type")
        if kind == "assistant":
            msg = d.get("message") or {}
            if included and msg.get("model"):
                row["models"].add(msg["model"])
            if included:
                bump(row, cur, "tokens", (msg.get("usage") or {}).get("output_tokens") or 0)
            for c in msg.get("content") or []:
                if not isinstance(c, dict) or c.get("type") != "tool_use":
                    continue
                name = c.get("name") or "?"
                if name == "Skill":
                    invoke(str((c.get("input") or {}).get("skill") or ""), ts, included, reset_unknown=True)
                if included:
                    row["usage_by_tool"][name] += 1
                    bump(row, cur, "tool_calls")
                if len(id2call) < ID_MAP_CAP:
                    id2call[c.get("id")] = (name, cur, command_of(c.get("input")))
        elif kind == "user":
            content = (d.get("message") or {}).get("content")
            if included and isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("is_error"):
                        tool, at, command = id2call.get(c.get("tool_use_id"), ("?", cur, ""))
                        if is_probe_exit(tool, command, c.get("content")):
                            bump(row, at, "probes")
                            continue
                        row["errors_by_tool"][tool] += 1
                        bump(row, at, "tool_errors")
            for text in texts_of(content):
                if not text:
                    continue
                if included:
                    row["user_msgs"] += 1
                    if INTERRUPT_MARK in text:
                        bump(row, cur, "interrupts")
                    stripped = text.strip()
                    if CORRECTION_RE.match(stripped) and stripped[:120] not in corrections_seen:
                        corrections_seen.add(stripped[:120])
                        bump(row, cur, "corrections")
                for name in COMMAND_RE.findall(text):
                    invoke(name, ts, included)

    roll_up_agents(row, marks, agent_root("claude", path), scan_agent, cutoff_epoch)
    return row


def skill_at(marks, ts):
    if not marks or not ts:
        return NONE
    idx = bisect.bisect_right(marks, (ts, "￿"))
    return marks[idx - 1][1] if idx else NONE


def roll_up_agents(row, marks, agent_dir, scanner, cutoff_epoch=0, only=None):
    if not os.path.isdir(agent_dir):
        return
    for base, _, files in os.walk(agent_dir):
        for fname in files:
            if not fname.endswith(".jsonl") or (only and fname != only):
                continue
            path = os.path.join(base, fname)
            first_ts, window_first, window_last, calls, errs, tokens, bad = scanner(path, cutoff_epoch)
            row["malformed_lines"] += bad
            if cutoff_epoch and not window_first:
                continue
            stamp(row, window_first)
            stamp(row, window_last)
            # Attribute by agent start; window timestamps only bound retained counters.
            skill = skill_at(marks, first_ts)
            bump(row, skill, "agents")
            bump(row, skill, "agent_tool_calls", calls)
            bump(row, skill, "agent_tool_errors", errs)
            bump(row, skill, "agent_tokens", tokens)


def scan_agent(path, cutoff_epoch=0):
    first_ts, window_first, window_last = None, None, None
    calls, errs, tokens, bad = 0, 0, 0, 0
    ids = set()
    in_scope = not cutoff_epoch
    try:
        for d in iter_lines(path):
            if d is None:
                if in_scope:
                    bad += 1
                continue
            ts = d.get("timestamp")
            if first_ts is None and ts:
                first_ts = ts
            included = in_window(ts, cutoff_epoch, in_scope)
            if included:
                in_scope = True
                if window_first is None:
                    window_first = ts
                window_last = ts
            kind = d.get("type")
            if kind == "assistant":
                msg = d.get("message") or {}
                if included:
                    tokens += (msg.get("usage") or {}).get("output_tokens") or 0
                for c in msg.get("content") or []:
                    if isinstance(c, dict) and c.get("type") == "tool_use":
                        if included:
                            calls += 1
                        if len(ids) < ID_MAP_CAP:
                            ids.add(c.get("id"))
            elif included and kind == "user":
                content = (d.get("message") or {}).get("content")
                if isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("is_error"):
                            errs += 1
    except OSError:
        pass
    return first_ts, window_first, window_last, calls, errs, tokens, bad


def exit_failed(output):
    if isinstance(output, dict) and "exit_code" in output:
        try:
            return int(output["exit_code"]) != 0
        except (TypeError, ValueError):
            return False
    text = output if isinstance(output, str) else json.dumps(output) if output else ""
    m = re.search(r'"exit_code":\s*"?(-?\d+)"?', text)
    if m:
        return m.group(1) != "0"
    return text.startswith("failed") or '"error"' in text[:200]


def mine_codex_session(path, registry, cutoff_epoch=0):
    row = new_row("codex", path)
    cur = NONE
    seen_tokens = 0
    corrections_seen = set()

    in_scope = not cutoff_epoch
    for d in iter_lines(path):
        if d is None:
            if in_scope:
                row["malformed_lines"] += 1
            continue
        ts = d.get("timestamp")
        included = in_window(ts, cutoff_epoch, in_scope)
        if included:
            in_scope = True
            stamp(row, ts)
        kind = d.get("type")
        p = d.get("payload") or {}
        if kind == "session_meta":
            row["project"] = p.get("cwd") or (p.get("meta") or {}).get("cwd") or row["project"]
        elif kind == "turn_context":
            if included and p.get("model"):
                row["models"].add(p["model"])
        elif kind == "event_msg":
            ptype = p.get("type")
            if ptype == "user_message":
                text = p.get("message") or ""
                if included:
                    row["user_msgs"] += 1
                for raw in DOLLAR_RE.findall(text):
                    skill = normalize(raw, registry)
                    if skill:
                        cur = skill
                        if included:
                            row["skills"][skill] += 1
                            bump(row, skill, "invocations")
                            begin_window(row, skill, ts)
                stripped = text.strip()
                if included and CORRECTION_RE.match(stripped) and stripped[:120] not in corrections_seen:
                    corrections_seen.add(stripped[:120])
                    bump(row, cur, "corrections")
            elif included and ptype == "error":
                bump(row, cur, "tool_errors")
                row["errors_by_tool"]["event_error"] += 1
            elif included and ptype == "turn_aborted":
                reason = p.get("reason") or "unknown"
                bump(row, cur, "aborts")
                row["aborts_by_reason"][reason] += 1
                if reason == "interrupted":
                    interrupt_window(row, cur)
            elif ptype == "token_count":
                total = ((p.get("info") or {}).get("total_token_usage") or {}).get("total_tokens") or 0
                if total > seen_tokens:
                    if included:
                        bump(row, cur, "tokens", total - seen_tokens)
                    seen_tokens = total
        elif kind == "response_item":
            ptype = p.get("type")
            if ptype in ("function_call", "custom_tool_call"):
                name = p.get("name") or "exec"
                if included:
                    row["usage_by_tool"][name] += 1
                    bump(row, cur, "tool_calls")
                    for hit in SKILLMD_RE.findall(str(p.get("arguments") or p.get("input") or "")):
                        skill = normalize(hit, registry)
                        if skill:
                            row["skillmd_reads"][skill] += 1
            elif included and ptype in ("function_call_output", "custom_tool_call_output") and exit_failed(p.get("output")):
                bump(row, cur, "tool_errors")
                row["errors_by_tool"]["exec"] += 1
    return row


def open_window(row, marks, registry, name, ts, included):
    """Start a new attribution window on a validated skill ID; return the new current skill."""
    skill = normalize(name, registry)
    if not skill:
        return None
    marks.append((ts or "", skill))
    if included:
        row["skills"][skill] += 1
        bump(row, skill, "invocations")
        begin_window(row, skill, ts)
    return skill


def mine_pi_session(path, registry, cutoff_epoch=0):
    row = new_row("pi", path)
    marks = []
    cur = NONE
    id2call = {}
    corrections_seen = set()

    in_scope = not cutoff_epoch
    for d in iter_lines(path):
        if d is None:
            if in_scope:
                row["malformed_lines"] += 1
            continue
        ts = d.get("timestamp")
        included = in_window(ts, cutoff_epoch, in_scope)
        if included:
            in_scope = True
            stamp(row, ts)
        kind = d.get("type")
        if kind == "session":
            row["project"] = d.get("cwd") or row["project"]
            continue
        if kind != "message":
            continue
        msg = d.get("message") or {}
        role = msg.get("role")
        if role == "assistant":
            if included:
                if msg.get("model"):
                    row["models"].add(msg["model"])
                bump(row, cur, "tokens", (msg.get("usage") or {}).get("output") or 0)
                if msg.get("stopReason") == "aborted":
                    bump(row, cur, "interrupts")
            for c in msg.get("content") or []:
                if not isinstance(c, dict) or c.get("type") != "toolCall":
                    continue
                name = c.get("name") or "?"
                if included:
                    row["usage_by_tool"][name] += 1
                    bump(row, cur, "tool_calls")
                    for hit in SKILLMD_RE.findall(str(c.get("arguments") or "")):
                        skill = normalize(hit, registry)
                        if skill:
                            row["skillmd_reads"][skill] += 1
                if len(id2call) < ID_MAP_CAP:
                    id2call[c.get("id")] = (name, cur, command_of(c.get("arguments")))
        elif role == "toolResult":
            if included and msg.get("isError"):
                tool, at, command = id2call.get(
                    msg.get("toolCallId"), (msg.get("toolName") or "?", cur, "")
                )
                if is_probe_exit(tool, command, msg.get("content")):
                    bump(row, at, "probes")
                else:
                    row["errors_by_tool"][tool] += 1
                    bump(row, at, "tool_errors")
        elif role == "user":
            for text in texts_of(msg.get("content")):
                if not text:
                    continue
                if included:
                    row["user_msgs"] += 1
                    stripped = text.strip()
                    if CORRECTION_RE.match(stripped) and stripped[:120] not in corrections_seen:
                        corrections_seen.add(stripped[:120])
                        bump(row, cur, "corrections")
                for name in SLASH_RE.findall(text):
                    cur = open_window(row, marks, registry, name, ts, included) or cur

    # Sibling subagent runs land in <session>/<run-id>/run-N/session.jsonl; forks/ holds
    # full sessions of the same shape and would double-count, so match session.jsonl only.
    roll_up_agents(row, marks, agent_root("pi", path), scan_pi_agent, cutoff_epoch,
                   only="session.jsonl")
    return row


def scan_pi_agent(path, cutoff_epoch=0):
    first_ts, window_first, window_last = None, None, None
    calls, errs, tokens, bad = 0, 0, 0, 0
    in_scope = not cutoff_epoch
    try:
        for d in iter_lines(path):
            if d is None:
                if in_scope:
                    bad += 1
                continue
            ts = d.get("timestamp")
            if first_ts is None and ts:
                first_ts = ts
            included = in_window(ts, cutoff_epoch, in_scope)
            if included:
                in_scope = True
                if window_first is None:
                    window_first = ts
                window_last = ts
            if not included or d.get("type") != "message":
                continue
            msg = d.get("message") or {}
            if msg.get("role") == "assistant":
                tokens += (msg.get("usage") or {}).get("output") or 0
                calls += sum(1 for c in msg.get("content") or []
                             if isinstance(c, dict) and c.get("type") == "toolCall")
            elif msg.get("role") == "toolResult" and msg.get("isError"):
                errs += 1
    except OSError:
        pass
    return first_ts, window_first, window_last, calls, errs, tokens, bad


def cursor_timestamp(text):
    m = CURSOR_TS_RE.search(text)
    if not m:
        return None
    try:
        dt = datetime.strptime(m.group(1), "%b %d, %Y, %I:%M %p")
    except ValueError:
        return None
    hours = int(m.group(2))
    offset = timedelta(hours=abs(hours), minutes=int(m.group(3) or 0))
    return (dt - offset if hours >= 0 else dt + offset).strftime("%Y-%m-%dT%H:%M:%SZ")


def cursor_project(path):
    parts = path.split(os.sep)
    return parts[parts.index("agent-transcripts") - 1] if "agent-transcripts" in parts else None


def mine_cursor_session(path, registry, cutoff_epoch=0):
    row = new_row("cursor", path)
    row["project"] = cursor_project(path)
    marks = []
    cur = NONE
    corrections_seen = set()

    in_scope = not cutoff_epoch
    for d in iter_lines(path):
        if d is None:
            if in_scope:
                row["malformed_lines"] += 1
            continue
        role = d.get("role")
        content = (d.get("message") or {}).get("content")
        # Only user turns carry a clock, inside a <timestamp> tag; everything after one
        # inherits its window.
        ts = cursor_timestamp(" ".join(texts_of(content))) if role == "user" else None
        included = in_window(ts, cutoff_epoch, in_scope)
        if included:
            in_scope = True
            stamp(row, ts)
        if role == "assistant":
            for c in content or []:
                if not isinstance(c, dict) or c.get("type") != "tool_use":
                    continue
                if included:
                    row["usage_by_tool"][c.get("name") or "?"] += 1
                    bump(row, cur, "tool_calls")
                    for hit in SKILLMD_RE.findall(json.dumps(c.get("input") or {})):
                        skill = normalize(hit, registry)
                        if skill:
                            row["skillmd_reads"][skill] += 1
        elif role == "user":
            if included:
                row["user_msgs"] += 1
            for text in texts_of(content):
                for query in CURSOR_QUERY_RE.findall(text):
                    stripped = query.strip()
                    if included and CORRECTION_RE.match(stripped) and stripped[:120] not in corrections_seen:
                        corrections_seen.add(stripped[:120])
                        bump(row, cur, "corrections")
                    for name in SLASH_RE.findall(query) + DOLLAR_RE.findall(query):
                        cur = open_window(row, marks, registry, name, ts, included) or cur
        elif included and d.get("type") == "turn_ended" and d.get("status") == "aborted":
            bump(row, cur, "interrupts")

    roll_up_agents(row, marks, agent_root("cursor", path), scan_cursor_agent, cutoff_epoch)
    return row


def scan_cursor_agent(path, cutoff_epoch=0):
    first_ts, window_first, window_last = None, None, None
    calls, bad = 0, 0
    in_scope = not cutoff_epoch
    try:
        for d in iter_lines(path):
            if d is None:
                if in_scope:
                    bad += 1
                continue
            content = (d.get("message") or {}).get("content")
            ts = cursor_timestamp(" ".join(texts_of(content))) if d.get("role") == "user" else None
            if first_ts is None and ts:
                first_ts = ts
            included = in_window(ts, cutoff_epoch, in_scope)
            if included:
                in_scope = True
                if window_first is None:
                    window_first = ts
                window_last = ts
            if included and d.get("role") == "assistant":
                calls += sum(1 for c in content or []
                             if isinstance(c, dict) and c.get("type") == "tool_use")
    except OSError:
        pass
    # Cursor records no token usage and no tool_result, so tokens and errors stay 0.
    return first_ts, window_first, window_last, calls, 0, 0, bad


def runtime_roots(runtime):
    if runtime == "pi":
        return [PI_SESSIONS, PI_SEAT_SESSIONS]
    return [{"claude": CLAUDE_PROJECTS, "codex": CODEX_SESSIONS, "cursor": CURSOR_PROJECTS}[runtime]]


def agent_root(runtime, path):
    """Directory holding the subagent transcripts spawned by this session, if any."""
    if runtime == "cursor":
        return os.path.join(os.path.dirname(path), "subagents")
    return path.removesuffix(".jsonl")


def is_session_path(runtime, root, path):
    """True for a top-level session transcript; subagent and fork files roll up instead."""
    rel = os.path.relpath(path, root).split(os.sep)
    if runtime == "claude":
        # <project>/<uuid>.jsonl - subagents/ sits one level deeper.
        return len(rel) == 2
    if runtime == "pi":
        # <project>/<ts>_<uuid>.jsonl, or a seat's <seat>/sessions/<ts>_<uuid>.jsonl - forks/, run-N/ and
        # subagent-artifacts/ sit deeper.
        return len(rel) == 2 or (len(rel) == 3 and rel[1] == "sessions")
    if runtime == "cursor":
        # <project>/agent-transcripts/<id>/<id>.jsonl - subagents/ sits one level deeper.
        return len(rel) == 4 and rel[1] == "agent-transcripts"
    return True


def discover(runtime, since_days, root=None, cutoff_epoch=None):
    roots = [d for d in ([root] if root else runtime_roots(runtime)) if os.path.isdir(d)]
    if not roots:
        print(f"note: no {runtime} transcripts at {root or ', '.join(runtime_roots(runtime))}", file=sys.stderr)
        return []
    cutoff = cutoff_epoch if cutoff_epoch is not None else (time.time() - since_days * 86400 if since_days else 0)

    def fresh(path):
        try:
            return os.path.getmtime(path) >= cutoff
        except OSError:
            return False

    def fresh_tree(path):
        if fresh(path):
            return True
        agent_dir = agent_root(runtime, path)
        if not os.path.isdir(agent_dir):
            return False
        return any(fresh(os.path.join(base, name))
                   for base, _, files in os.walk(agent_dir)
                   for name in files if name.endswith(".jsonl"))

    paths = []
    for top in roots:
        for base, _, files in os.walk(top):
            for f in files:
                path = os.path.join(base, f)
                if f.endswith(".jsonl") and is_session_path(runtime, top, path) and fresh_tree(path):
                    paths.append(path)
    return sorted(paths)


def blank_skill():
    return {
        **{k: 0 for k in COUNTER_KEYS},
        "sessions": 0, "solo_sessions": 0, "skillmd_reads": 0,
        "projects": set(), "models": set(), "first_used": "", "last_used": "",
    }


def aggregate(rows):
    skills = {}
    for row in rows:
        invoked = set(row["skills"])
        solo = invoked if len(invoked) == 1 else set()
        for name, counts in row["attr"].items():
            s = skills.setdefault(name, blank_skill())
            s["sessions"] += 1
            if name in solo:
                s["solo_sessions"] += 1
            s["projects"].add(row.get("project") or "?")
            s["models"].update(row["models"])
            for key in COUNTER_KEYS:
                s[key] += counts.get(key, 0)
            first, last = row["first_ts"] or "", row["last_ts"] or ""
            if first and (not s["first_used"] or first < s["first_used"]):
                s["first_used"] = first
            if last > s["last_used"]:
                s["last_used"] = last
        for name, n in row["skillmd_reads"].items():
            skills.setdefault(name, blank_skill())["skillmd_reads"] += n
    for s in skills.values():
        s["projects"] = len(s["projects"])
        s["models"] = sorted(s["models"])
        s["err_rate"] = round(s["tool_errors"] / s["tool_calls"], 4) if s["tool_calls"] else None
    return skills


def baseline(rows):
    errors_by_tool, usage_by_tool, aborts = Counter(), Counter(), Counter()
    totals = Counter()
    for row in rows:
        errors_by_tool.update(row["errors_by_tool"])
        usage_by_tool.update(row["usage_by_tool"])
        aborts.update(row["aborts_by_reason"])
        totals["malformed_lines"] += row["malformed_lines"]
        totals["user_msgs"] += row.get("user_msgs", 0)
        for counts in row["attr"].values():
            for key in COUNTER_KEYS:
                totals[key] += counts.get(key, 0)
    calls = totals["tool_calls"]
    return {
        "sessions": len(rows),
        "tool_calls": calls,
        "tool_errors": totals["tool_errors"],
        "probes": totals["probes"],
        "err_rate": round(totals["tool_errors"] / calls, 4) if calls else None,
        "interrupts": totals["interrupts"],
        "aborts": totals["aborts"],
        "aborts_by_reason": dict(aborts.most_common()),
        "corrections": totals["corrections"],
        "subagents": totals["agents"],
        "subagent_tool_calls": totals["agent_tool_calls"],
        "user_msgs": totals["user_msgs"],
        "malformed_lines": totals["malformed_lines"],
        "errors_by_tool": dict(errors_by_tool.most_common(30)),
        "usage_by_tool": dict(usage_by_tool.most_common(40)),
    }


def classify(counts):
    """pass | corrected | failed for one window's counters. A coarse heuristic, labelled as such in the row."""
    calls, errors = counts["tool_calls"], counts["tool_errors"]
    if counts["aborts"] or (errors >= FAILED_MIN_ERRORS and calls and errors / calls >= FAILED_ERROR_RATE):
        return "failed"
    if counts["corrections"] or counts["interrupts"]:
        return "corrected"
    return "pass"


def outcome_rows(row):
    """One row per invocation window of a session: skill, runtime, session, window, outcome, counters, evidence."""
    out = []
    windows = row["windows"]
    seen = Counter()
    for index, window in enumerate(windows):
        tie = seen[(window["skill"], window["start"])]
        seen[(window["skill"], window["start"])] += 1
        end = window["end"] or (windows[index + 1]["start"] if index + 1 < len(windows) else row["last_ts"]) or ""
        out.append({
            "runtime": row["runtime"],
            "session": row["session"],
            "project": row["project"],
            "skill": window["skill"],
            "window": {"start": window["start"], "end": end, "index": index, "tie": tie},
            "outcome": classify(window["counts"]),
            "counts": window["counts"],
            "reads": row["skillmd_reads"].get(window["skill"], 0),
            "evidence": {"session": row["session"], "runtime": row["runtime"], "window_start": window["start"], "window_end": end},
            "method": "heuristic: failed = abort, or >= %d tool errors at >= %d%% of calls; corrected = correction or interrupt; else pass"
            % (FAILED_MIN_ERRORS, FAILED_ERROR_RATE * 100),
        })  # fmt: skip
    return out


def outcome_key(r):
    """Stable across scans of different width: not the window index, which shifts when an earlier window enters scope."""
    return (r["runtime"], r["session"], r["skill"], r["window"]["start"], r["window"].get("tie", 0))


def write_outcomes(path, new_rows):
    """Merge `new_rows` into the JSONL at `path` by key (a rerun, or a wider scan, updates rows in place). The
    read-merge-replace runs under an exclusive lock and through a unique temp file, so two miners on one host never
    interleave or lose each other's rows."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path + ".lock", "a") as lock:
        if fcntl is not None:
            fcntl.flock(lock, fcntl.LOCK_EX)
        merged = {}
        if os.path.isfile(path):
            with open(path) as fh:
                for line in fh:
                    try:
                        r = json.loads(line)
                        merged[outcome_key(r)] = r
                    except (ValueError, KeyError, TypeError):
                        continue
        for r in new_rows:
            merged[outcome_key(r)] = r
        tmp = f"{path}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
        try:
            with open(tmp, "w") as fh:
                for r in sorted(merged.values(), key=lambda r: (r["window"]["start"], r["runtime"], r["session"], r["window"]["index"])):
                    fh.write(json.dumps(r, sort_keys=True) + "\n")
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    return len(merged)


def session_json(row):
    out = dict(row)
    out["models"] = sorted(row["models"])
    for key in ("skills", "skillmd_reads", "aborts_by_reason", "errors_by_tool", "usage_by_tool"):
        out[key] = dict(row[key])
    out["attr"] = {k: dict(v) for k, v in row["attr"].items()}
    return out


MINERS = {"claude": mine_claude_session, "codex": mine_codex_session,
          "pi": mine_pi_session, "cursor": mine_cursor_session}


def run(runtime, registry, out_dir, since_days, cutoff_epoch=None):
    if cutoff_epoch is None:
        cutoff_epoch = time.time() - since_days * 86400 if since_days else 0
    paths = discover(runtime, since_days, cutoff_epoch=cutoff_epoch)
    miner = MINERS[runtime]
    rows = []
    out_path = os.path.join(out_dir, f"sessions-{runtime}.jsonl")
    with open(out_path, "w") as fh:
        for i, path in enumerate(paths, 1):
            try:
                row = miner(path, registry, cutoff_epoch)
            except OSError:
                continue
            if cutoff_epoch and not row["first_ts"]:
                continue
            rows.append(row)
            fh.write(json.dumps(session_json(row)) + "\n")
            if i % 200 == 0:
                print(f"{runtime}: {i}/{len(paths)}", file=sys.stderr)
    return rows


def summarize(name, skills, base):
    print(f"\n== {name} ==")
    print(f"sessions={base['sessions']} tool_calls={base['tool_calls']} "
          f"err_rate={base['err_rate']} corrections={base['corrections']} "
          f"interrupts={base['interrupts']} aborts={base['aborts']} malformed={base['malformed_lines']}")
    ranked = sorted(skills.items(), key=lambda kv: -kv[1]["invocations"])[:15]
    print(f"{'skill':<22}{'inv':>5}{'sess':>6}{'solo':>6}{'calls':>8}{'errs':>6}{'err%':>7}{'corr':>6}{'intr':>6}")
    for skill, s in ranked:
        rate = "-" if s["err_rate"] is None else f"{s['err_rate'] * 100:.1f}"
        print(f"{skill:<22}{s['invocations']:>5}{s['sessions']:>6}{s['solo_sessions']:>6}"
              f"{s['tool_calls']:>8}{s['tool_errors']:>6}{rate:>7}{s['corrections']:>6}{s['interrupts']:>6}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Mine skill usage from Claude Code, Codex, pi and Cursor transcripts.")
    ap.add_argument("--since", type=int, default=0, metavar="DAYS",
                    help="scan transcripts active in the last N days, then keep events in that window")
    ap.add_argument("--runtime", choices=RUNTIMES + ("all", "both"), default="all",
                    help="'both' is a legacy alias for claude+codex")
    ap.add_argument("--out", default=".", metavar="DIR", help="output directory for aggregates + session rows")
    ap.add_argument("--outcomes", nargs="?", const=OUTCOMES_DIR, default=None, metavar="DIR",
                    help="also write one outcome row per invocation window to DIR/<host>.jsonl "
                         "(default DIR: ~/.share/openrig/skill-outcomes; local, never a repo path)")
    args = ap.parse_args(argv)
    if args.since < 0:
        ap.error("--since must be >= 0")
    if args.outcomes is not None:
        args.outcomes = os.path.expanduser(args.outcomes.strip())
        if not args.outcomes:
            ap.error("--outcomes needs a directory (or no value for the default)")

    os.makedirs(args.out, exist_ok=True)
    registry = load_registry()
    if not registry:
        print("warn: no installed skills found; skill-ID validation is off and results will contain noise", file=sys.stderr)

    runtimes = {"all": RUNTIMES, "both": ("claude", "codex")}.get(args.runtime, (args.runtime,))
    cutoff_epoch = time.time() - args.since * 86400 if args.since else 0
    cutoff = time.strftime("%Y-%m-%dT%H:%M:%S.000000Z", time.gmtime(cutoff_epoch)) if args.since else ""
    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "since_days": args.since or None,
        "cutoff_at": cutoff or None,
        "registry_skills": len(registry),
        "runtimes": {},
    }
    used = set()
    outcomes = []
    for runtime in runtimes:
        rows = run(runtime, registry, args.out, args.since, cutoff_epoch)
        for session_row in rows:
            outcomes += outcome_rows(session_row)
        skills = aggregate(rows)
        base = baseline(rows)
        used.update(k for k in skills if k != NONE)
        report["runtimes"][runtime] = {"baseline": base, "skills": skills}
        summarize(runtime, skills, base)

    report["coverage"] = {
        "installed": len(registry),
        "used": len(used & registry),
        "activation_rate": round(len(used & registry) / len(registry), 4) if registry else None,
        "never_used": sorted(registry - used),
    }
    agg_path = os.path.join(args.out, "skill-aggregates.json")
    with open(agg_path, "w") as fh:
        json.dump(report, fh, indent=1, default=str)
    cov = report["coverage"]
    print(f"\ncoverage: {cov['used']}/{cov['installed']} installed skills used "
          f"({'-' if cov['activation_rate'] is None else round(cov['activation_rate'] * 100)}%)")
    print(f"wrote {agg_path}")
    if args.outcomes is not None:
        host = socket.gethostname().split(".")[0] or "host"
        total = write_outcomes(os.path.join(args.outcomes, f"{host}.jsonl"), outcomes)
        print(f"outcomes: {len(outcomes)} rows from this scan, {total} in {os.path.join(args.outcomes, host + '.jsonl')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
