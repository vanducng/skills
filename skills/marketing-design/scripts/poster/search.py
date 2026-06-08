#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Poster Search — query poster CSVs by domain or build a design brief.

Usage:
    search.py --domain style --query "swiss minimal"
    search.py --domain palette --query "warm earthy"
    search.py --poster-brief --topic "AI Conference"
    search.py --domain layout --query "centered"
    search.py --domain texture --query "risograph"
"""

import argparse
import csv
import json
import random
import re
import sys
from collections import defaultdict
from math import log
from pathlib import Path

import core

DOMAIN_CSV = {
    "style": "poster-styles.csv",
    "palette": "poster-palettes.csv",
    "layout": "poster-layouts.csv",
    "texture": "poster-textures.csv",
}


def load_csv(domain: str) -> list[dict]:
    path = core.DATA_DIR / DOMAIN_CSV[domain]
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))


def tokenize(text: str) -> list[str]:
    return [w for w in re.sub(r"[^\w\s]", " ", str(text).lower()).split() if len(w) > 2]


def bm25_rank(rows: list[dict], query: str, search_cols: list[str], top_k: int = 5) -> list[dict]:
    """Lightweight BM25 over selected columns."""
    if not rows or not query:
        return rows[:top_k]
    docs = [" ".join(str(r.get(c, "")) for c in search_cols) for r in rows]
    tokens = [tokenize(d) for d in docs]
    N = len(tokens)
    avgdl = sum(len(t) for t in tokens) / max(N, 1)
    df: dict[str, int] = defaultdict(int)
    for doc in tokens:
        for term in set(doc):
            df[term] += 1
    idf = {t: log((N - f + 0.5) / (f + 0.5) + 1) for t, f in df.items()}
    q_tokens = tokenize(query)
    scored: list[tuple[int, float]] = []
    k1, b = 1.5, 0.75
    for i, doc in enumerate(tokens):
        score = 0.0
        dl = len(doc)
        tf: dict[str, int] = defaultdict(int)
        for w in doc:
            tf[w] += 1
        for qt in q_tokens:
            if qt in idf:
                num = tf[qt] * (k1 + 1)
                den = tf[qt] + k1 * (1 - b + b * dl / max(avgdl, 1))
                score += idf[qt] * num / max(den, 1e-9)
        scored.append((i, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [rows[i] for i, s in scored if s > 0][:top_k] or rows[:top_k]


SEARCH_COLS = {
    "style": ["Style Name", "Category", "Keywords", "Mood", "When To Use"],
    "palette": ["Palette Name", "Color Mood", "Pairs With Styles", "When To Use"],
    "layout": ["Layout Name", "Grid System", "Focal Anchor", "Best For Content"],
    "texture": ["Texture Name", "Material", "Grain/Finish", "Pairs With Styles"],
}


def build_brief(topic: str, query: str) -> dict:
    """Pick one row per domain to assemble a brief."""
    rng = random.Random(query + topic)
    out = {"topic": topic, "query": query}
    for domain in ("style", "palette", "layout", "texture"):
        rows = load_csv(domain)
        if not rows:
            continue
        ranked = bm25_rank(rows, query, SEARCH_COLS[domain], top_k=3) or rows[:3]
        out[domain] = rng.choice(ranked)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", choices=list(DOMAIN_CSV))
    parser.add_argument("--query", default="")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--poster-brief", action="store_true")
    parser.add_argument("--topic", default="")
    parser.add_argument("--json", action="store_true", help="output JSON")
    args = parser.parse_args()

    if args.poster_brief:
        brief = build_brief(args.topic, args.query)
        print(json.dumps(brief, indent=2, ensure_ascii=False))
        return 0

    if not args.domain:
        parser.error("--domain required when not using --poster-brief")
    rows = load_csv(args.domain)
    if not rows:
        print(f"no data in {DOMAIN_CSV[args.domain]}; run cluster.py first", file=sys.stderr)
        return 2
    results = bm25_rank(rows, args.query, SEARCH_COLS[args.domain], top_k=args.top)
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            print("---")
            for k, v in r.items():
                print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
