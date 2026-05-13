"""`twitter post "text" [--media path...] [--long] [--community ID] [--share-with-followers]`."""
from __future__ import annotations

import argparse
import asyncio
import sys

from lib import media as media_lib
from lib.browser_fallback import post_browser
from lib.router import call_with_fallback
from lib.twikit_client import get_client


def _validate_text(text: str, long_flag: bool) -> str | None:
    if len(text) > 280 and not long_flag:
        return (
            f"text is {len(text)} chars (>280); add --long to post as a note "
            "tweet (requires X Premium)"
        )
    return None


async def _run(args: argparse.Namespace) -> int:
    err = _validate_text(args.text, args.long)
    if err:
        print(f"twitter post: {err}", file=sys.stderr)
        return 2

    async with get_client() as client:
        media_ids = await media_lib.upload(client, args.media) if args.media else None

        async def _twikit_post(text):
            return await client.create_tweet(
                text=text,
                media_ids=media_ids,
                reply_to=args.reply_to,
                community_id=args.community,
                is_note_tweet=args.long,
                share_with_followers=args.share_with_followers,
            )

        async def _browser_post(text):
            return await post_browser(text, media=args.media, reply_to=args.reply_to)

        try:
            tweet = await call_with_fallback(_twikit_post, _browser_post, args.text)
        except Exception as exc:
            msg = str(exc)
            if args.long and "premium" in msg.lower():
                print(
                    "twitter post: long tweets require X Premium on this account",
                    file=sys.stderr,
                )
                return 1
            raise
        screen = getattr(getattr(tweet, "user", None), "screen_name", None) or "i"
        print(tweet.id)
        print(f"https://x.com/{screen}/status/{tweet.id}")
        return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="twitter post")
    p.add_argument("text")
    p.add_argument("--media", action="append", default=[], help="path to a media file (repeatable)")
    p.add_argument("--reply-to", help="tweet ID to reply to")
    p.add_argument("--community", help="community ID to scope the post")
    p.add_argument("--long", action="store_true", help="post as a note tweet (Premium)")
    p.add_argument("--share-with-followers", action="store_true", help="share community post with followers")
    args = p.parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
