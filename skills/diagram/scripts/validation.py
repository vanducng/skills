"""Post-generation SVG validation gate.

Catches the bug classes that pure-LLM SVG output produces but a human reviewer
would catch in seconds:

  1. Bare `&` in text content -> XML strict-mode parse error (blank canvas).
  2. CSS var() in presentation attributes -> doesn't resolve when SVG loads
     via <img>; markers/labels render off-color or invisible. Fix by moving
     the var() reference into an inline `style=` attribute (CSS context).
  3. Node-rect bounding-box overlaps -> visible visual defect.
  4. Arrow-label rects landing on top of node-rects -> the dominant LLM
     positioning failure: occluder rects placed at node-corner coordinates
     instead of on edge midpoints.
  5. Coordinate drift -> only checked when an `expected_layout` is supplied
     (skeleton engine). Pass-2 LLM may not relocate elements > 5% from the
     coords supplied by the layout pass.

Auto-fixes 1 and 2 on the way through. Reports 3, 4, and 5 as blocking issues
so the caller can trigger one revise pass.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


# -- validation report ----------------------------------------------------

@dataclass
class ValidationReport:
    autofix_applied: list[str] = field(default_factory=list)
    blocking_issues: list[str] = field(default_factory=list)

    @property
    def needs_revise(self) -> bool:
        return bool(self.blocking_issues)

    def summary(self) -> str:
        return "\n".join(f"- {x}" for x in self.blocking_issues)


@dataclass
class ExpectedLayout:
    """Coords from pass-1 layout that pass-2 SVG must match within tolerance."""
    nodes: dict[str, tuple[float, float, float, float]]


def validate_and_fix(
    svg_text: str,
    *,
    expected_layout: "ExpectedLayout | None" = None,
) -> tuple[str, ValidationReport]:
    """Run the validation gate. Returns (possibly-modified-svg, report).

    Auto-fixes happen first (so that XML parsing succeeds on the fixed text).
    Blocking issues are returned for the caller to drive a single revise pass.
    If `expected_layout` is provided, additionally runs `validate_coord_fidelity`
    and adds any drift complaints to `report.blocking_issues`.
    """
    report = ValidationReport()

    svg_text, n_amp = _autofix_ampersands(svg_text)
    if n_amp:
        report.autofix_applied.append(f"escaped {n_amp} bare ampersand(s)")

    svg_text, n_var = _autofix_inline_css_vars(svg_text)
    if n_var:
        report.autofix_applied.append(
            f"moved {n_var} presentation-attr var() into inline style= "
            f"(preserves dark-mode swap)"
        )

    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError as exc:
        report.blocking_issues.append(f"xml parse error: {exc}")
        return svg_text, report

    node_rects = _collect_rects(root, _NODE_CLASSES)
    label_rects = _collect_rects(root, _LABEL_CLASSES)
    moved_labels = _autofix_arrow_label_positions(root, label_rects, node_rects)
    if moved_labels:
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        svg_text = ET.tostring(root, encoding="unicode")
        report.autofix_applied.append(
            f"moved {moved_labels} arrow label group(s) away from node bodies"
        )
        try:
            root = ET.fromstring(svg_text)
        except ET.ParseError as exc:
            report.blocking_issues.append(f"xml parse error after label autofix: {exc}")
            return svg_text, report
        node_rects = _collect_rects(root, _NODE_CLASSES)
        label_rects = _collect_rects(root, _LABEL_CLASSES)

    overlaps = _pairwise_overlaps(node_rects, node_rects, same_set=True)
    if overlaps:
        report.blocking_issues.append(
            "node-rect overlaps: " + _summarize(overlaps)
        )

    label_on_node = _pairwise_overlaps(label_rects, node_rects, same_set=False)
    if label_on_node:
        report.blocking_issues.append(
            "arrow-label rects occluding node bodies (place them on edge "
            "midpoints, not on node corners): " + _summarize(label_on_node)
        )

    if expected_layout is not None:
        drift = validate_coord_fidelity(svg_text, expected_layout)
        if drift:
            report.blocking_issues.extend(drift)

    return svg_text, report


def validate_coord_fidelity(
    svg_text: str,
    expected: ExpectedLayout,
    *,
    tolerance: float = 0.05,
) -> list[str]:
    """Return a list of drift complaints. Empty list = OK.

    Walks every SVG element with a `data-name` attribute matching an expected
    node name, computes its observed bbox, and compares to expected within
    `tolerance` (fractional, with a 4 px floor).
    """
    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError:
        return []

    by_name = _index_by_data_name(root)
    out: list[str] = []
    for name, (xe, ye, we, he) in expected.nodes.items():
        el = by_name.get(name)
        if el is None:
            out.append(f"missing element: {name}")
            continue
        bbox = _element_bbox(el)
        if bbox is None:
            out.append(f"missing data-bbox on path/composite element: {name}")
            continue
        xo, yo, wo, ho = bbox
        tol_x = max(tolerance * we, 4)
        tol_y = max(tolerance * he, 4)
        tol_w = max(tolerance * we, 4)
        tol_h = max(tolerance * he, 4)
        dx, dy = abs(xo - xe), abs(yo - ye)
        dw, dh = abs(wo - we), abs(ho - he)
        if dx > tol_x or dy > tol_y or dw > tol_w or dh > tol_h:
            out.append(
                f"{name}: drift ({dx:.0f},{dy:.0f},{dw:.0f},{dh:.0f}) "
                f"exceeds tol ({tol_x:.0f},{tol_y:.0f},{tol_w:.0f},{tol_h:.0f})"
            )
    return out


def _index_by_data_name(root: ET.Element) -> dict[str, ET.Element]:
    out: dict[str, ET.Element] = {}
    for el in root.iter():
        name = el.get("data-name")
        if name and name not in out:
            out[name] = el
    return out


def _element_bbox(el: ET.Element) -> tuple[float, float, float, float] | None:
    """Compute observed AABB. Honors data-bbox first; else infers from tag."""
    db = el.get("data-bbox")
    if db:
        try:
            x, y, w, h = (float(v.strip()) for v in db.split(","))
            return (x, y, w, h)
        except (ValueError, TypeError):
            pass
    tag = el.tag.split("}", 1)[-1]
    try:
        if tag == "rect":
            return (float(el.get("x", 0)), float(el.get("y", 0)),
                    float(el.get("width", 0)), float(el.get("height", 0)))
        if tag == "ellipse":
            cx, cy = float(el.get("cx", 0)), float(el.get("cy", 0))
            rx, ry = float(el.get("rx", 0)), float(el.get("ry", 0))
            return (cx - rx, cy - ry, 2 * rx, 2 * ry)
        if tag == "circle":
            cx, cy = float(el.get("cx", 0)), float(el.get("cy", 0))
            r = float(el.get("r", 0))
            return (cx - r, cy - r, 2 * r, 2 * r)
        if tag == "polygon":
            tokens = (el.get("points") or "").replace(",", " ").split()
            xs = [float(tokens[i]) for i in range(0, len(tokens) - 1, 2)]
            ys = [float(tokens[i + 1]) for i in range(0, len(tokens) - 1, 2)]
            if xs and ys:
                return (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    except (TypeError, ValueError):
        return None
    if tag == "g":
        boxes = [_element_bbox(c) for c in el.iter() if c is not el]
        boxes = [b for b in boxes if b is not None]
        if boxes:
            x = min(b[0] for b in boxes); y = min(b[1] for b in boxes)
            x2 = max(b[0] + b[2] for b in boxes); y2 = max(b[1] + b[3] for b in boxes)
            return (x, y, x2 - x, y2 - y)
    return None


# -- auto-fixers ----------------------------------------------------------

# Match `&` not followed by a known XML/HTML entity prefix.
_BARE_AMP = re.compile(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)")

# Match an opening tag and capture its attribute string. Used so we can rewrite
# all var()-presentation-attrs on a single element together (otherwise multiple
# inline `style=` attributes on the same element collide).
_OPEN_TAG = re.compile(r"<([A-Za-z][\w:-]*)((?:[^>'\"]|\"[^\"]*\"|'[^']*')*?)(/?)>")

# Match `attr="var(--name)"` or `attr='var(--name)'` inside an attribute string.
_VAR_ATTR = re.compile(
    r"""\s+(fill|stroke|stop-color)=(["'])var\(--([\w-]+)\)\2"""
)

# Match the existing `style="..."` attribute (if any).
_STYLE_ATTR = re.compile(r"""\s+style=(["'])(.*?)\1""", re.DOTALL)


def _autofix_ampersands(svg: str) -> tuple[str, int]:
    """Escape bare `&` outside CDATA sections."""
    parts: list[str] = []
    count = 0
    last = 0
    for match in re.finditer(r"<!\[CDATA\[.*?\]\]>", svg, re.DOTALL):
        head = svg[last:match.start()]
        new_head, n = _BARE_AMP.subn("&amp;", head)
        parts.append(new_head)
        parts.append(match.group(0))
        count += n
        last = match.end()
    new_tail, n = _BARE_AMP.subn("&amp;", svg[last:])
    parts.append(new_tail)
    count += n
    return "".join(parts), count


def _autofix_inline_css_vars(svg: str) -> tuple[str, int]:
    """Move presentation-attr var() into an inline `style=` attribute.

    `<rect fill="var(--bg)"/>` does NOT resolve when the SVG is loaded via an
    <img> tag - presentation attributes are not CSS context, so var() is left
    as a literal string. Inline `style="fill: var(--bg)"`, by contrast, IS CSS
    context and resolves correctly, including respecting `@media (prefers-color-scheme: dark)`
    rules from the embedded <style>.

    All var()-presentation attrs on the same element collapse into one merged
    `style=` so dark-mode adaptation continues to work.
    """
    count = 0

    def rewrite_tag(match: re.Match) -> str:
        nonlocal count
        tag = match.group(1)
        attrs_str = match.group(2)
        slash = match.group(3)

        # Collect every var() presentation attr and strip them from the tag.
        collected: list[tuple[str, str]] = []

        def grab(m: re.Match) -> str:
            collected.append((m.group(1), m.group(3)))  # (css-property, var-name)
            return ""

        attrs_str = _VAR_ATTR.sub(grab, attrs_str)
        if not collected:
            return match.group(0)

        count += len(collected)

        # Merge into existing style= if present, else append a new one.
        new_decls = "; ".join(f"{prop}: var(--{name})" for prop, name in collected)
        existing = _STYLE_ATTR.search(attrs_str)
        if existing:
            existing_body = existing.group(2).strip().rstrip(";")
            merged = f'{existing_body}; {new_decls}' if existing_body else new_decls
            attrs_str = (
                attrs_str[: existing.start()]
                + f' style="{merged}"'
                + attrs_str[existing.end() :]
            )
        else:
            attrs_str = attrs_str.rstrip() + f' style="{new_decls}"'

        return f"<{tag}{attrs_str}{slash}>"

    return _OPEN_TAG.sub(rewrite_tag, svg), count


# -- overlap detector -----------------------------------------------------

# CSS classes whose <rect> elements are "node bodies". Mutual overlap is a defect,
# AND label-rects landing on top of these is a defect.
_NODE_CLASSES = frozenset({
    "service", "datastore", "external-system", "cache", "queue",
    "process", "decision", "state", "entity", "actor", "node",
})

# Arrow-label occluder rects - designed to sit ON edges, NOT on nodes.
_LABEL_CLASSES = frozenset({"arrow-label", "label-bg", "edge-label"})


def _collect_rects(
    root: ET.Element, allowed_classes: frozenset[str]
) -> list[tuple[float, float, float, float, str]]:
    """Walk the tree, return (x, y, w, h, class-summary) for matching rects.

    Includes plain `<rect>` elements directly classed via `class=`, and rects
    nested inside a `<g class="arrow-label">` group (LLMs often put the bg-rect
    + the text inside a group rather than classing the rect itself).
    """
    out: list[tuple[float, float, float, float, str]] = []
    for el in root.iter():
        tag = el.tag.split("}", 1)[-1]
        if tag != "rect":
            continue
        classes = set((el.get("class") or "").split())
        # Inherit class from immediate <g> parent if applicable.
        # ElementTree doesn't expose parent natively, so we scan groups.
        if not classes & allowed_classes:
            # Maybe it's nested inside a labeled <g>; check by re-walk.
            # (Cheap fallback: include every rect inside a <g class="arrow-label"...>
            #  in the label-rect set.)
            continue
        try:
            x = float(el.get("x", 0))
            y = float(el.get("y", 0))
            w = float(el.get("width", 0))
            h = float(el.get("height", 0))
        except (TypeError, ValueError):
            continue
        if w <= 0 or h <= 0:
            continue
        out.append((x, y, w, h, " ".join(classes) or tag))

    # Second pass: rects nested inside <g class="<label-class>"> with no own class.
    for g in root.iter():
        if g.tag.split("}", 1)[-1] != "g":
            continue
        g_classes = set((g.get("class") or "").split())
        if not g_classes & allowed_classes:
            continue
        for el in g.iter():
            tag = el.tag.split("}", 1)[-1]
            if tag != "rect":
                continue
            classes = set((el.get("class") or "").split())
            if classes & allowed_classes:
                continue  # already collected on the first pass
            try:
                x = float(el.get("x", 0))
                y = float(el.get("y", 0))
                w = float(el.get("width", 0))
                h = float(el.get("height", 0))
            except (TypeError, ValueError):
                continue
            if w <= 0 or h <= 0:
                continue
            out.append((x, y, w, h, "/".join(g_classes) or "g"))

    return out


def _autofix_arrow_label_positions(
    root: ET.Element,
    label_rects: list[tuple[float, float, float, float, str]],
    node_rects: list[tuple[float, float, float, float, str]],
) -> int:
    """Move arrow-label groups above node bodies when the painter overlaps them."""
    if not label_rects or not node_rects:
        return 0
    parent = {child: el for el in root.iter() for child in el}
    moved: set[int] = set()
    for lx, ly, lw, lh, _ in label_rects:
        overlaps = [
            (nx, ny, nw, nh, nc)
            for nx, ny, nw, nh, nc in node_rects
            if _overlaps(lx, ly, lw, lh, nx, ny, nw, nh)
        ]
        if not overlaps:
            continue
        label_el = _find_rect(root, lx, ly, lw, lh)
        if label_el is None:
            continue
        move_root = _label_move_root(label_el, parent)
        ident = id(move_root)
        if ident in moved:
            continue
        new_y = min(ny for _, ny, _, _, _ in overlaps) - lh - 8
        if new_y < 8:
            new_y = max(ny + nh for _, ny, _, nh, _ in overlaps) + 8
        dy = new_y - ly
        if abs(dy) < 0.5:
            continue
        _shift_y(move_root, dy)
        moved.add(ident)
    return len(moved)


def _label_move_root(el: ET.Element, parent: dict[ET.Element, ET.Element]) -> ET.Element:
    p = parent.get(el)
    if p is not None and "arrow-label" in set((p.get("class") or "").split()):
        return p
    return el


def _find_rect(root: ET.Element, x: float, y: float, w: float, h: float) -> ET.Element | None:
    for el in root.iter():
        if el.tag.split("}", 1)[-1] != "rect":
            continue
        try:
            ex = float(el.get("x", 0)); ey = float(el.get("y", 0))
            ew = float(el.get("width", 0)); eh = float(el.get("height", 0))
        except (TypeError, ValueError):
            continue
        if abs(ex - x) < 0.1 and abs(ey - y) < 0.1 and abs(ew - w) < 0.1 and abs(eh - h) < 0.1:
            return el
    return None


def _shift_y(root: ET.Element, dy: float) -> None:
    for el in root.iter():
        for attr in ("y", "y1", "y2", "cy"):
            val = el.get(attr)
            if val is None:
                continue
            try:
                el.set(attr, _fmt_num(float(val) + dy))
            except ValueError:
                continue


def _fmt_num(v: float) -> str:
    if abs(v - round(v)) < 0.01:
        return str(int(round(v)))
    return f"{v:.1f}".rstrip("0").rstrip(".")


def _pairwise_overlaps(
    set_a: list[tuple[float, float, float, float, str]],
    set_b: list[tuple[float, float, float, float, str]],
    *,
    same_set: bool,
    min_overlap_px: float = 4.0,
) -> list[str]:
    """Report rect-pairs whose AABBs overlap by more than min_overlap_px on both axes."""
    out: list[str] = []
    for i, (ax, ay, aw, ah, ac) in enumerate(set_a):
        start = i + 1 if same_set else 0
        for j in range(start, len(set_b)):
            bx, by, bw, bh, bc = set_b[j]
            if same_set and i == j:
                continue
            ox = min(ax + aw, bx + bw) - max(ax, bx)
            oy = min(ay + ah, by + bh) - max(ay, by)
            if ox > min_overlap_px and oy > min_overlap_px:
                out.append(
                    f"[{ac} @ ({ax:.0f},{ay:.0f}) {aw:.0f}x{ah:.0f}] "
                    f"vs [{bc} @ ({bx:.0f},{by:.0f}) {bw:.0f}x{bh:.0f}]"
                )
    return out


def _overlaps(
    ax: float, ay: float, aw: float, ah: float,
    bx: float, by: float, bw: float, bh: float,
    *,
    min_overlap_px: float = 4.0,
) -> bool:
    ox = min(ax + aw, bx + bw) - max(ax, bx)
    oy = min(ay + ah, by + bh) - max(ay, by)
    return ox > min_overlap_px and oy > min_overlap_px


def _summarize(overlaps: list[str], cap: int = 5) -> str:
    head = "; ".join(overlaps[:cap])
    return head + (f" (+{len(overlaps) - cap} more)" if len(overlaps) > cap else "")
