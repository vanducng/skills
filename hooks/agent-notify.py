#!/usr/bin/env python3
"""Telegram notifier for coding-agent hooks.

Pings a Telegram chat when Claude Code / Codex finishes a turn or needs
approval, with enough context (what / when / where) to triage the next action.

Wiring (see install.py):
  Claude (~/.claude/settings.json):  Stop + Notification hooks  (JSON on stdin)
  Codex  (~/.codex/config.toml):     notify program            (JSON as last arg)

Usage:
  agent-notify.py claude stop|notification     # JSON on stdin
  agent-notify.py codex '<json>'               # JSON as last arg

Config comes from the ENV (installable on any machine), e.g. in ~/.envrc:
  export TELEGRAM_BOT_TOKEN=...
  export TELEGRAM_CHAT_ID=...
  export CODEX_NOTIFY_FORWARD=...        # optional: chain a prior Codex notify
  export CODEX_NOTIFY_FORWARD_ARG=...    # optional
Stdlib only — no pip installs, no jq.
"""
import json
import os
import re
import socket
import subprocess
import sys
from datetime import datetime
from urllib import parse, request

KEYS = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "CODEX_NOTIFY_FORWARD", "CODEX_NOTIFY_FORWARD_ARG")
DEBUG = bool(os.environ.get("AGENT_NOTIFY_DEBUG"))


def load_config():
    cfg = {k: os.environ.get(k) for k in KEYS}
    # Fall back to ~/.envrc exports so the hook works even when the agent process
    # wasn't started with direnv loaded.
    if not (cfg["TELEGRAM_BOT_TOKEN"] and cfg["TELEGRAM_CHAT_ID"]):
        envrc = os.path.expanduser("~/.envrc")
        if os.path.isfile(envrc):
            parsed = parse_envrc(envrc)
            for k in KEYS:
                cfg[k] = cfg[k] or parsed.get(k)
    return cfg


def parse_envrc(path):
    out, pat = {}, re.compile(r"^\s*export\s+([A-Z_]+)=(.*)$")
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            m = pat.match(line)
            if not m:
                continue
            val = m.group(2).strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            out[m.group(1)] = val
    return out


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def short(p):
    home = os.path.expanduser("~")
    return "~" + p[len(home):] if p.startswith(home) else p


def tmux_ctx():
    pane = os.environ.get("TMUX_PANE")
    if not pane:
        return ""
    try:
        r = subprocess.run(["tmux", "display-message", "-p", "-t", pane, "#S:#W"],
                           capture_output=True, text=True, timeout=2)
        return r.stdout.strip()
    except Exception:
        return ""


def send(token, chat, text):
    body = parse.urlencode({
        "chat_id": chat,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
        "text": text,
    }).encode()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = request.urlopen(request.Request(url, data=body), timeout=8).read()
        if DEBUG:
            print(resp.decode())
    except Exception as e:  # never fail the hook
        if DEBUG:
            print("ERROR", e)


def build(agent, agent_icon, status_icon, what, cwd, preview):
    cwd = cwd or os.getcwd()
    project = os.path.basename(cwd.rstrip("/")) or cwd
    host = socket.gethostname().split(".")[0]
    when = datetime.now().strftime("%H:%M · %a %d %b")
    lines = [
        f"{agent_icon} <b>{agent}</b> · {status_icon} {esc(what)}",
        f"🕒 {when}   💻 <code>{esc(host)}</code>",
        f"📂 <b>{esc(project)}</b>",
        f"📁 <code>{esc(short(cwd))}</code>",
    ]
    tx = tmux_ctx()
    if tx:
        lines.append(f"🖥 <code>{esc(tx)}</code>")
    if preview:
        lines.append(f"💬 {esc(' '.join(preview.split())[:300])}")
    return "\n".join(lines)


def main():
    cfg = load_config()
    if not (cfg["TELEGRAM_BOT_TOKEN"] and cfg["TELEGRAM_CHAT_ID"]):
        return  # not configured → silent no-op

    src = sys.argv[1] if len(sys.argv) > 1 else ""
    if src == "claude":
        event = sys.argv[2] if len(sys.argv) > 2 else "stop"
        try:
            payload = json.load(sys.stdin)
        except Exception:
            payload = {}
        if event == "notification":
            icon, what, preview = "🔔", "needs you", payload.get("message", "")
        else:
            icon, what, preview = "✅", "turn complete", ""
        text = build("CLAUDE", "✳️", icon, what, payload.get("cwd", ""), preview)
    elif src == "codex":
        raw = sys.argv[2] if len(sys.argv) > 2 else "{}"
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {}
        ctype = payload.get("type", "")
        icon, what = {
            "approval-requested": ("🔔", "needs approval"),
            "agent-turn-complete": ("✅", "turn complete"),
        }.get(ctype, ("ℹ️", ctype or "event"))
        text = build("CODEX", "🟢", icon, what, payload.get("cwd", ""), payload.get("last-assistant-message", ""))
        fwd, arg = cfg["CODEX_NOTIFY_FORWARD"], cfg["CODEX_NOTIFY_FORWARD_ARG"]
        if fwd and os.access(fwd, os.X_OK):  # chain a previously-configured notify
            try:
                subprocess.Popen([fwd] + ([arg] if arg else []) + [raw],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
    else:
        return

    send(cfg["TELEGRAM_BOT_TOKEN"], cfg["TELEGRAM_CHAT_ID"], text)


if __name__ == "__main__":
    main()
