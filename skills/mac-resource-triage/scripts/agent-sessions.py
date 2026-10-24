#!/usr/bin/env python3
"""List live Claude Code sessions with status and hours since their transcript last changed.

Reads Claude Code's runtime registry ($HOME/.claude/sessions/<pid>.json) and transcripts
($HOME/.claude/projects/*/<sessionId>.jsonl). Both are internal formats and may change.
Usage: agent-sessions.py [--idle-hours N]   (with N, also prints close candidates)
"""
import argparse
import glob
import json
import os
import subprocess
import time

HOME = os.path.expanduser("~")


def short_home(path: str) -> str:
    return "~" + path[len(HOME):] if path == HOME or path.startswith(HOME + os.sep) else path


def is_claude(cmd: str) -> bool:
    argv0 = cmd.split()[0]
    return os.path.basename(argv0) == "claude" or "/claude/versions/" in argv0


def process_table() -> dict:
    ps = subprocess.run(["ps", "-Ao", "pid=,ppid=,etime=,rss=,command="], capture_output=True, text=True)
    if ps.returncode != 0:
        raise SystemExit(f"ps failed ({ps.returncode}): {ps.stderr.strip()}")
    out = ps.stdout
    table = {}
    for line in out.splitlines():
        parts = line.split(None, 4)
        if len(parts) == 5:
            pid, ppid, etime, rss, cmd = parts
            table[int(pid)] = {"ppid": int(ppid), "etime": etime, "rss_mb": int(rss) // 1024, "cmd": cmd}
    return table


def ancestors(pid: int, table: dict) -> list:
    seen = []
    while pid in table and pid not in seen and pid > 1:
        seen.append(pid)
        pid = table[pid]["ppid"]
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--idle-hours", type=float, help="print idle sessions untouched for at least N hours")
    args = ap.parse_args()

    table = process_table()
    self_chain = set(ancestors(os.getpid(), table))
    now = time.time()
    rows = []
    for pid, proc in table.items():
        # Requiring a claude executable also keeps a reused PID's stale registry file out.
        if not is_claude(proc["cmd"]) or "--chrome-native-host" in proc["cmd"]:
            continue
        info = {}
        try:
            with open(f"{HOME}/.claude/sessions/{pid}.json") as fh:
                info = json.load(fh)
        except (OSError, ValueError):
            pass
        sid = info.get("sessionId", "")
        transcripts = glob.glob(f"{HOME}/.claude/projects/*/{sid}.jsonl") if sid else []
        idle_h = (now - max(map(os.path.getmtime, transcripts))) / 3600 if transcripts else None
        parent_cmds = " ".join(table[a]["cmd"] for a in ancestors(proc["ppid"], table))
        seat = "@" in info.get("name", "") or "--name" in proc["cmd"] or "tmux-send" in parent_cmds
        rows.append({
            "pid": pid,
            "status": info.get("status", "no-registry"),
            "idle_h": idle_h,
            "etime": proc["etime"],
            "rss_mb": proc["rss_mb"],
            "cwd": short_home(info.get("cwd", "?")),
            "sid": sid,
            "flag": "self" if pid in self_chain else ("seat" if seat else ""),
        })

    rows.sort(key=lambda r: -(r["idle_h"] if r["idle_h"] is not None else -1))
    print(f"{'pid':>7} {'status':<11} {'idle_h':>7} {'elapsed':>12} {'rss':>6} {'flag':<5} cwd")
    for r in rows:
        idle = f"{r['idle_h']:.1f}" if r["idle_h"] is not None else "?"
        print(f"{r['pid']:>7} {r['status']:<11} {idle:>7} {r['etime']:>12} {r['rss_mb']:>5}M {r['flag']:<5} {r['cwd']}")
    print(f"{len(rows)} sessions, {sum(r['rss_mb'] for r in rows)} MB RSS (MCP children not included)")

    if args.idle_hours is not None:
        picks = [r for r in rows if r["status"] == "idle" and not r["flag"]
                 and r["idle_h"] is not None and r["idle_h"] >= args.idle_hours]
        print(f"\nclose candidates (status idle, untouched >= {args.idle_hours}h, not self/seat):")
        for r in picks:
            print(f"  {r['pid']}  {r['idle_h']:.1f}h  {r['cwd']}  resume: claude --resume {r['sid']}")
        print(f"  pids: {' '.join(str(r['pid']) for r in picks) or '(none)'}")


if __name__ == "__main__":
    main()
