#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Poster Analyzer — vision-extract structured design attributes from poster images.

Usage:
    analyze.py --input-dir /path/to/posters [--limit N] [--force] [--model MODEL]

Output: one JSON per image at data/poster/analysis/raw/{stem}.json with the
schema validated by core.validate_extraction.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import core

EXTRACTION_PROMPT = """You are analyzing a poster design for a knowledge base.
Extract ONLY the structured design attributes below. Output a SINGLE JSON object
with these exact keys. Do not add commentary.

{
  "image": "<the filename I will provide>",
  "style_cues": [3-6 short tags: e.g. "swiss", "grid", "high-contrast", "editorial"],
  "palette_hexes": [3-6 dominant hex colors including background and accents, format "#RRGGBB"],
  "layout": {
    "grid": "<grid descriptor e.g. '12-col asymmetric', 'centered stack', 'broken grid'>",
    "focal": "<focal anchor: 'top-left'|'top-right'|'center'|'bottom-left'|'bottom-right'|'full-bleed'>",
    "whitespace_ratio": "<'low'|'medium'|'high'>"
  },
  "texture": {
    "material": "<e.g. 'matte paper', 'glossy', 'risograph', 'newsprint', 'digital flat'>",
    "finish": "<e.g. 'halftone dots', 'paper grain', 'foil', 'gradient mesh', 'flat vector', 'photo collage'>"
  },
  "mood": [2-4 mood tags: e.g. "serious", "playful", "editorial", "energetic"],
  "shape_primitives": [3-6 shape primitives present: e.g. "circle", "thick rule", "rotated text block", "diagonal stripe", "triangle"],
  "typography": [2-4 typography descriptors: e.g. "geometric sans", "extreme size contrast", "all caps", "serif display"]
}

Be terse. Use lowercase tags. Match the lists exactly in cardinality."""


def analyze_image(client, image_path: Path, model: str) -> dict | None:
    """Run one extraction. Returns validated dict or None on failure."""
    try:
        uploaded = client.files.upload(file=str(image_path))
        response = client.models.generate_content(
            model=model,
            contents=[uploaded, EXTRACTION_PROMPT],
        )
    except Exception as exc:  # noqa: BLE001 — network errors are bounded
        print(f"  [err] {image_path.name}: {exc}", file=sys.stderr)
        return None

    text = (response.text or "").strip()
    # Strip code fences if model emitted them
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"  [err] {image_path.name}: bad json ({exc})", file=sys.stderr)
        return None

    data["image"] = image_path.name
    ok, reason = core.validate_extraction(data)
    if not ok:
        print(f"  [err] {image_path.name}: {reason}", file=sys.stderr)
        return None
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=0, help="0 = no limit")
    parser.add_argument("--force", action="store_true", help="re-analyze existing")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--sleep", type=float, default=0.25, help="seconds between calls")
    args = parser.parse_args()

    if not args.input_dir.exists():
        print(f"input dir not found: {args.input_dir}", file=sys.stderr)
        return 2

    images = core.iter_images(args.input_dir)
    if args.limit > 0:
        images = images[: args.limit]
    if not images:
        print("no images found", file=sys.stderr)
        return 2

    core.RAW_DIR.mkdir(parents=True, exist_ok=True)
    client = core.gemini_client()

    ok_count = 0
    skip_count = 0
    fail_count = 0
    for idx, img in enumerate(images, 1):
        out = core.RAW_DIR / f"{img.stem}.json"
        if out.exists() and not args.force:
            skip_count += 1
            continue
        print(f"[{idx}/{len(images)}] {img.name}")
        data = analyze_image(client, img, args.model)
        if data is None:
            fail_count += 1
        else:
            core.write_raw(img.name, data)
            ok_count += 1
        time.sleep(args.sleep)

    print(f"\nDone: ok={ok_count} skip={skip_count} fail={fail_count}")
    return 0 if fail_count == 0 or ok_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
