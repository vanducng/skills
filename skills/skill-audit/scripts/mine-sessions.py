#!/usr/bin/env python3
"""Mine Claude Code + Codex transcripts into per-invocation skill-usage aggregates."""

from __future__ import annotations

import argparse
import bisect
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict

HOME = os.path.expanduser("~")
CLAUDE_PROJECTS = os.path.join(HOME, ".claude", "projects")
CODEX_SESSIONS = os.path.join(HOME, ".codex", "sessions")
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
SKILLMD_RE = re.compile(r"skills/([a-z0-9_-]+)/SKILL\.md")
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
    "invocations", "tool_calls", "tool_errors", "corrections", "interrupts",
    "aborts", "tokens", "agents", "agent_tool_calls", "agent_tool_errors", "agent_tokens",
)


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
        "user_msgs": 0,
        "malformed_lines": 0,
    }


def bump(row, skill, key, n=1):
    if n:
        row["attr"][skill][key] += n


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
    if row["first_ts"] is None:
        row["first_ts"] = ts
    row["last_ts"] = ts


def texts_of(content):
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [c.get("text") or "" for c in content if isinstance(c, dict) and c.get("type") == "text"]
    return []


def mine_claude_session(path, registry):
    row = new_row("claude", path)
    row["project"] = os.path.basename(os.path.dirname(path))
    marks = []
    cur = NONE
    id2call = {}
    corrections_seen = set()

    def invoke(name, ts):
        nonlocal cur
        skill = normalize(name, registry)
        if not skill:
            return
        cur = skill
        row["skills"][skill] += 1
        bump(row, skill, "invocations")
        marks.append((ts or "", skill))

    for d in iter_lines(path):
        if d is None:
            row["malformed_lines"] += 1
            continue
        ts = d.get("timestamp")
        stamp(row, ts)
        kind = d.get("type")
        if kind == "assistant":
            msg = d.get("message") or {}
            if msg.get("model"):
                row["models"].add(msg["model"])
            bump(row, cur, "tokens", (msg.get("usage") or {}).get("output_tokens") or 0)
            for c in msg.get("content") or []:
                if not isinstance(c, dict) or c.get("type") != "tool_use":
                    continue
                name = c.get("name") or "?"
                row["usage_by_tool"][name] += 1
                bump(row, cur, "tool_calls")
                if len(id2call) < ID_MAP_CAP:
                    id2call[c.get("id")] = (name, cur)
                if name == "Skill":
                    invoke(str((c.get("input") or {}).get("skill") or ""), ts)
        elif kind == "user":
            content = (d.get("message") or {}).get("content")
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("is_error"):
                        tool, at = id2call.get(c.get("tool_use_id"), ("?", cur))
                        row["errors_by_tool"][tool] += 1
                        bump(row, at, "tool_errors")
            for text in texts_of(content):
                if not text:
                    continue
                row["user_msgs"] += 1
                if INTERRUPT_MARK in text:
                    bump(row, cur, "interrupts")
                stripped = text.strip()
                if CORRECTION_RE.match(stripped) and stripped[:120] not in corrections_seen:
                    corrections_seen.add(stripped[:120])
                    bump(row, cur, "corrections")
                for name in COMMAND_RE.findall(text):
                    invoke(name, ts)

    mine_claude_subagents(path, row, marks)
    return row


def skill_at(marks, ts):
    if not marks or not ts:
        return NONE
    idx = bisect.bisect_right(marks, (ts, "￿"))
    return marks[idx - 1][1] if idx else NONE


def mine_claude_subagents(session_path, row, marks):
    agent_dir = session_path.removesuffix(".jsonl")
    if not os.path.isdir(agent_dir):
        return
    for base, _, files in os.walk(agent_dir):
        for fname in files:
            if not fname.endswith(".jsonl"):
                continue
            path = os.path.join(base, fname)
            first_ts, calls, errs, tokens, bad = scan_agent(path)
            row["malformed_lines"] += bad
            skill = skill_at(marks, first_ts)
            bump(row, skill, "agents")
            bump(row, skill, "agent_tool_calls", calls)
            bump(row, skill, "agent_tool_errors", errs)
            bump(row, skill, "agent_tokens", tokens)


def scan_agent(path):
    first_ts, calls, errs, tokens, bad = None, 0, 0, 0, 0
    ids = set()
    try:
        for d in iter_lines(path):
            if d is None:
                bad += 1
                continue
            if first_ts is None:
                first_ts = d.get("timestamp")
            kind = d.get("type")
            if kind == "assistant":
                msg = d.get("message") or {}
                tokens += (msg.get("usage") or {}).get("output_tokens") or 0
                for c in msg.get("content") or []:
                    if isinstance(c, dict) and c.get("type") == "tool_use":
                        calls += 1
                        if len(ids) < ID_MAP_CAP:
                            ids.add(c.get("id"))
            elif kind == "user":
                content = (d.get("message") or {}).get("content")
                if isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("is_error"):
                            errs += 1
    except OSError:
        pass
    return first_ts, calls, errs, tokens, bad


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


