#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Poster Prompt Generator — emit a text prompt for any image-gen model.

Axis selection:
- STYLE, PALETTE, TEXTURE are locked (style identity preserved).
- LAYOUT + variation seed (positions, shapes, density, rotation) are randomized
  per call, producing visibly different outputs in the same series.

Usage:
    generate.py --topic "AI Conference"
    generate.py --topic "AI Conference" --style style-03-swiss
    generate.py --topic "AI Conference" --lock-axis style,texture --seed 42
    generate.py --topic "AI Conference" --aspect a2
"""

import argparse
import csv
import random
import sys
from pathlib import Path

import core
import search as poster_search

ASPECT_HINTS = {
    "a2": "vertical A2 poster (420mm × 594mm, ~1:1.41)",
    "a3": "vertical A3 poster (297mm × 420mm, ~1:1.41)",
    "square": "1:1 square poster (1080×1080)",
    "landscape": "landscape 16:9 banner",
}

DENSITY_OPTIONS = ["sparse", "medium", "dense"]
POSITIONS = ["top-left", "top-center", "top-right",
             "center-left", "center", "center-right",
             "bottom-left", "bottom-center", "bottom-right"]


def pick_row(rows: list[dict], match_key: str, match_value: str, rng: random.Random) -> dict:
    """If match_value given, find row by name match; else random."""
    if match_value:
        for r in rows:
            if r.get(match_key, "").lower() == match_value.lower():
                return r
    return rng.choice(rows)


def filter_pairs(rows: list[dict], style_name: str, pairs_col: str) -> list[dict]:
    """Filter rows whose Pairs With Styles column contains style_name; fallback full set."""
    if not style_name:
        return rows
    matches = [r for r in rows if style_name.lower() in (r.get(pairs_col, "") or "").lower()]
    return matches or rows


def build_variation_seed(style_row: dict, layout_row: dict, rng: random.Random) -> dict:
    shape_pool = [s.strip() for s in (style_row.get("Shape Pool", "") or "").split(",") if s.strip()]
    if not shape_pool:
        shape_pool = ["circle", "thick rule", "rotated text block"]
    n_shapes = min(len(shape_pool), rng.randint(2, 4))
    return {
        "focal_position": layout_row.get("Focal Anchor") or rng.choice(POSITIONS),
        "secondary_positions": rng.sample(POSITIONS, k=min(3, len(POSITIONS))),
        "shape_set": rng.sample(shape_pool, k=n_shapes),
        "density": rng.choice(DENSITY_OPTIONS),
        "rotation_deg": rng.randint(-8, 8),
        "hierarchy_order": rng.sample(
            ["headline", "supporting graphic", "meta", "decorative shapes"],
            k=4,
        ),
    }


def render_prompt(topic: str, aspect: str, style: dict, palette: dict,
                  layout: dict, texture: dict, variation: dict) -> str:
    return f"""Design a {ASPECT_HINTS.get(aspect, aspect)} on the theme of "{topic}".

STYLE (locked — preserve identity exactly):
  Name: {style.get('Style Name')}
  Category: {style.get('Category')}
  Description: {style.get('Description')}
  Mood: {style.get('Mood')}
  Era: {style.get('Era')}
  Hints: {style.get('Hints')}

PALETTE (locked):
  Name: {palette.get('Palette Name')}
  Hex: {palette.get('Hex Colors')}
  Contrast: {palette.get('Contrast Level')}
  Mood: {palette.get('Color Mood')}

TEXTURE / MATERIAL (locked — must remain identical to source style):
  Material: {texture.get('Material')}
  Finish: {texture.get('Grain/Finish')}
  Effect: {texture.get('Effect Description')}
  Rendering: {texture.get('Rendering Hints')}

COMPOSITION (vary freely within style):
  Grid: {layout.get('Grid System')}
  Whitespace: {layout.get('Whitespace Ratio')}
  Element hierarchy: {' > '.join(variation['hierarchy_order'])}
  Focal anchor: {variation['focal_position']}
  Secondary element positions: {', '.join(variation['secondary_positions'])}
  Shape primitives to incorporate (2-4 only): {', '.join(variation['shape_set'])}
  Density: {variation['density']}
  Rotation jitter on secondary elements: {variation['rotation_deg']}°

COPY SLOTS:
  Headline: derive from topic — "{topic}"
  Sub: a short tagline that fits the mood
  Meta: date / venue / org placeholder text

CONSTRAINTS:
- Style, palette, and texture must remain visually identical to the locked specs above.
- Vary ONLY: layout grid usage, element positions, shape selection from the listed pool, density, rotation jitter.
- Do not invent textures/materials outside the locked set.
- Keep typography consistent with style description.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--aspect", default="a3", choices=list(ASPECT_HINTS) + ["custom"])
    parser.add_argument("--style", default="", help="exact Style Name to lock")
    parser.add_argument("--palette", default="")
    parser.add_argument("--layout", default="")
    parser.add_argument("--texture", default="")
    parser.add_argument("--query", default="", help="optional keyword query to filter style selection")
    parser.add_argument("--lock-axis", default="",
                        help="comma list of axes to lock when batching: style,palette,layout,texture")
    parser.add_argument("--seed", type=int, default=0, help="0 = random")
    args = parser.parse_args()

    seed = args.seed or random.randint(1, 2**31 - 1)
    rng = random.Random(seed)

    styles = poster_search.load_csv("style")
    palettes = poster_search.load_csv("palette")
    layouts = poster_search.load_csv("layout")
    textures = poster_search.load_csv("texture")
    if not (styles and palettes and layouts and textures):
        print("missing CSVs — run analyze.py then cluster.py first", file=sys.stderr)
        return 2

    if args.query and not args.style:
        ranked = poster_search.bm25_rank(styles, args.query,
                                         poster_search.SEARCH_COLS["style"], top_k=3)
        if ranked:
            styles_pool = ranked
        else:
            styles_pool = styles
    else:
        styles_pool = styles

    style = pick_row(styles_pool, "Style Name", args.style, rng)
    style_name = style.get("Style Name", "")

    palette = pick_row(filter_pairs(palettes, style_name, "Pairs With Styles"),
                       "Palette Name", args.palette, rng)
    layout = pick_row(layouts, "Layout Name", args.layout, rng)
    texture = pick_row(filter_pairs(textures, style_name, "Pairs With Styles"),
                       "Texture Name", args.texture, rng)

    variation = build_variation_seed(style, layout, rng)

    prompt = render_prompt(args.topic, args.aspect, style, palette, layout, texture, variation)
    print(f"# seed={seed} style={style_name} palette={palette.get('Palette Name')} "
          f"layout={layout.get('Layout Name')} texture={texture.get('Texture Name')}\n")
    print(prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
