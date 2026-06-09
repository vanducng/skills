#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Poster Design Core - shared utilities for analyze/cluster/search/generate.

Responsibilities:
- Env loading (GEMINI_API_KEY) following same priority order as logo/.
- Gemini client factory (vision + text).
- JSON schema validator for extraction outputs.
- CSV writer with deterministic ordering.
- Path helpers anchored at design skill root.
"""

import json
import os
from pathlib import Path
from typing import Iterable

SKILL_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = SKILL_ROOT / "data" / "poster"
RAW_DIR = DATA_DIR / "analysis" / "raw"
CLUSTERS_AUDIT = DATA_DIR / "analysis" / "clusters.json"

EXTRACTION_REQUIRED_KEYS = {
    "image",
    "style_cues",
    "palette_hexes",
    "layout",
    "texture",
    "mood",
    "shape_primitives",
    "typography",
}

LAYOUT_REQUIRED_KEYS = {"grid", "focal", "whitespace_ratio"}
TEXTURE_REQUIRED_KEYS = {"material", "finish"}


def load_env() -> None:
    """Load .env in priority order: project → skills → home. Idempotent."""
    candidates = [
        SKILL_ROOT.parent.parent / ".env",
        Path.home() / ".claude" / "skills" / ".env",
        Path.home() / ".claude" / ".env",
    ]
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def get_api_key() -> str:
    """Return GEMINI_API_KEY, raising with actionable message if missing."""
    load_env()
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Add to ~/.claude/.env or project .env."
        )
    return key


def gemini_client():
    """Return a google-genai Client configured with API key."""
    from google import genai

    return genai.Client(api_key=get_api_key())


def validate_extraction(data: dict) -> tuple[bool, str]:
    """Strict validate that an extraction JSON has all required keys."""
    if not isinstance(data, dict):
        return False, "not a dict"
    missing = EXTRACTION_REQUIRED_KEYS - set(data.keys())
    if missing:
        return False, f"missing keys: {sorted(missing)}"
    if not isinstance(data.get("layout"), dict):
        return False, "layout must be dict"
    if LAYOUT_REQUIRED_KEYS - set(data["layout"].keys()):
        return False, f"layout missing: {LAYOUT_REQUIRED_KEYS - set(data['layout'].keys())}"
    if not isinstance(data.get("texture"), dict):
        return False, "texture must be dict"
    if TEXTURE_REQUIRED_KEYS - set(data["texture"].keys()):
        return False, "texture missing material/finish"
    for list_key in ("style_cues", "palette_hexes", "mood", "shape_primitives", "typography"):
        if not isinstance(data.get(list_key), list):
            return False, f"{list_key} must be list"
    return True, ""


def write_raw(image_name: str, payload: dict) -> Path:
    """Write extraction JSON to RAW_DIR keyed by image filename stem."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / f"{Path(image_name).stem}.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    return out


def load_all_raw() -> list[dict]:
    """Load every valid raw extraction JSON; skip invalid ones with warning."""
    if not RAW_DIR.exists():
        return []
    items: list[dict] = []
    for path in sorted(RAW_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        ok, _ = validate_extraction(data)
        if ok:
            items.append(data)
    return items


def iter_images(input_dir: Path, exts: Iterable[str] = (".jpg", ".jpeg", ".png")) -> list[Path]:
    """Sorted list of image files in input_dir filtered by extension."""
    return sorted(p for p in input_dir.iterdir() if p.suffix.lower() in exts)
