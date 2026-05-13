"""agent-browser-driven implementations of `fetch` and `post`.

Used when the router classifies a twikit failure as transaction drift or
Error 226. Same gopass cookies are injected into a persistent agent-browser
session named `twitter` so no UI login is required.

This is a v1 escape-hatch — selectors WILL break as X's DOM changes. See
`references/failure-modes.md` and the maintenance section in SKILL.md.
"""
from __future__ import annotations

import json
import shlex
import subprocess
from typing import Any

from . import auth

SESSION_NAME = "twitter"


class BrowserUnavailable(RuntimeError):
    pass


def _ab(*args: str) -> str:
    """Run `agent-browser --session twitter <args>` and return stdout."""
    cmd = ["agent-browser", "--session", SESSION_NAME, *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise BrowserUnavailable(
            f"agent-browser failed: {' '.join(shlex.quote(a) for a in cmd)}\n"
            f"stderr: {proc.stderr.strip()}"
        )
    return proc.stdout.strip()


def _inject_cookies() -> None:
    """Push gopass cookies into the named agent-browser session."""
    cookies = auth.read_cookies()
    for name, value in cookies.items():
        _ab(
            "cookies",
            "set",
            f"{name}={value}",
            "--domain",
            ".x.com",
            "--path",
            "/",
            "--secure",
            "--httpOnly",
        )


async def fetch_browser(target) -> dict[str, Any]:
    """Fetch a tweet via agent-browser; return a dict shaped like formatters.tweet_to_dict.

    `target` is a `lib.url_parser.Target` for a `tweet` (URL or numeric id).
    User feeds + search are not implemented in v1 (defer until twikit search
    actually breaks irrecoverably).
    """
    if target.kind != "tweet":
        raise NotImplementedError(
            f"browser fallback only supports tweet permalinks in v1; "
            f"target kind={target.kind!r}"
        )

    _inject_cookies()
    url = f"https://x.com/i/status/{target.value}"
    _ab("open", url)
    _ab("wait", "article[data-testid='tweet']")

    js = (
        "const a=document.querySelector(\"article[data-testid='tweet']\");"
        "if(!a)throw new Error('tweet article not found');"
        "const t=a.querySelector(\"[data-testid='tweetText']\");"
        "const h=a.querySelector(\"a[href*='/status/']\");"
        "const u=a.querySelector(\"div[data-testid='User-Name'] a\");"
        "JSON.stringify({"
        "text:t?t.innerText:'',"
        "permalink:h?h.href:'',"
        "screen_name:u?u.href.split('/').pop():''"
        "})"
    )
    raw = _ab("eval", js)
    parsed = json.loads(raw) if raw.startswith("{") else {}
    return {
        "id": target.value,
        "text": parsed.get("text", ""),
        "author": {"screen_name": parsed.get("screen_name") or "unknown", "name": None, "id": None},
        "created_at": "",
        "media": [],
        "urls": [],
        "reply_count": None,
        "retweet_count": None,
        "favorite_count": None,
        "view_count": None,
        "is_quote_status": False,
        "conversation_id": target.value,
    }


async def post_browser(text: str, media=None, reply_to: str | None = None) -> dict[str, Any]:
    """Browser-side post — deferred to v2.

    Phase 6 ships the router + classifier + fetch fallback. A browser-driven
    `post` requires a working compose-textbox selector and a reliable
    new-tweet-id extraction; both are brittle and not needed while
    twikit's create_tweet works under the patch (verified phase 3).
    See plan revision 2026-05-09 + SKILL.md maintenance section.
    """
    raise NotImplementedError(
        "browser-side post is deferred to v2; twikit primary path covers writes. "
        "If twikit writes break: implement the compose flow here against current "
        "X DOM (data-testid='tweetTextarea_0' + 'tweetButton')."
    )


__all__ = ["fetch_browser", "post_browser", "BrowserUnavailable", "SESSION_NAME"]
