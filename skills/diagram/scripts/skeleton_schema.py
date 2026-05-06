"""YAML skeleton schema + validator for `--engine skeleton` (pass-1 output).

Defines the dataclass tree the pass-1 LLM emits as YAML and a strict validator
that rejects any deviation from the contract. Pure-Python; no LLM calls.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import yaml

SUPPORTED_TYPES = frozenset({
    "system-architecture", "data-flow", "sequence", "er-diagram",
    "state-machine", "c4-context", "c4-container",
})

SUPPORTED_PRESETS = frozenset({"warm", "mono", "pastel", "cyberpunk"})

KINDS = frozenset({
    "service", "datastore", "external-system", "cache", "queue",
    "actor", "process", "decision", "state", "entity",
})

EDGE_KINDS = frozenset({"sync", "async", "error"})

NOTE_POSITIONS = frozenset({"above", "below", "left", "right"})

ALLOWED_TOP_LEVEL = frozenset({
    "type", "preset", "title", "groups", "elements", "edges", "notes",
})
REQUIRED_TOP_LEVEL = frozenset({"type", "preset", "groups", "elements", "edges"})

NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
LABEL_MAX = 40
EDGE_LABEL_MAX_WORDS = 4


class SkeletonError(ValueError):
    """Raised when a skeleton fails schema validation."""


@dataclass
class Group:
    name: str
    label: str | None = None


@dataclass
class Element:
    name: str
    kind: str
    group: str
    label: str
    subject: bool = False
    note: str | None = None


@dataclass
class Edge:
    from_: str
    to: str
    label: str | None = None
    kind: str = "sync"
    bidirectional: bool = False


@dataclass
class Note:
    attached: str
    position: str
    text: str


@dataclass
class Skeleton:
    type: str
    preset: str
    title: str | None = None
    groups: list[Group] = field(default_factory=list)
    elements: list[Element] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    notes: list[Note] = field(default_factory=list)


def parse_skeleton(yaml_text: str) -> Skeleton:
    """Parse + validate YAML skeleton string. Raises SkeletonError on any defect."""
    try:
        raw = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise SkeletonError(f"YAML parse error: {exc}") from exc
    if not isinstance(raw, dict):
        raise SkeletonError("top-level must be a mapping")

    keys = set(raw.keys())
    unknown = keys - ALLOWED_TOP_LEVEL
    if unknown:
        raise SkeletonError(
            f"unknown top-level key(s): {sorted(unknown)}. "
            f"Allowed: {sorted(ALLOWED_TOP_LEVEL)}"
        )
    missing = REQUIRED_TOP_LEVEL - keys
    if missing:
        raise SkeletonError(f"missing required top-level key(s): {sorted(missing)}")

    dtype = raw["type"]
    if dtype not in SUPPORTED_TYPES:
        raise SkeletonError(f"type {dtype!r} not in {sorted(SUPPORTED_TYPES)}")

    preset = raw["preset"]
    if preset not in SUPPORTED_PRESETS:
        raise SkeletonError(f"preset {preset!r} not in {sorted(SUPPORTED_PRESETS)}")

    title = raw.get("title")
    if title is not None and not isinstance(title, str):
        raise SkeletonError("title must be a string")

    groups = _parse_groups(raw.get("groups") or [])
    elements = _parse_elements(raw.get("elements") or [], {g.name for g in groups})
    edges = _parse_edges(raw.get("edges") or [], {e.name for e in elements})
    notes = _parse_notes(raw.get("notes") or [], {e.name for e in elements})

    subject_count = sum(1 for e in elements if e.subject)
    if subject_count > 1:
        raise SkeletonError(f"only one element may have subject: true (found {subject_count})")

    return Skeleton(
        type=dtype, preset=preset, title=title,
        groups=groups, elements=elements, edges=edges, notes=notes,
    )


def _parse_groups(items: list) -> list[Group]:
    seen: set[str] = set()
    out: list[Group] = []
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            raise SkeletonError(f"groups[{i}] must be a mapping")
        name = it.get("name")
        if not isinstance(name, str) or not NAME_RE.match(name):
            raise SkeletonError(f"groups[{i}].name {name!r} must match {NAME_RE.pattern}")
        if name in seen:
            raise SkeletonError(f"duplicate group name: {name!r}")
        seen.add(name)
        label = it.get("label")
        if label is not None and not isinstance(label, str):
            raise SkeletonError(f"groups[{i}].label must be a string")
        out.append(Group(name=name, label=label))
    return out


def _parse_elements(items: list, group_names: set[str]) -> list[Element]:
    seen: set[str] = set()
    out: list[Element] = []
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            raise SkeletonError(f"elements[{i}] must be a mapping")
        name = it.get("name")
        if not isinstance(name, str) or not NAME_RE.match(name):
            raise SkeletonError(f"elements[{i}].name {name!r} must match {NAME_RE.pattern}")
        if name in seen:
            raise SkeletonError(f"duplicate element name: {name!r}")
        seen.add(name)
        kind = it.get("kind")
        if kind not in KINDS:
            raise SkeletonError(f"elements[{i}].kind {kind!r} not in {sorted(KINDS)}")
        group = it.get("group")
        if group not in group_names:
            raise SkeletonError(f"elements[{i}].group {group!r} not declared in groups")
        label = it.get("label")
        if not isinstance(label, str) or not label.strip():
            raise SkeletonError(f"elements[{i}].label must be a non-empty string")
        if len(label) > LABEL_MAX:
            raise SkeletonError(f"elements[{i}].label > {LABEL_MAX} chars")
        subject = bool(it.get("subject", False))
        note = it.get("note")
        if note is not None and not isinstance(note, str):
            raise SkeletonError(f"elements[{i}].note must be a string")
        out.append(Element(name=name, kind=kind, group=group, label=label,
                           subject=subject, note=note))
    return out


def _parse_edges(items: list, element_names: set[str]) -> list[Edge]:
    out: list[Edge] = []
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            raise SkeletonError(f"edges[{i}] must be a mapping")
        src = it.get("from")
        dst = it.get("to")
        if src not in element_names:
            raise SkeletonError(f"edges[{i}].from {src!r} not an element")
        if dst not in element_names:
            raise SkeletonError(f"edges[{i}].to {dst!r} not an element")
        kind = it.get("kind", "sync")
        if kind not in EDGE_KINDS:
            raise SkeletonError(f"edges[{i}].kind {kind!r} not in {sorted(EDGE_KINDS)}")
        label = it.get("label")
        if label is not None:
            if not isinstance(label, str):
                raise SkeletonError(f"edges[{i}].label must be a string")
            words = label.split()
            if len(words) > EDGE_LABEL_MAX_WORDS:
                raise SkeletonError(
                    f"edges[{i}].label has {len(words)} words; "
                    f"max {EDGE_LABEL_MAX_WORDS}"
                )
        bidirectional = bool(it.get("bidirectional", False))
        out.append(Edge(from_=src, to=dst, label=label, kind=kind,
                        bidirectional=bidirectional))
    return out


def _parse_notes(items: list, element_names: set[str]) -> list[Note]:
    out: list[Note] = []
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            raise SkeletonError(f"notes[{i}] must be a mapping")
        attached = it.get("attached")
        if attached not in element_names:
            raise SkeletonError(f"notes[{i}].attached {attached!r} not an element")
        position = it.get("position")
        if position not in NOTE_POSITIONS:
            raise SkeletonError(f"notes[{i}].position {position!r} not in {sorted(NOTE_POSITIONS)}")
        text = it.get("text")
        if not isinstance(text, str) or not text.strip():
            raise SkeletonError(f"notes[{i}].text must be a non-empty string")
        out.append(Note(attached=attached, position=position, text=text))
    return out


def to_yaml(skel: Skeleton) -> str:
    """Round-trip back to YAML. Used to feed pass-2 with the laid-out skeleton."""
    data: dict = {
        "type": skel.type,
        "preset": skel.preset,
    }
    if skel.title is not None:
        data["title"] = skel.title
    data["groups"] = [_group_dict(g) for g in skel.groups]
    data["elements"] = [_element_dict(e) for e in skel.elements]
    data["edges"] = [_edge_dict(e) for e in skel.edges]
    if skel.notes:
        data["notes"] = [_note_dict(n) for n in skel.notes]
    return yaml.safe_dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)


def _group_dict(g: Group) -> dict:
    out: dict = {"name": g.name}
    if g.label is not None:
        out["label"] = g.label
    return out


def _element_dict(e: Element) -> dict:
    out: dict = {"name": e.name, "kind": e.kind, "group": e.group, "label": e.label}
    if e.subject:
        out["subject"] = True
    if e.note is not None:
        out["note"] = e.note
    return out


def _edge_dict(e: Edge) -> dict:
    out: dict = {"from": e.from_, "to": e.to}
    if e.label is not None:
        out["label"] = e.label
    out["kind"] = e.kind
    if e.bidirectional:
        out["bidirectional"] = True
    return out


def _note_dict(n: Note) -> dict:
    return {"attached": n.attached, "position": n.position, "text": n.text}
