#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Poster Clusterer — consume raw extraction JSONs, cluster on 4 axes,
synthesize curated rows via Gemini text, emit 4 CSVs.

Usage:
    cluster.py [--max-styles 30] [--seed 42] [--skip-synthesis]

Outputs:
    data/poster/poster-styles.csv
    data/poster/poster-palettes.csv
    data/poster/poster-layouts.csv
    data/poster/poster-textures.csv
    data/poster/analysis/clusters.json   (audit trail)
"""

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import core

# ---------- vector encoding ----------

def _ratio_score(value: str) -> float:
    return {"low": 0.2, "medium": 0.5, "high": 0.8}.get(value, 0.5)


def encode_style_vector(item: dict, vocab: dict[str, int]) -> list[float]:
    """One-hot over style_cues + mood + typography vocab."""
    vec = [0.0] * len(vocab)
    for key in ("style_cues", "mood", "typography"):
        for tag in item.get(key, []):
            idx = vocab.get(tag.lower())
            if idx is not None:
                vec[idx] = 1.0
    return vec


def build_vocab(items: list[dict]) -> dict[str, int]:
    counter: Counter = Counter()
    for item in items:
        for key in ("style_cues", "mood", "typography"):
            counter.update(t.lower() for t in item.get(key, []))
    # Keep tags appearing in >=2 images to suppress noise
    kept = sorted(t for t, c in counter.items() if c >= 2)
    return {t: i for i, t in enumerate(kept)}


# ---------- clustering ----------

def cluster_styles(items: list[dict], max_k: int, seed: int) -> list[list[dict]]:
    """K-means over attribute vectors. K chosen by silhouette in [8, max_k]."""
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    vocab = build_vocab(items)
    if not vocab:
        return [items]
    X = np.array([encode_style_vector(it, vocab) for it in items])
    n = len(items)
    best_k, best_score, best_labels = 8, -1.0, None
    upper = min(max_k, max(8, n // 4))
    for k in range(8, upper + 1):
        if k >= n:
            break
        km = KMeans(n_clusters=k, n_init=10, random_state=seed)
        labels = km.fit_predict(X)
        if len(set(labels)) < 2:
            continue
        try:
            score = silhouette_score(X, labels)
        except ValueError:
            continue
        if score > best_score:
            best_k, best_score, best_labels = k, score, labels

    if best_labels is None:
        return [items]
    groups: dict[int, list[dict]] = defaultdict(list)
    for label, item in zip(best_labels, items):
        groups[int(label)].append(item)
    # Drop singletons, merge into nearest cluster by attribute overlap
    final: list[list[dict]] = []
    orphans: list[dict] = []
    for grp in groups.values():
        if len(grp) >= 2:
            final.append(grp)
        else:
            orphans.extend(grp)
    for orphan in orphans:
        best_idx, best_overlap = 0, -1
        ov = set(orphan.get("style_cues", []))
        for i, grp in enumerate(final):
            grp_tags = {t for it in grp for t in it.get("style_cues", [])}
            overlap = len(ov & grp_tags)
            if overlap > best_overlap:
                best_overlap, best_idx = overlap, i
        if final:
            final[best_idx].append(orphan)
        else:
            final.append([orphan])
    return final


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _color_distance(a: str, b: str) -> float:
    ra, ga, ba = _hex_to_rgb(a)
    rb, gb, bb_ = _hex_to_rgb(b)
    return ((ra - rb) ** 2 + (ga - gb) ** 2 + (ba - bb_) ** 2) ** 0.5


def cluster_palettes(items: list[dict], seed: int) -> list[list[dict]]:
    """Group items by palette signature: sorted dominant hexes bucketed."""
    import numpy as np
    from sklearn.cluster import KMeans

    # Each item's palette → averaged RGB centroid
    rows = []
    for it in items:
        rgbs = []
        for h in it.get("palette_hexes", []):
            try:
                rgbs.append(_hex_to_rgb(h))
            except (ValueError, IndexError):
                continue
        if rgbs:
            avg = [sum(c) / len(rgbs) for c in zip(*rgbs)]
            rows.append((it, avg))
    if not rows:
        return []
    X = [r[1] for r in rows]
    k = min(18, max(8, len(rows) // 6))
    km = KMeans(n_clusters=k, n_init=10, random_state=seed)
    labels = km.fit_predict(X)
    groups: dict[int, list[dict]] = defaultdict(list)
    for label, (item, _) in zip(labels, rows):
        groups[int(label)].append(item)
    return [g for g in groups.values() if len(g) >= 2]


def cluster_layouts(items: list[dict]) -> list[list[dict]]:
    """Group by (focal, whitespace, grid-bucket) signature."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for it in items:
        layout = it.get("layout", {})
        grid_key = (layout.get("grid", "") or "").split()[0].lower() or "unknown"
        sig = (
            layout.get("focal", "unknown"),
            layout.get("whitespace_ratio", "medium"),
            grid_key,
        )
        groups[sig].append(it)
    return sorted([g for g in groups.values() if len(g) >= 2], key=len, reverse=True)[:14]