def mine_codex_session(path, registry):
    row = new_row("codex", path)
    cur = NONE
    seen_tokens = 0
    corrections_seen = set()

    for d in iter_lines(path):
        if d is None:
            row["malformed_lines"] += 1
            continue
        stamp(row, d.get("timestamp"))
        kind = d.get("type")
        p = d.get("payload") or {}
        if kind == "session_meta":
            row["project"] = p.get("cwd") or (p.get("meta") or {}).get("cwd") or row["project"]
        elif kind == "turn_context":
            if p.get("model"):
                row["models"].add(p["model"])
        elif kind == "event_msg":
            ptype = p.get("type")
            if ptype == "user_message":
                text = p.get("message") or ""
                row["user_msgs"] += 1
                for raw in DOLLAR_RE.findall(text):
                    skill = normalize(raw, registry)
                    if skill:
                        cur = skill
                        row["skills"][skill] += 1
                        bump(row, skill, "invocations")
                stripped = text.strip()
                if CORRECTION_RE.match(stripped) and stripped[:120] not in corrections_seen:
                    corrections_seen.add(stripped[:120])
                    bump(row, cur, "corrections")
            elif ptype == "error":
                bump(row, cur, "tool_errors")
                row["errors_by_tool"]["event_error"] += 1
            elif ptype == "turn_aborted":
                bump(row, cur, "aborts")
                row["aborts_by_reason"][p.get("reason") or "unknown"] += 1
            elif ptype == "token_count":
                total = ((p.get("info") or {}).get("total_token_usage") or {}).get("total_tokens") or 0
                if total > seen_tokens:
                    bump(row, cur, "tokens", total - seen_tokens)
                    seen_tokens = total
        elif kind == "response_item":
            ptype = p.get("type")
            if ptype == "function_call":
                name = p.get("name") or "exec"
                row["usage_by_tool"][name] += 1
                bump(row, cur, "tool_calls")
                for hit in SKILLMD_RE.findall(str(p.get("arguments") or "")):
                    skill = normalize(hit, registry)
                    if skill:
                        row["skillmd_reads"][skill] += 1
            elif ptype == "function_call_output" and exit_failed(p.get("output")):
                bump(row, cur, "tool_errors")
                row["errors_by_tool"]["exec"] += 1
    return row


def discover(runtime, since_days, root=None):
    root = root or (CLAUDE_PROJECTS if runtime == "claude" else CODEX_SESSIONS)
    if not os.path.isdir(root):
        print(f"note: no {runtime} transcripts at {root}", file=sys.stderr)
        return []
    cutoff = time.time() - since_days * 86400 if since_days else 0

    def fresh(path):
        try:
            return os.path.getmtime(path) >= cutoff
        except OSError:
            return False

    paths = []
    if runtime == "claude":
        for project in os.listdir(root):
            pdir = os.path.join(root, project)
            if not os.path.isdir(pdir):
                continue
            paths += [os.path.join(pdir, f) for f in os.listdir(pdir)
                      if f.endswith(".jsonl") and fresh(os.path.join(pdir, f))]
    else:
        for base, _, files in os.walk(root):
            paths += [os.path.join(base, f) for f in files
                      if f.endswith(".jsonl") and fresh(os.path.join(base, f))]
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


def session_json(row):
    out = dict(row)
    out["models"] = sorted(row["models"])
    for key in ("skills", "skillmd_reads", "aborts_by_reason", "errors_by_tool", "usage_by_tool"):
        out[key] = dict(row[key])
    out["attr"] = {k: dict(v) for k, v in row["attr"].items()}
    return out


def run(runtime, registry, out_dir, since_days):
    paths = discover(runtime, since_days)
    miner = mine_claude_session if runtime == "claude" else mine_codex_session
    rows = []
    out_path = os.path.join(out_dir, f"sessions-{runtime}.jsonl")
    with open(out_path, "w") as fh:
        for i, path in enumerate(paths, 1):
            try:
                row = miner(path, registry)
            except OSError:
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
    ap = argparse.ArgumentParser(description="Mine skill usage from Claude Code + Codex transcripts.")
    ap.add_argument("--since", type=int, default=0, metavar="DAYS", help="only sessions modified in the last N days")
    ap.add_argument("--runtime", choices=("claude", "codex", "both"), default="both")
    ap.add_argument("--out", default=".", metavar="DIR", help="output directory for aggregates + session rows")
    args = ap.parse_args(argv)
    if args.since < 0:
        ap.error("--since must be >= 0")

    os.makedirs(args.out, exist_ok=True)
    registry = load_registry()
    if not registry:
        print("warn: no installed skills found; skill-ID validation is off and results will contain noise", file=sys.stderr)

    runtimes = ("claude", "codex") if args.runtime == "both" else (args.runtime,)
    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "since_days": args.since or None,
        "registry_skills": len(registry),
        "runtimes": {},
    }
    used = set()
    for runtime in runtimes:
        rows = run(runtime, registry, args.out, args.since)
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
