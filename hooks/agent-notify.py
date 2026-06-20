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
  export AGENT_NOTIFY_STOP=off|always   # claude turn-complete sound+push (default off)
  export AGENT_NOTIFY_SOUND=on|off      # macOS afplay ping (default on)
  export AGENT_NOTIFY_DRYRUN=1          # optional: print text/sound intent, skip side effects
Stdlib only — no pip installs, no jq.
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from datetime import datetime
from urllib import parse, request

KEYS = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "CODEX_NOTIFY_FORWARD", "CODEX_NOTIFY_FORWARD_ARG")
DEBUG = bool(os.environ.get("AGENT_NOTIFY_DEBUG"))


def load_config():
    cfg = {k: os.environ.get(k) for k in KEYS}
    # ~/.envrc exports as fallback so the hook works without direnv loaded.
    envrc = os.path.expanduser("~/.envrc")
    parsed = parse_envrc(envrc) if os.path.isfile(envrc) else {}
    for k in KEYS:
        cfg[k] = cfg[k] or parsed.get(k)
    # Chat ids: UNION env + ~/.envrc (deduped). A session started before an
    # ~/.envrc edit keeps the old value in its process env (unchangeable while
    # live) — merging means newly-added chats still get notified without restart.
    ids = []
    for src in (os.environ.get("TELEGRAM_CHAT_ID"), parsed.get("TELEGRAM_CHAT_ID")):
        for cid in (c.strip() for c in (src or "").split(",")):
            if cid and cid not in ids:
                ids.append(cid)
    if ids:
        cfg["TELEGRAM_CHAT_ID"] = ",".join(ids)
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
        r = subprocess.run(["tmux", "display-message", "-p", "-t", pane, "#S:#W:#P"],
                           capture_output=True, text=True, timeout=2)
        return r.stdout.strip()
    except Exception:
        return ""


def send(token, chat, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for cid in (c.strip() for c in chat.split(",") if c.strip()):  # comma-separated → fan out
        body = parse.urlencode({
            "chat_id": cid,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
            "text": text,
        }).encode()
        try:
            resp = request.urlopen(request.Request(url, data=body), timeout=8).read()
            if DEBUG:
                print(resp.decode())
        except Exception as e:  # never fail the hook
            if DEBUG:
                print("ERROR", e)


def play_sound(kind):
    """macOS afplay ping for claude events. Fail-open; off via AGENT_NOTIFY_SOUND=off."""
    if os.environ.get("AGENT_NOTIFY_SOUND", "on").lower() == "off":
        return
    nmp3 = os.path.expanduser("~/.claude/notification.mp3")
    sound = {
        "needs": nmp3 if os.path.isfile(nmp3) else "/System/Library/Sounds/Ping.aiff",
        "done": "/System/Library/Sounds/Glass.aiff",
    }.get(kind)
    if not sound:
        return
    if os.environ.get("AGENT_NOTIFY_DRYRUN"):
        print(f"SOUND {kind} -> {sound}")
        return
    if sys.platform != "darwin" or not shutil.which("afplay") or not os.path.isfile(sound):
        return
    try:
        subprocess.Popen(["afplay", sound], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


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
        # Drop code fences, collapse intra-line whitespace but KEEP newlines so
        # lists/paragraphs stay readable, then an expandable blockquote (Bot API
        # 7.0) so long messages stay tidy.
        body = preview.replace("```", "")
        body = "\n".join(re.sub(r"[ \t]+", " ", ln).strip() for ln in body.splitlines())
        # Telegram caps a message at 4096 chars; leave room for the header lines.
        body = re.sub(r"\n{3,}", "\n\n", body).strip()[:3500]
        lines.append(f"<blockquote expandable>{esc(body)}</blockquote>")
    return "\n".join(lines)


def main():
    cfg = load_config()
    configured = bool(cfg["TELEGRAM_BOT_TOKEN"] and cfg["TELEGRAM_CHAT_ID"])

    src = sys.argv[1] if len(sys.argv) > 1 else ""
    if src == "claude":
        event = sys.argv[2] if len(sys.argv) > 2 else "stop"
        try:
            payload = json.load(sys.stdin)
        except Exception:
            payload = {}
        if event == "notification":
            play_sound("needs")  # plays even when Telegram is unconfigured
            msg = payload.get("message", "")
            what = "needs approval" if "permission" in msg.lower() else "needs you"
            icon, preview = "🔔", msg
        else:
            # Per-turn "turn complete" sound+push spam during autonomous / auto-accept
            # runs; the real "your turn" ping is the idle Notification event.
            # AGENT_NOTIFY_STOP=always restores the legacy per-turn sound + push.
            if os.environ.get("AGENT_NOTIFY_STOP", "off").lower() != "always":
                if DEBUG:
                    print("SUPPRESS claude stop (AGENT_NOTIFY_STOP=off)")
                return
            play_sound("done")
            icon, what, preview = "✅", "turn complete", ""
        if not configured:
            return  # sound done; no Telegram creds → nothing to send
        text = build("CLAUDE", "🟠", icon, what, payload.get("cwd", ""), preview)
    elif src == "codex":
        if not configured:
            return
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
        text = build("CODEX", "🔵", icon, what, payload.get("cwd", ""), payload.get("last-assistant-message", ""))
        fwd, arg = cfg["CODEX_NOTIFY_FORWARD"], cfg["CODEX_NOTIFY_FORWARD_ARG"]
        if fwd and os.access(fwd, os.X_OK):  # chain a previously-configured notify
            try:
                subprocess.Popen([fwd] + ([arg] if arg else []) + [raw],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
    else:
        return

    if os.environ.get("AGENT_NOTIFY_DRYRUN"):
        print(text)
        return
    send(cfg["TELEGRAM_BOT_TOKEN"], cfg["TELEGRAM_CHAT_ID"], text)


if __name__ == "__main__":
    main()
