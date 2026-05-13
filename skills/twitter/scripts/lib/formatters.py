"""Format twikit Tweet objects to JSON-friendly dicts and human-readable markdown."""
from __future__ import annotations

from typing import Any, Iterable


def _safe_get(obj: Any, name: str, default: Any = None) -> Any:
    return getattr(obj, name, default)


def tweet_to_dict(t: Any) -> dict:
    """Reduce a twikit Tweet to a stable JSON-friendly shape."""
    user = _safe_get(t, "user")
    media = _safe_get(t, "media") or []
    media_out = []
    for m in media:
        media_out.append(
            {
                "type": _safe_get(m, "type"),
                "url": _safe_get(m, "media_url_https") or _safe_get(m, "media_url"),
            }
        )
    urls = []
    for u in _safe_get(t, "urls") or []:
        if isinstance(u, dict):
            urls.append(u.get("expanded_url") or u.get("url"))
        else:
            urls.append(_safe_get(u, "expanded_url") or _safe_get(u, "url"))
    author = None
    if user is not None:
        author = {
            "id": _safe_get(user, "id"),
            "screen_name": _safe_get(user, "screen_name"),
            "name": _safe_get(user, "name"),
        }
    return {
        "id": _safe_get(t, "id"),
        "created_at": str(_safe_get(t, "created_at") or ""),
        "author": author,
        "text": _safe_get(t, "text") or _safe_get(t, "full_text") or "",
        "reply_count": _safe_get(t, "reply_count"),
        "retweet_count": _safe_get(t, "retweet_count"),
        "favorite_count": _safe_get(t, "favorite_count"),
        "view_count": _safe_get(t, "view_count"),
        "urls": [u for u in urls if u],
        "media": media_out,
        "is_quote_status": _safe_get(t, "is_quote_status"),
        "conversation_id": _safe_get(t, "conversation_id"),
    }


def tweet_to_md(t: Any) -> str:
    d = tweet_to_dict(t)
    handle = (d["author"] or {}).get("screen_name") or "unknown"
    name = (d["author"] or {}).get("name") or ""
    when = d["created_at"]
    text = d["text"]
    likes = d.get("favorite_count") or 0
    rt = d.get("retweet_count") or 0
    replies = d.get("reply_count") or 0
    url = f"https://x.com/{handle}/status/{d['id']}" if d["id"] else ""
    header = f"**@{handle}**" + (f" ({name})" if name and name != handle else "")
    if when:
        header += f" · {when}"
    body = text.strip()
    footer_bits = [f"♥ {likes}", f"↻ {rt}", f"💬 {replies}"]
    if url:
        footer_bits.append(url)
    return f"{header}\n\n{body}\n\n_{' · '.join(footer_bits)}_"


def tweets_to_md(ts: Iterable[Any]) -> str:
    blocks = [tweet_to_md(t) for t in ts]
    return "\n\n---\n\n".join(blocks) if blocks else "_(no tweets)_"


__all__ = ["tweet_to_dict", "tweet_to_md", "tweets_to_md"]
