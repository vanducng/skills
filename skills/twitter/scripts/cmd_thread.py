"""`twitter thread "a" "b" "c"` - post a chained thread.

Each tweet replies to the previous. On mid-thread failure, prints the IDs
already posted so the user can resume manually (we never auto-delete).
"""
from __future__ import annotations

import argparse
import asyncio
import sys


from lib.twikit_client import get_client


async def _run(args: argparse.Namespace) -> int:
    if not args.texts:
        print("twitter thread: need at least one text", file=sys.stderr)
        return 2

    posted: list[str] = []
    async with get_client() as client:
        prev_id: str | None = None
        for i, text in enumerate(args.texts, start=1):
            try:
                tweet = await client.create_tweet(text=text, reply_to=prev_id)
            except Exception as exc:
                print(f"twitter thread: failed at tweet #{i}: {exc}", file=sys.stderr)
                if posted:
                    print("posted so far (not auto-deleted):", file=sys.stderr)
                    for tid in posted:
                        print(f"  {tid}", file=sys.stderr)
                return 1
            posted.append(tweet.id)
            prev_id = tweet.id
            print(tweet.id)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="twitter thread")
    p.add_argument("texts", nargs="+", help="one positional per tweet, in order")
    args = p.parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
