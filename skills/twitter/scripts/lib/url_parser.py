"""Parse the unified `target` argument used by fetch / reply / delete.

Accepts:
  - https://x.com/<user>/status/<id>          → ('tweet', '<id>')
  - https://twitter.com/<user>/status/<id>     → ('tweet', '<id>')
  - <numeric>                                  → ('tweet', '<numeric>')
  - @handle  /  handle                         → ('user', 'handle')
  - search:<query>                             → ('search', '<query>')
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_URL_RE = re.compile(
    r"^https?://(?:www\.)?(?:x|twitter)\.com/[^/]+/status/(\d+)",
    re.IGNORECASE,
)
_HANDLE_RE = re.compile(r"^@?([A-Za-z0-9_]{1,15})$")


@dataclass(frozen=True)
class Target:
    kind: str  # 'tweet' | 'user' | 'search'
    value: str


def parse_target(arg: str) -> Target:
    s = arg.strip()
    if not s:
        raise ValueError("empty target")

    m = _URL_RE.match(s)
    if m:
        return Target("tweet", m.group(1))

    if s.lower().startswith("search:"):
        q = s[len("search:") :].strip()
        if not q:
            raise ValueError("search target needs a query: 'search:<query>'")
        return Target("search", q)

    if s.isdigit():
        return Target("tweet", s)

    m = _HANDLE_RE.match(s)
    if m:
        return Target("user", m.group(1))

    raise ValueError(
        f"unrecognized target: {arg!r}. Use a tweet URL, @handle, numeric id, or 'search:<query>'."
    )


__all__ = ["Target", "parse_target"]
