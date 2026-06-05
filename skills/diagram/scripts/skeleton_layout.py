"""Deterministic layouts for `--engine skeleton`.

`layered_lr()` is the public entry point kept for CLI compatibility. Most
diagram types use group columns. Workflow diagrams use horizontal swimlanes so
process ownership reads top-to-bottom while time still flows left-to-right.
Coordinates snap to a 20-px grid.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict, deque

import yaml

from skeleton_schema import Element, Skeleton

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
    "workflow": {
        # Swimlane-friendly process maps: groups are horizontal ownership rows.
        "layout": "swimlane_rows", "axis": "horizontal", "lane_dir": "tb",
        "node_w": 180, "node_h": 80,
        "lane_pad_x": 40, "lane_pad_y": 32,
        "node_gap": 120, "lane_gap": 28,
        "lane_label_w": 180,
        "canvas_pad": 40,
        "title_h": 80,
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
    group_labels: dict[str, tuple[int, int, int, int]] = field(default_factory=dict)
    steps: dict[str, int] = field(default_factory=dict)
    layout_style: str = "group-columns"


def _snap(v: float) -> int:
    return int(round(v / 20) * 20)


def layered_lr(skel: Skeleton) -> LaidOut:
    """Compute coordinates for a skeleton diagram.

    Column layouts keep groups left-to-right and stack elements vertically.
    Workflow layouts render groups as horizontal swimlanes and place steps
    left-to-right by dependency rank.
    """
    cfg = TYPE_CONFIG.get(skel.type)
    if cfg is None:
        raise ValueError(f"layered_lr does not support type {skel.type!r}; "
                         f"supported: {sorted(TYPE_CONFIG)}")
    if cfg.get("layout") == "swimlane_rows":
        return _swimlane_rows(skel, cfg)
    return _group_columns(skel, cfg)


def _group_columns(skel: Skeleton, cfg: dict) -> LaidOut:
    """Classic layout: each group is a vertical column."""
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

    return LaidOut(skeleton=skel, canvas_w=canvas_w, canvas_h=canvas_h,
                   nodes=nodes, edges=_route_edges(skel, nodes),
                   notes=_layout_notes(skel, nodes), groups=groups_box)


def _swimlane_rows(skel: Skeleton, cfg: dict) -> LaidOut:
    """Workflow layout: groups are horizontal swimlanes, steps flow left-to-right."""
    nw, nh = cfg["node_w"], cfg["node_h"]
    pad_x, pad_y = cfg["lane_pad_x"], cfg["lane_pad_y"]
    ngap, lgap, cpad = cfg["node_gap"], cfg["lane_gap"], cfg["canvas_pad"]
    label_w, title_h = cfg["lane_label_w"], cfg["title_h"]

    columns = _workflow_columns(skel)
    max_col = max(columns.values(), default=0)
    lane_h = _snap(nh + 2 * pad_y)
    content_w = _snap((max_col + 1) * nw + max_col * ngap)
    lane_w = _snap(label_w + 2 * pad_x + content_w)
    y0 = _snap(cpad + (title_h if skel.title else 0))

    nodes: dict[str, tuple[int, int, int, int]] = {}
    groups_box: dict[str, tuple[int, int, int, int]] = {}
    group_labels: dict[str, tuple[int, int, int, int]] = {}
    for li, group in enumerate(skel.groups):
        lane_x = _snap(cpad)
        lane_y = _snap(y0 + li * (lane_h + lgap))
        groups_box[group.name] = (lane_x, lane_y, lane_w, lane_h)
        group_labels[group.name] = (lane_x, lane_y, _snap(label_w), lane_h)
        for el in _elements_for_group(skel, group.name):
            col = columns[el.name]
            nodes[el.name] = (
                _snap(lane_x + label_w + pad_x + col * (nw + ngap)),
                _snap(lane_y + pad_y),
                _snap(nw),
                _snap(nh),
            )

    ordered = sorted(
        skel.elements,
        key=lambda e: (nodes[e.name][0], nodes[e.name][1], _element_order(skel)[e.name]),
    )
    steps = {el.name: i + 1 for i, el in enumerate(ordered)}
    canvas_w = _snap(cpad + lane_w + cpad)
    canvas_h = _snap(y0 + len(skel.groups) * lane_h + max(len(skel.groups) - 1, 0) * lgap + cpad)
    return LaidOut(
        skeleton=skel, canvas_w=canvas_w, canvas_h=canvas_h,
        nodes=nodes, edges=_route_edges(skel, nodes, same_column_vertical=False),
        notes=_layout_notes(skel, nodes), groups=groups_box,
        group_labels=group_labels, steps=steps, layout_style="workflow-swimlanes",
    )


def _workflow_columns(skel: Skeleton) -> dict[str, int]:
    """Assign stable left-to-right columns from dependency rank and lane order."""
    ranks = _dependency_ranks(skel)
    order = _element_order(skel)
    columns: dict[str, int] = {}
    for group in skel.groups:
        prev = -1
        elems = sorted(
            _elements_for_group(skel, group.name),
            key=lambda e: (ranks.get(e.name, order[e.name]), order[e.name]),
        )
        for el in elems:
            col = max(ranks.get(el.name, 0), prev + 1)
            columns[el.name] = col
            prev = col
    return columns


def _dependency_ranks(skel: Skeleton) -> dict[str, int]:
    """Longest-path ranks for acyclic portions; declaration order fallback for loops."""
    order = _element_order(skel)
    outgoing: dict[str, list[str]] = defaultdict(list)
    indegree: dict[str, int] = {el.name: 0 for el in skel.elements}
    for edge in skel.edges:
        outgoing[edge.from_].append(edge.to)
        indegree[edge.to] = indegree.get(edge.to, 0) + 1

    queue = deque(sorted((name for name, degree in indegree.items() if degree == 0), key=order.get))
    ranks: dict[str, int] = {name: 0 for name in queue}
    visited: set[str] = set()
    while queue:
        name = queue.popleft()
        visited.add(name)
        for to_name in sorted(outgoing.get(name, []), key=order.get):
            ranks[to_name] = max(ranks.get(to_name, 0), ranks.get(name, 0) + 1)
            indegree[to_name] -= 1
            if indegree[to_name] == 0:
                queue.append(to_name)

    for el in skel.elements:
        if el.name not in ranks:
            ranks[el.name] = max((ranks.get(edge.from_, 0) + 1 for edge in skel.edges if edge.to == el.name), default=order[el.name])
    return ranks


def _elements_for_group(skel: Skeleton, group_name: str) -> list[Element]:
    return [e for e in skel.elements if e.group == group_name]


def _element_order(skel: Skeleton) -> dict[str, int]:
    return {el.name: i for i, el in enumerate(skel.elements)}


def _route_edges(
    skel: Skeleton,
    nodes: dict[str, tuple[int, int, int, int]],
    *,
    same_column_vertical: bool = True,
) -> list[dict]:
    edges_out: list[dict] = []
    for edge in skel.edges:
        sx, sy, sw, sh = nodes[edge.from_]
        dx, dy, dw, dh = nodes[edge.to]
        if same_column_vertical and sx == dx:
            if sy < dy:
                wp = [(sx + sw // 2, sy + sh), (dx + dw // 2, dy)]
            else:
                wp = [(sx + sw // 2, sy), (dx + dw // 2, dy + dh)]
        else:
            if dx > sx:
                start, end = (sx + sw, sy + sh // 2), (dx, dy + dh // 2)
                mid = _snap((start[0] + end[0]) / 2)
            elif dx < sx:
                start, end = (sx, sy + sh // 2), (dx + dw, dy + dh // 2)
                mid = _snap((start[0] + end[0]) / 2)
            else:
                gutter = _snap(max(sx + sw, dx + dw) + 40)
                start, end = (sx + sw, sy + sh // 2), (dx + dw, dy + dh // 2)
                mid = gutter
            wp = [start, (mid, start[1]), (mid, end[1]), end]
        edges_out.append({
            "from": edge.from_, "to": edge.to, "kind": edge.kind,
            "bidirectional": edge.bidirectional, "label": edge.label,
            "waypoints": wp, "label_xy": _label_xy(wp),
        })
    return edges_out


def _layout_notes(skel: Skeleton, nodes: dict[str, tuple[int, int, int, int]]) -> list[dict]:
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
    return notes_out


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
    data["layout"] = {"style": lo.layout_style}
    data["groups"] = [
        _group_item(g.name, g.label, lo)
        for g in skel.groups
    ]
    data["elements"] = []
    for e in skel.elements:
        item: dict = {"name": e.name, "kind": e.kind, "group": e.group,
                      "label": e.label, "bbox": _bbox(lo.nodes[e.name])}
        if e.name in lo.steps:
            item["step"] = lo.steps[e.name]
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


def _group_item(name: str, label: str | None, lo: LaidOut) -> dict:
    item = {"name": name, "label": label, "bbox": _bbox(lo.groups[name])}
    if name in lo.group_labels:
        item["label_bbox"] = _bbox(lo.group_labels[name])
    return item
