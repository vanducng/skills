"""`twitter fetch <url|@user|search:...>` - read tweets, user feeds, or search."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

from lib import formatters
from lib.browser_fallback import fetch_browser
from lib.router import call_with_fallback
from lib.twikit_client import get_client
from lib.url_parser import parse_target


def _emit(items, fmt: str) -> None:
    if fmt == "json":
        if isinstance(items, list):
            payload = [formatters.tweet_to_dict(t) for t in items]
        elif isinstance(items, dict):
            payload = items
        else:
            payload = formatters.tweet_to_dict(items)
        print(json.dumps(payload, indent=2, default=str))
    else:
        if isinstance(items, list):
            print(formatters.tweets_to_md(items))
        elif isinstance(items, dict):
            handle = (items.get("author") or {}).get("screen_name") or "unknown"
            print(f"**@{handle}**\n\n{items.get('text','').strip()}")
        else:
            print(formatters.tweet_to_md(items))


async def _run(args: argparse.Namespace) -> int:
    target = parse_target(args.target)
    async with get_client() as client:
        if target.kind == "tweet":
            async def _twikit_fetch(tgt):
                return await client.get_tweet_by_id(tgt.value)

            async def _browser_fetch(tgt):
                return await fetch_browser(tgt)

            t = await call_with_fallback(_twikit_fetch, _browser_fetch, target)
            _emit(t, args.format)
            return 0
        if target.kind == "user":
            user = await client.get_user_by_screen_name(target.value)
            tweets = await client.get_user_tweets(user.id, "Tweets", count=args.count)
            _emit(list(tweets), args.format)
            return 0
        if target.kind == "search":
            results = await client.search_tweet(target.value, "Latest", count=args.count)
            _emit(list(results), args.format)
            return 0
    return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="twitter fetch")
    p.add_argument("target", help="tweet URL, @handle, numeric ID, or 'search:<query>'")
    p.add_argument("--count", type=int, default=20, help="result count for user/search (default 20)")
    p.add_argument("--format", choices=("json", "md"), default="md")
    args = p.parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
