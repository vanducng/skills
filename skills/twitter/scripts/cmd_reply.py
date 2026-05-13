"""`twitter reply <url|id> "text" [--media path...]` — reply to a tweet."""
from __future__ import annotations

import argparse
import asyncio
import sys

from lib import media as media_lib
from lib.twikit_client import get_client
from lib.url_parser import parse_target


async def _run(args: argparse.Namespace) -> int:
    target = parse_target(args.target)
    if target.kind != "tweet":
        print(f"twitter reply: target must be a tweet URL or id, got {target.kind}", file=sys.stderr)
        return 2

    async with get_client() as client:
        media_ids = await media_lib.upload(client, args.media) if args.media else None
        tweet = await client.create_tweet(
            text=args.text,
            media_ids=media_ids,
            reply_to=target.value,
        )
        screen = getattr(getattr(tweet, "user", None), "screen_name", None) or "i"
        print(tweet.id)
        print(f"https://x.com/{screen}/status/{tweet.id}")
        return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="twitter reply")
    p.add_argument("target", help="tweet URL or numeric ID to reply to")
    p.add_argument("text")
    p.add_argument("--media", action="append", default=[], help="path to a media file (repeatable)")
    args = p.parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
