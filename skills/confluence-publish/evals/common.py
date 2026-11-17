"""Shared by the checks.sh files: parse a Confluence HTML body without the skill's own script, so a check never grades the code under test with itself."""

import re
import sys
from html.parser import HTMLParser
from pathlib import Path


class Body(HTMLParser):
    def __init__(self, text: str):
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict]] = []
        self.tables: list[list[list[dict]]] = []  # table -> rows -> cell attrs (+ "_text")
        self._cell = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        self.tags.append((tag, a))
        if tag == "table":
            self.tables.append([])
        elif tag == "tr" and self.tables:
            self.tables[-1].append([])
        elif tag in ("th", "td") and self.tables and self.tables[-1]:
            a["_text"] = ""
            self.tables[-1][-1].append(a)
            self._cell = a

    def handle_endtag(self, tag):
        if tag in ("th", "td"):
            self._cell = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell["_text"] += data


def fail(msg: str):
    print(msg)
    sys.exit(1)


def load(path: str) -> tuple[str, Body]:
    p = Path(path)
    if not p.is_file():
        fail(f"no {path}")
    text = p.read_text(encoding="utf-8")
    return text, Body(text)


def assert_clean_markup(text: str, body: Body):
    """No <b>/<i>, no class attribute except language-* on a code block, no inline svg or local img, no document wrapper."""
    for tag, a in body.tags:
        if tag in ("b", "i"):
            fail(f"<{tag}> left in the body; Confluence wants <strong>/<em>")
        if "class" in a and not (tag == "code" and re.fullmatch(r"language-[\w+#-]+", a["class"])):
            fail(f'class="{a["class"]}" on <{tag}>')
        if tag == "svg":
            fail("inline <svg> left in the body")
        if tag == "img" and not a.get("src", "").startswith(("http://", "https://")):
            fail(f"local <img src={a.get('src')}> left in the body")
        if tag in ("html", "head", "body", "style", "script"):
            fail(f"<{tag}> in the body; emit a fragment only")


def column_widths(table: list[list[dict]], header: str) -> list[int]:
    """Every data-colwidth set on the column whose first-row text is `header` (single-span cells only)."""
    heads = [c["_text"].strip().casefold() for c in table[0]]
    if header.casefold() not in heads:
        fail(f"no column named {header}")
    i = heads.index(header.casefold())
    out = []
    for row in table:
        if i < len(row) and "colspan" not in row[i]:
            out.append(int(float(row[i]["data-colwidth"].split(",")[0])))
    return out


def assert_tables_sized(body: Body):
    if not body.tables:
        fail("no table in the body")
    for tag, a in body.tags:
        if tag == "table" and a.get("data-layout") != "full-width":
            fail('a <table> without data-layout="full-width"')
        if tag in ("th", "td") and not re.fullmatch(r"\d+(\.\d+)?(,\d+(\.\d+)?)*", a.get("data-colwidth", "")):
            fail(f"<{tag}> without a numeric data-colwidth")


def media(body: Body) -> list[tuple[dict, dict]]:
    """(figure attrs, media div attrs) for every media-single figure."""
    out, fig = [], None
    for tag, a in body.tags:
        if tag == "figure":
            fig = a
        elif tag == "div" and a.get("data-type") == "media" and fig is not None:
            out.append((fig, a))
    return out
