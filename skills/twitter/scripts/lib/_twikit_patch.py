"""Vendored fix for twikit 2.3.3's broken `ClientTransaction.init()`.

Upstream issue: https://github.com/d60/twikit/issues/408
Reference fix: iSarabjitDhiman/XClientTransaction@2ff84383

X rotated its main bundle so `ondemand.s` is no longer present as a top-level
key/value (`'ondemand.s':'<hash>'`). It now appears inside the manifest as
`,<N>:"ondemand.s"` and the hash is at a separate `,<N>:"<hex>"` token.
The minified variable names also widened (1 -> 1-2 chars), breaking
INDICES_REGEX. This module subclasses the original ClientTransaction with
new regexes + a two-step `get_indices`, then `apply()` monkey-patches it in.
"""
from __future__ import annotations

import re

from twikit.x_client_transaction import transaction as _twikit_t


ON_DEMAND_FILE_REGEX = re.compile(
    r""",(\d+):["']ondemand\.s["']""",
    flags=(re.VERBOSE | re.MULTILINE),
)
ON_DEMAND_HASH_PATTERN = r',{}:"([0-9a-f]+)"'
INDICES_REGEX = re.compile(
    r"""(\(\w{1,2}\[(\d{1,2})\],\s*16\))+""",
    flags=(re.VERBOSE | re.MULTILINE),
)


class PatchedClientTransaction(_twikit_t.ClientTransaction):
    """ClientTransaction with bundle-format-aware `get_indices`."""

    async def get_indices(self, home_page_response, session, headers):
        key_byte_indices: list[str] = []
        response = self.validate_response(
            home_page_response
        ) or self.home_page_response
        body = str(response)

        m = ON_DEMAND_FILE_REGEX.search(body)
        if not m:
            raise Exception(
                "Couldn't get KEY_BYTE indices: 'ondemand.s' marker not found "
                "(X may have rotated the bundle format again - refresh the patch)"
            )
        token_index = m.group(1)

        hash_re = re.compile(ON_DEMAND_HASH_PATTERN.format(token_index))
        h = hash_re.search(body)
        if not h:
            raise Exception(
                f"Couldn't get KEY_BYTE indices: hash for index {token_index} "
                "not found in bundle manifest"
            )
        bundle_hash = h.group(1)

        on_demand_file_url = (
            f"https://abs.twimg.com/responsive-web/client-web/"
            f"ondemand.s.{bundle_hash}a.js"
        )
        on_demand_file_response = await session.request(
            method="GET", url=on_demand_file_url, headers=headers
        )
        for item in INDICES_REGEX.finditer(str(on_demand_file_response.text)):
            key_byte_indices.append(item.group(2))

        if not key_byte_indices:
            raise Exception("Couldn't get KEY_BYTE indices")
        idx = list(map(int, key_byte_indices))
        return idx[0], idx[1:]


async def _patched_get_tweet_by_id(self, tweet_id: str, cursor=None):
    """Minimal replacement for `Client.get_tweet_by_id`.

    Upstream parses the reply-cursor via `entries[-1]['content']['itemContent']
    ['value']` which `KeyError`s on the current API shape (cursor lives at
    `entries[-1]['content']['items'][0]['item']['itemContent']['value']`).
    Skill only needs the target tweet, not the reply pagination, so walk the
    entries, build the tweet, attach reply_to / related_tweets, and skip the
    fragile cursor logic entirely.
    """
    from twikit.errors import TweetNotAvailable
    from twikit.utils import find_dict
    from twikit.tweet import tweet_from_data
    from twikit.utils import Result

    response, _ = await self.gql.tweet_detail(tweet_id, cursor)
    if "errors" in response:
        raise TweetNotAvailable(response["errors"][0]["message"])

    entries_match = find_dict(response, "entries", find_one=True)
    if not entries_match:
        raise TweetNotAvailable(f"no entries in response for tweet {tweet_id}")
    entries = entries_match[0]

    reply_to = []
    related_tweets = []
    replies_list = []
    tweet = None

    for entry in entries:
        entry_id = entry.get("entryId", "")
        if entry_id.startswith("cursor"):
            continue
        tweet_object = tweet_from_data(self, entry)
        if tweet_object is None:
            continue
        if entry_id.startswith("tweetdetailrelatedtweets"):
            related_tweets.append(tweet_object)
            continue
        if entry_id == f"tweet-{tweet_id}":
            tweet = tweet_object
        elif tweet is None:
            reply_to.append(tweet_object)
        else:
            replies_list.append(tweet_object)

    if tweet is None:
        raise TweetNotAvailable(f"tweet {tweet_id} not found in response")

    tweet.replies = Result(replies_list, None, None)
    tweet.reply_to = reply_to
    tweet.related_tweets = related_tweets
    return tweet


