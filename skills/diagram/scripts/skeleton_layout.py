"""Layered LR layout for `--engine skeleton`.

One shared `layered_lr()` function. Per-type behavior comes from `TYPE_CONFIG`,
not type-specific code paths. Coordinates snap to a 20-px grid.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import yaml

from skeleton_schema import Skeleton

TYPE_CONFIG: dict[str, dict] = {
    "system-architecture": {
        "axis": "horizontal", "lane_dir": "lr",
        "node_w": 160, "node_h": 80,
        "lane_pad": 40, "node_gap": 32, "lane_gap": 80,
        "canvas_pad": 60,
    },
    "data-flow": {
        # Wider lane gap to fit transformation labels.
        "axis": "horizontal", "lane_dir": "lr",
        "node_w": 160, "node_h": 80,
        "lane_pad": 40, "node_gap": 32, "lane_gap": 100,
        "canvas_pad": 60,
    },
    "c4-context": {
        # Larger nodes — context diagrams have descriptive text.
        "axis": "horizontal", "lane_dir": "lr",
        "node_w": 200, "node_h": 100,
        "lane_pad": 48, "node_gap": 40, "lane_gap": 120,
        "canvas_pad": 80,
    },
    "c4-container": {
        # Containers grouped within a single system boundary.
        "axis": "horizontal", "lane_dir": "lr",
        "node_w": 180, "node_h": 90,
        "lane_pad": 40, "node_gap": 32, "lane_gap": 80,
        "canvas_pad": 60,
    },
    "er-diagram": {
        # Entities clustered by relationship density; lanes = clusters.
        "axis": "horizontal", "lane_dir": "lr",
        "node_w": 180, "node_h": 100,
        "lane_pad": 32, "node_gap": 24, "lane_gap": 96,
        "canvas_pad": 60,
    },
}


@dataclass
class LaidOut:
    skeleton: Skeleton
    canvas_w: int = 0
    canvas_h: int = 0
    nodes: dict[str, tuple[int, int, int, int]] = field(default_factory=dict)
    edges: list[dict] = field(default_factory=list)
    notes: list[dict] = field(default_factory=list)
    groups: dict[str, tuple[int, int, int, int]] = field(default_factory=dict)


def _snap(v: float) -> int:
    return int(round(v / 20) * 20)


def layered_lr(skel: Skeleton) -> LaidOut:
    """Compute coordinates for a layered LR diagram.

    Lanes = groups (in declaration order). Within a lane, elements stack
    vertically. Edges route as 3-segment orthogonals (or straight if same lane).
    """
    cfg = TYPE_CONFIG.get(skel.type)
    if cfg is None:
        raise ValueError(f"layered_lr does not support type {skel.type!r}; "
                         f"supported: {sorted(TYPE_CONFIG)}")
    nw, nh = cfg["node_w"], cfg["node_h"]
    pad, ngap, lgap, cpad = cfg["lane_pad"], cfg["node_gap"], cfg["lane_gap"], cfg["canvas_pad"]

    nodes: dict[str, tuple[int, int, int, int]] = {}
    groups_box: dict[str, tuple[int, int, int, int]] = {}
    lane_step = nw + 2 * pad + lgap
    max_lane_h = 0
    for li, group in enumerate(skel.groups):
        elems = [e for e in skel.elements if e.group == group.name]
        n_eff = max(len(elems), 1)
        lane_x = _snap(cpad + li * lane_step)
        lane_y = _snap(cpad)
        lane_w = _snap(nw + 2 * pad)
        lane_h = _snap(n_eff * nh + max(n_eff - 1, 0) * ngap + 2 * pad)
        groups_box[group.name] = (lane_x, lane_y, lane_w, lane_h)
        max_lane_h = max(max_lane_h, lane_y + lane_h)
        for ei, el in enumerate(elems):
            nodes[el.name] = (
                _snap(lane_x + pad), _snap(lane_y + pad + ei * (nh + ngap)),
                _snap(nw), _snap(nh),
            )

    canvas_w = _snap(cpad + len(skel.groups) * lane_step - lgap + cpad)
    canvas_h = _snap(max_lane_h + cpad)

    edges_out: list[dict] = []
    for edge in skel.edges:
        sx, sy, sw, sh = nodes[edge.from_]
        dx, dy, dw, dh = nodes[edge.to]
        if sx == dx:
            if sy < dy:
                wp = [(sx + sw // 2, sy + sh), (dx + dw // 2, dy)]
            else:
                wp = [(sx + sw // 2, sy), (dx + dw // 2, dy + dh)]
        else:
            if dx > sx:
                start, end = (sx + sw, sy + sh // 2), (dx, dy + dh // 2)
            else:
                start, end = (sx, sy + sh // 2), (dx + dw, dy + dh // 2)
            mid = (start[0] + end[0]) // 2
            wp = [start, (mid, start[1]), (mid, end[1]), end]
        edges_out.append({
            "from": edge.from_, "to": edge.to, "kind": edge.kind,
            "bidirectional": edge.bidirectional, "label": edge.label,
            "waypoints": wp, "label_xy": _label_xy(wp),
        })

    notes_out: list[dict] = []
    for note in skel.notes:
        ax, ay, aw, ah = nodes[note.attached]
        cx, cy = ax + aw // 2, ay + ah // 2
        xy = {
            "above": (cx, ay - 24),
            "below": (cx, ay + ah + 24),
            "left":  (ax - 24, cy),
            "right": (ax + aw + 24, cy),
        }[note.position]
        notes_out.append({
            "attached": note.attached, "position": note.position,
            "text": note.text, "xy": xy,
        })

    return LaidOut(skeleton=skel, canvas_w=canvas_w, canvas_h=canvas_h,
                   nodes=nodes, edges=edges_out, notes=notes_out, groups=groups_box)


def _label_xy(wp: list[tuple[int, int]]) -> tuple[int, int]:
    """Midpoint of the longest segment, offset 12 px above (horiz) or right (vert)."""
    best, best_len = (wp[0], wp[1]), 0
    for a, b in zip(wp, wp[1:]):
        ln = abs(b[0] - a[0]) + abs(b[1] - a[1])
        if ln > best_len:
            best_len, best = ln, (a, b)
    (ax, ay), (bx, by) = best
    return ((ax + bx) // 2, (ay + by) // 2 - 12) if ay == by else ((ax + bx) // 2 + 12, (ay + by) // 2)


def laid_out_to_yaml(lo: LaidOut) -> str:
    """Serialize LaidOut for pass-2 prompt. Compact, deterministic ordering."""
    skel = lo.skeleton
    data: dict = {"type": skel.type, "preset": skel.preset,
                  "canvas": {"w": lo.canvas_w, "h": lo.canvas_h}}
    if skel.title is not None:
        data["title"] = skel.title
    data["groups"] = [
        {"name": g.name, "label": g.label, "bbox": _bbox(lo.groups[g.name])}
        for g in skel.groups
    ]
    data["elements"] = []
    for e in skel.elements:
        item: dict = {"name": e.name, "kind": e.kind, "group": e.group,
                      "label": e.label, "bbox": _bbox(lo.nodes[e.name])}
        if e.subject:
            item["subject"] = True
        if e.note is not None:
            item["note"] = e.note
        data["elements"].append(item)
    data["edges"] = []
    for ed in lo.edges:
        item = {"from": ed["from"], "to": ed["to"], "kind": ed["kind"],
                "waypoints": [list(p) for p in ed["waypoints"]]}
        if ed["label"] is not None:
            item["label"], item["label_xy"] = ed["label"], list(ed["label_xy"])
        if ed["bidirectional"]:
            item["bidirectional"] = True
        data["edges"].append(item)
    if lo.notes:
        data["notes"] = [{"attached": n["attached"], "position": n["position"],
                          "text": n["text"], "xy": list(n["xy"])} for n in lo.notes]
    return yaml.safe_dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)


def _bbox(t: tuple[int, int, int, int]) -> dict:
    return {"x": t[0], "y": t[1], "w": t[2], "h": t[3]}