def cluster_textures(items: list[dict]) -> list[list[dict]]:
    """Group by (material, finish) pair."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    def _flat(v):
        if isinstance(v, list):
            return ", ".join(str(x) for x in v) or "unknown"
        return str(v) if v else "unknown"
    for it in items:
        tx = it.get("texture", {}) or {}
        sig = (_flat(tx.get("material")), _flat(tx.get("finish")))
        groups[sig].append(it)
    return sorted([g for g in groups.values() if len(g) >= 2], key=len, reverse=True)[:12]


# ---------- synthesis ----------

SYNTH_PROMPT = """You are summarizing a cluster of poster designs into ONE curated style row.
Given these member-image attribute snapshots:

{snapshots}

Output JSON with EXACT keys:
{{
  "name": "<short kebab-case style name, e.g. 'swiss-editorial', 'risograph-pop'>",
  "category": "<broad category: 'editorial'|'expressive'|'minimal'|'retro'|'experimental'>",
  "keywords": "<6-10 comma-separated keywords>",
  "mood": "<3-5 comma-separated moods>",
  "description": "<one rich sentence describing the style>",
  "specs": "<typographic + layout specs in one sentence>",
  "when_to_use": "<one sentence: ideal use cases>",
  "avoid_for": "<one sentence: where it fails>",
  "hints": "<one sentence of design hints for the prompt>",
  "recommendations": "<one sentence of model/render recommendations>",
  "era": "<e.g. '2010s-Present', 'Classic', '1960s-70s'>"
}}
No commentary. JSON only."""


def synthesize_style_row(client, members: list[dict], model: str) -> dict:
    snapshots = "\n".join(
        f"- cues={m.get('style_cues')}, mood={m.get('mood')}, type={m.get('typography')}"
        for m in members[:6]
    )
    prompt = SYNTH_PROMPT.format(snapshots=snapshots)
    resp = client.models.generate_content(model=model, contents=prompt)
    text = (resp.text or "").strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


# ---------- CSV writers ----------

def write_styles_csv(rows: list[dict], path: Path) -> None:
    cols = [
        "No", "Style Name", "Category", "Keywords", "Mood", "Description",
        "Specs", "Shape Pool", "When To Use", "Avoid For", "Hints",
        "Recommendations", "Era",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for i, r in enumerate(rows, 1):
            w.writerow([
                i, r["name"], r["category"], r["keywords"], r["mood"],
                r["description"], r["specs"], r["shape_pool"],
                r["when_to_use"], r["avoid_for"], r["hints"],
                r["recommendations"], r["era"],
            ])


def write_palettes_csv(rows: list[dict], path: Path) -> None:
    cols = ["No", "Palette Name", "Hex Colors", "Color Mood", "Contrast Level",
            "Pairs With Styles", "When To Use"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for i, r in enumerate(rows, 1):
            w.writerow([i, r["name"], r["hex_colors"], r["mood"],
                        r["contrast"], r["pairs_with"], r["when_to_use"]])


def write_layouts_csv(rows: list[dict], path: Path) -> None:
    cols = ["No", "Layout Name", "Grid System", "Focal Anchor",
            "Element Hierarchy", "Whitespace Ratio", "Best For Content"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for i, r in enumerate(rows, 1):
            w.writerow([i, r["name"], r["grid"], r["focal"],
                        r["hierarchy"], r["whitespace"], r["best_for"]])


def write_textures_csv(rows: list[dict], path: Path) -> None:
    cols = ["No", "Texture Name", "Material", "Grain/Finish",
            "Effect Description", "Pairs With Styles", "Rendering Hints"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for i, r in enumerate(rows, 1):
            w.writerow([i, r["name"], r["material"], r["finish"],
                        r["effect"], r["pairs_with"], r["rendering"]])


# ---------- main orchestration ----------

def aggregate_shapes(members: list[dict]) -> str:
    pool: Counter = Counter()
    for m in members:
        for s in m.get("shape_primitives", []):
            pool[s.lower()] += 1
    return ", ".join(s for s, _ in pool.most_common(8))


def build_palette_row(idx: int, members: list[dict]) -> dict:
    # Pick the most common hexes across members (top 5)
    hex_counter: Counter = Counter()
    for m in members:
        for h in m.get("palette_hexes", []):
            hex_counter[h.upper()] += 1
    top_hexes = [h for h, _ in hex_counter.most_common(5)]
    moods = Counter(t for m in members for t in m.get("mood", []))
    top_mood = ", ".join(t for t, _ in moods.most_common(3))
    # Contrast heuristic: max RGB distance among top 2 hexes
    contrast = "medium"
    if len(top_hexes) >= 2:
        d = _color_distance(top_hexes[0], top_hexes[1])
        contrast = "high" if d > 220 else "low" if d < 100 else "medium"
    return {
        "name": f"palette-{idx:02d}",
        "hex_colors": " ".join(top_hexes),
        "mood": top_mood or "neutral",
        "contrast": contrast,
        "pairs_with": "",  # filled in pair_axes
        "when_to_use": f"When the {top_mood or 'neutral'} mood suits the message.",
    }


def build_layout_row(idx: int, members: list[dict]) -> dict:
    sample = members[0].get("layout", {})
    cues = Counter(t for m in members for t in m.get("style_cues", []))
    best_for = ", ".join(t for t, _ in cues.most_common(4))
    return {
        "name": f"layout-{idx:02d}",
        "grid": sample.get("grid", ""),
        "focal": sample.get("focal", ""),
        "hierarchy": "headline > supporting graphic > meta",
        "whitespace": sample.get("whitespace_ratio", "medium"),
        "best_for": best_for,
    }


def build_texture_row(idx: int, members: list[dict]) -> dict:
    sample = members[0].get("texture", {})
    return {
        "name": f"texture-{idx:02d}-{sample.get('material', '').replace(' ', '-')}",
        "material": sample.get("material", ""),
        "finish": sample.get("finish", ""),
        "effect": f"{sample.get('material', '')} surface with {sample.get('finish', '')} finish",
        "pairs_with": "",
        "rendering": f"Render with visible {sample.get('finish', '')} texture; preserve {sample.get('material', '')} qualities.",
    }


def pair_axes(style_rows: list[dict], style_clusters: list[list[dict]],
              palettes: list[dict], textures: list[dict],
              palette_clusters: list[list[dict]],
              texture_clusters: list[list[dict]]) -> None:
    """Fill pairs_with on palettes/textures by co-occurrence in source images."""
    img_to_style = {}
    for srow, members in zip(style_rows, style_clusters):
        for m in members:
            img_to_style[m["image"]] = srow["name"]

    for prow, pmembers in zip(palettes, palette_clusters):
        styles = Counter(img_to_style.get(m["image"]) for m in pmembers if img_to_style.get(m["image"]))
        prow["pairs_with"] = ", ".join(s for s, _ in styles.most_common(4)) or "any"

    for trow, tmembers in zip(textures, texture_clusters):
        styles = Counter(img_to_style.get(m["image"]) for m in tmembers if img_to_style.get(m["image"]))
        trow["pairs_with"] = ", ".join(s for s, _ in styles.most_common(4)) or "any"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-styles", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--skip-synthesis", action="store_true",
                        help="Use heuristic style rows without Gemini synthesis")
    args = parser.parse_args()

    items = core.load_all_raw()
    if len(items) < 10:
        print(f"too few raw items ({len(items)}); run analyze.py first", file=sys.stderr)
        return 2
    print(f"Loaded {len(items)} extractions")

    style_clusters = cluster_styles(items, args.max_styles, args.seed)
    palette_clusters = cluster_palettes(items, args.seed)
    layout_clusters = cluster_layouts(items)
    texture_clusters = cluster_textures(items)
    print(f"Clusters: styles={len(style_clusters)} palettes={len(palette_clusters)} "
          f"layouts={len(layout_clusters)} textures={len(texture_clusters)}")

    client = None if args.skip_synthesis else core.gemini_client()
    style_rows: list[dict] = []
    for i, members in enumerate(style_clusters, 1):
        if client:
            try:
                row = synthesize_style_row(client, members, args.model)
            except Exception as exc:  # noqa: BLE001
                print(f"  [warn] cluster {i} synthesis failed ({exc}); using heuristic", file=sys.stderr)
                row = None
        else:
            row = None
        if row is None:
            cues = Counter(t for m in members for t in m.get("style_cues", []))
            top_cues = [t for t, _ in cues.most_common(5)]
            row = {
                "name": f"style-{i:02d}-{(top_cues[0] if top_cues else 'mixed').replace(' ', '-')}",
                "category": "editorial",
                "keywords": ", ".join(top_cues),
                "mood": ", ".join(t for t, _ in Counter(t for m in members for t in m.get("mood", [])).most_common(3)),
                "description": f"Cluster of {len(members)} posters sharing {', '.join(top_cues[:3])}.",
                "specs": "geometric sans, strong hierarchy",
                "when_to_use": "When evoking the cluster's dominant mood.",
                "avoid_for": "When mood contradicts brief.",
                "hints": "Lock palette + texture; vary layout.",
                "recommendations": "Gemini Nano Banana 2 for fast iteration.",
                "era": "2010s-Present",
            }
        row["shape_pool"] = aggregate_shapes(members)
        style_rows.append(row)
        print(f"  style {i:02d}: {row['name']} ({len(members)} members)")

    palette_rows = [build_palette_row(i, m) for i, m in enumerate(palette_clusters, 1)]
    layout_rows = [build_layout_row(i, m) for i, m in enumerate(layout_clusters, 1)]
    texture_rows = [build_texture_row(i, m) for i, m in enumerate(texture_clusters, 1)]

    pair_axes(style_rows, style_clusters, palette_rows, texture_rows,
              palette_clusters, texture_clusters)

    core.DATA_DIR.mkdir(parents=True, exist_ok=True)
    write_styles_csv(style_rows, core.DATA_DIR / "poster-styles.csv")
    write_palettes_csv(palette_rows, core.DATA_DIR / "poster-palettes.csv")
    write_layouts_csv(layout_rows, core.DATA_DIR / "poster-layouts.csv")
    write_textures_csv(texture_rows, core.DATA_DIR / "poster-textures.csv")

    audit = {
        "seed": args.seed,
        "style_clusters": [[m["image"] for m in g] for g in style_clusters],
        "palette_clusters": [[m["image"] for m in g] for g in palette_clusters],
        "layout_clusters": [[m["image"] for m in g] for g in layout_clusters],
        "texture_clusters": [[m["image"] for m in g] for g in texture_clusters],
    }
    core.CLUSTERS_AUDIT.write_text(json.dumps(audit, indent=2))

    print(f"\nWrote 4 CSVs to {core.DATA_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
