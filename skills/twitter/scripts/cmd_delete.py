"""`twitter delete <url|id>` — delete a tweet."""
from __future__ import annotations

import argparse
import asyncio
import sys

from lib.twikit_client import get_client
from lib.url_parser import parse_target


async def _run(args: argparse.Namespace) -> int:
    target = parse_target(args.target)
    if target.kind != "tweet":
        print(f"twitter delete: target must be a tweet URL or id, got {target.kind}", file=sys.stderr)
        return 2
    async with get_client() as client:
        await client.delete_tweet(target.value)
        print(f"deleted {target.value}")
        return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="twitter delete")
    p.add_argument("target", help="tweet URL or numeric ID")
    args = p.parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
