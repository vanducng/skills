#!/usr/bin/env python3
"""
OpenRouter image-gen client (vd:diagram skill).

Source: adapted from the local multimodal image-generation helper used before `vd:omnimedia`.
Intentional change: the `modalities` payload field is ALWAYS `["image", "text"]`,
not branched on `"gemini" in model`. Proof that `["image", "text"]` works for
`openai/gpt-5.4-image-2`: `skills/file-browser/scripts/generate-logo.cjs`.

Public API:
    find_api_key() -> str | None
    generate_image(prompt, output_path, model=DEFAULT_MODEL, ...) -> dict
"""
from __future__ import annotations

import base64
import os
import sys
from pathlib import Path
from typing import Any

import requests

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-5.4-image-2"

INSTALL_HINT = (
    "OPEN_ROUTER_KEY (or OPENROUTER_API_KEY) not set. "
    "Get a key at https://openrouter.ai/settings/keys, then `export OPEN_ROUTER_KEY=sk-or-v1-...`"
)


def find_api_key() -> str | None:
    return os.getenv("OPEN_ROUTER_KEY") or os.getenv("OPENROUTER_API_KEY")


def _get_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/vanducng/skills",
        "X-Title": "vd:diagram",
    }


def _build_payload(
    prompt: str,
    model: str,
    aspect_ratio: str | None,
    image_size: str | None,
    quality: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "modalities": ["image", "text"],
        "messages": [{"role": "user", "content": prompt}],
    }
    image_config: dict[str, Any] = {}
    if aspect_ratio:
        image_config["aspect_ratio"] = aspect_ratio
    if image_size:
        image_config["image_size"] = image_size
    if image_config:
        payload["image_config"] = image_config
    if quality:
        payload["quality"] = quality
    return payload


def _extract_image_bytes(image_url: str) -> bytes:
    if image_url.startswith("data:"):
        _, encoded = image_url.split(",", 1)
        return base64.b64decode(encoded)
    res = requests.get(image_url, timeout=120)
    res.raise_for_status()
    return res.content


def generate_image(
    prompt: str,
    output_path: str,
    model: str = DEFAULT_MODEL,
    aspect_ratio: str | None = None,
    quality: str | None = None,
    image_size: str | None = None,
    timeout: int = 180,
) -> dict[str, Any]:
    api_key = find_api_key()
    if not api_key:
        raise RuntimeError(INSTALL_HINT)

    payload = _build_payload(prompt, model, aspect_ratio, image_size, quality)
    res = requests.post(
        OPENROUTER_API_URL,
        headers=_get_headers(api_key),
        json=payload,
        timeout=timeout,
    )
    if not res.ok:
        raise RuntimeError(f"OpenRouter HTTP {res.status_code}: {res.text[:500]}")

    data = res.json()
    try:
        image_url = data["choices"][0]["message"]["images"][0]["image_url"]["url"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"No image in response: {str(data)[:500]}") from exc

    buf = _extract_image_bytes(image_url)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(buf)
    return {"path": str(out), "bytes": len(buf), "model": model}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: openrouter_image.py <prompt> <output_path>", file=sys.stderr)
        sys.exit(2)
    result = generate_image(sys.argv[1], sys.argv[2])
    print(result)
