"""Media upload helper for the twitter skill.

Wraps `twikit.Client.upload_media` with size + mime validation. X's caps
(image 5 MB, gif 15 MB, video 512 MB) come from the public help-center
page; mirror them here to fail fast before the round-trip.
"""
from __future__ import annotations

import mimetypes
from pathlib import Path

_IMAGE_MAX = 5 * 1024 * 1024
_GIF_MAX = 15 * 1024 * 1024
_VIDEO_MAX = 512 * 1024 * 1024
_LONG_VIDEO_THRESHOLD = 140 * 1024 * 1024


class MediaTooLarge(ValueError):
    pass


class MediaUnsupported(ValueError):
    pass


def _classify(path: Path) -> tuple[str, int]:
    """Return (kind, max_bytes) for a media path. kind ∈ {image, gif, video}."""
    mime, _ = mimetypes.guess_type(str(path))
    if mime is None:
        raise MediaUnsupported(f"could not determine mime for {path}")
    if mime == "image/gif":
        return "gif", _GIF_MAX
    if mime.startswith("image/"):
        return "image", _IMAGE_MAX
    if mime.startswith("video/"):
        return "video", _VIDEO_MAX
    raise MediaUnsupported(f"unsupported mime {mime} for {path}")


async def upload(client, paths: list[str | Path]) -> list[str]:
    """Validate + upload each path; return the list of media IDs (in order)."""
    ids: list[str] = []
    for raw in paths:
        path = Path(raw).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"media not found: {raw}")
        kind, cap = _classify(path)
        size = path.stat().st_size
        if size > cap:
            raise MediaTooLarge(
                f"{path.name} is {size} bytes; cap for {kind} is {cap}"
            )
        kwargs: dict = {}
        if kind == "video":
            kwargs["media_category"] = "tweet_video"
            kwargs["wait_for_completion"] = True
            if size > _LONG_VIDEO_THRESHOLD:
                kwargs["is_long_video"] = True
        media_id = await client.upload_media(str(path), **kwargs)
        ids.append(media_id)
    return ids


__all__ = ["upload", "MediaTooLarge", "MediaUnsupported"]
