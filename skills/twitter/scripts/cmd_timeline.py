"""`twitter timeline [home|latest|user:@handle]` — read your X timeline."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

from lib import formatters
from lib.twikit_client import get_client


async def _run(args: argparse.Namespace) -> int:
    kind = args.kind.lower()
    async with get_client() as client:
        if kind == "home":
            tweets = await client.get_timeline(count=args.count)
        elif kind == "latest":
            tweets = await client.get_latest_timeline(count=args.count)
        elif kind.startswith("user:"):
            handle = kind[len("user:") :].lstrip("@")
            user = await client.get_user_by_screen_name(handle)
            tweets = await client.get_user_tweets(user.id, "Tweets", count=args.count)
        else:
            print(f"twitter: unknown timeline kind: {args.kind!r}", file=sys.stderr)
            print("  valid: home | latest | user:@handle", file=sys.stderr)
            return 2

    items = list(tweets)
    if args.format == "json":
        print(json.dumps([formatters.tweet_to_dict(t) for t in items], indent=2, default=str))
    else:
        print(formatters.tweets_to_md(items))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="twitter timeline")
    p.add_argument("kind", nargs="?", default="latest", help="home | latest | user:@handle")
    p.add_argument("--count", type=int, default=20)
    p.add_argument("--format", choices=("json", "md"), default="md")
    args = p.parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