def _patched_user_init(self, client, data: dict) -> None:
    """Tolerant replacement for `twikit.user.User.__init__`.

    twikit 2.3.3 directly subscripts many `legacy[...]` keys that X has been
    migrating to a slimmer `core` shape, leading to `KeyError` on common
    accounts (e.g. `legacy['entities']['description']['urls']`). Mirror the
    original assignments but use `.get()` everywhere with sensible defaults.
    """
    import sys

    self._client = client
    legacy = data.get("legacy", {}) or {}
    entities = legacy.get("entities", {}) or {}
    desc_entity = entities.get("description") or {}
    url_entity = entities.get("url") or {}

    self.id = data.get("rest_id") or legacy.get("id_str")
    if not self.id:
        print(
            "twitter: User payload missing both rest_id and legacy.id_str - "
            "X may have changed the user shape; check upstream twikit",
            file=sys.stderr,
        )
    self.created_at = legacy.get("created_at")
    self.name = legacy.get("name")
    self.screen_name = legacy.get("screen_name")
    self.profile_image_url = legacy.get("profile_image_url_https")
    self.profile_banner_url = legacy.get("profile_banner_url")
    self.url = legacy.get("url")
    self.location = legacy.get("location")
    self.description = legacy.get("description")
    self.description_urls = desc_entity.get("urls", []) or []
    self.urls = url_entity.get("urls", []) or []
    self.pinned_tweet_ids = legacy.get("pinned_tweet_ids_str", []) or []
    self.is_blue_verified = data.get("is_blue_verified", False)
    self.verified = legacy.get("verified", False)
    self.possibly_sensitive = legacy.get("possibly_sensitive", False)
    self.can_dm = legacy.get("can_dm", False)
    self.can_media_tag = legacy.get("can_media_tag", False)
    self.want_retweets = legacy.get("want_retweets", False)
    self.default_profile = legacy.get("default_profile", False)
    self.default_profile_image = legacy.get("default_profile_image", False)
    self.has_custom_timelines = legacy.get("has_custom_timelines", False)
    self.followers_count = legacy.get("followers_count", 0)
    self.fast_followers_count = legacy.get("fast_followers_count", 0)
    self.normal_followers_count = legacy.get("normal_followers_count", 0)
    self.following_count = legacy.get("friends_count", 0)
    self.favourites_count = legacy.get("favourites_count", 0)
    self.listed_count = legacy.get("listed_count", 0)
    self.media_count = legacy.get("media_count", 0)
    self.statuses_count = legacy.get("statuses_count", 0)
    self.is_translator = legacy.get("is_translator", False)
    self.translator_type = legacy.get("translator_type")
    self.withheld_in_countries = legacy.get("withheld_in_countries", []) or []
    self.protected = legacy.get("protected", False)


_APPLIED = False


def apply() -> None:
    """Replace `ClientTransaction` everywhere twikit references it.

    Three sites need patching because `twikit.client.client` does
    `from ..x_client_transaction import ClientTransaction` at module-import
    time, binding its own reference. Idempotent.
    """
    global _APPLIED
    if _APPLIED:
        return
    _twikit_t.ClientTransaction = PatchedClientTransaction

    import twikit.x_client_transaction as _xct_pkg
    _xct_pkg.ClientTransaction = PatchedClientTransaction

    import twikit.client.client as _twikit_client
    _twikit_client.ClientTransaction = PatchedClientTransaction

    import twikit.user as _twikit_user
    _twikit_user.User.__init__ = _patched_user_init

    _twikit_client.Client.get_tweet_by_id = _patched_get_tweet_by_id

    _APPLIED = True


__all__ = [
    "PatchedClientTransaction",
    "ON_DEMAND_FILE_REGEX",
    "ON_DEMAND_HASH_PATTERN",
    "INDICES_REGEX",
    "apply",
]
