#!/usr/bin/env python3
"""Turn a local HTML report into a Confluence Cloud body for `twg confluence content create|update --format html`.

  to_confluence.py REPORT.html [-o BODY.html] [--widths JSON|FILE] [--media FILE] [--page-id ID] [--figure-width 1800]
  to_confluence.py --lint BODY.html

--widths maps a table header to a column width in px ({"Status": 110}); other columns get a width estimated from
their longest cell. --media maps an <img src> (or its basename) or an inline <svg> id ("#velocity", else "svg-1",
"svg-2" in page order) to the uploaded attachment: {"fileId": "...", "collection"?: "...", "width"?: px,
"height"?: px, "file"?: png}. Native size comes from width/height, else the PNG header of "file" or of the <img src>.
Exit 1 when the output breaks a rule (the same check as --lint) or a chart has no media entry. Stdlib only.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

RENAME = {"b": "strong", "i": "em", "strike": "s", "del": "s"}
MARKS = {"strong", "em", "u", "s", "sub", "sup"}
VOID = {"br", "hr", "img", "input", "meta", "link", "col", "source", "wbr", "area", "base"}
DROP = {"head", "style", "script", "title", "noscript", "template", "colgroup"}
UNWRAP = {"html", "body", "main", "article", "header", "footer", "nav"}
BLOCK = {"p", "ul", "ol", "pre", "table", "div", "figure", "blockquote", "hr", "section", "details",
         "h1", "h2", "h3", "h4", "h5", "h6", "img", "svg", "aside"}  # fmt: skip
PILL = {"pill", "status", "badge", "chip", "lozenge", "tag"}
PANEL = {"note", "callout", "info", "panel", "notice", "tip", "alert"}
COLORS = {
    "green": {"green", "ok", "pass", "passed", "success", "done", "good", "healthy"},
    "yellow": {"yellow", "amber", "orange", "warn", "warning", "pending", "partial", "risk", "at-risk"},
    "red": {"red", "fail", "failed", "error", "danger", "bad", "blocked", "critical"},
    "blue": {"blue"},
    "purple": {"purple"},
}
PANEL_TYPES = {"warning": {"warn", "warning"}, "error": {"error", "danger"}, "success": {"success"}}
LANG = re.compile(r"language-[\w+#-]+")


def norm(text: str) -> str:
    return " ".join(text.split()).casefold()


def estimate(chars: int) -> int:
    return max(80, min(480, round(chars * 8 + 32)))  # ~8px a character at the 16px body font, plus cell padding


def png_size(path: Path) -> tuple[int, int] | None:
    try:
        head = path.read_bytes()[:24]
    except OSError:
        return None
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


class Grid:
    """Column index of each cell, honoring colspan and rowspan."""

    def __init__(self):
        self.row, self.col, self.taken = -1, 0, set()

    def next_row(self):
        self.row, self.col = self.row + 1, 0

    def place(self, span: int, rowspan: int) -> int:
        while (self.row, self.col) in self.taken:
            self.col += 1
        start = self.col
        self.taken.update((self.row + r, start + c) for r in range(rowspan) for c in range(span))
        self.col = start + span
        return start


def spans(attrs: dict) -> tuple[int, int]:
    def num(key):
        try:
            return max(1, int(attrs.get(key) or 1))
        except ValueError:
            return 1

    return num("colspan"), num("rowspan")


class TableScan(HTMLParser):
    """First pass: per table, the first-row header names and the longest text in each column."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.stack, self.cells, self.drop = [], [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in DROP:
            self.drop += 1
        a = dict(attrs)
        if tag == "table":
            t = {"headers": {}, "longest": {}, "grid": Grid()}
            self.tables.append(t)
            self.stack.append(t)
        elif tag == "tr" and self.stack:
            self.stack[-1]["grid"].next_row()
        elif tag in ("th", "td") and self.stack:
            t = self.stack[-1]
            span, rowspan = spans(a)
            self.cells.append({"t": t, "col": t["grid"].place(span, rowspan), "span": span, "text": ""})

    def handle_endtag(self, tag):
        if tag in DROP:
            self.drop = max(0, self.drop - 1)
        if tag in ("th", "td") and self.cells:
            c = self.cells.pop()
            t, text = c["t"], " ".join(c["text"].split())
            if t["grid"].row == 0:
                t["headers"][c["col"]] = text
            for k in range(c["span"]):
                t["longest"][c["col"] + k] = max(t["longest"].get(c["col"] + k, 0), len(text) // c["span"])
        elif tag == "table" and self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if self.cells and not self.drop:
            self.cells[-1]["text"] += data


class Converter(HTMLParser):
    def __init__(self, tables, widths, media, page_id, base, figure_width):
        super().__init__(convert_charrefs=True)
        self.tables, self.widths, self.media, self.page_id = iter(tables), widths, media, page_id
        self.base, self.figure_width = base, figure_width
        self.out, self.stack, self.drop, self.svgs = [], [], 0, 0
        self.skip_svg, self.svg, self.svg_title, self.svg_title_on = 0, {}, "", False
        self.errors, self.estimated = [], {}

    # -- output helpers
    def emit(self, s: str):
        self.out.append(s)

    def open_tag(self, tag: str, attrs: dict):
        parts = [tag] + [f'{k}="{html.escape(str(v), quote=True)}"' if v is not None else k for k, v in attrs.items()]
        self.emit("<" + " ".join(parts) + ">")

    def push(self, src, out, **extra):
        self.stack.append({"src": src, "out": out, **extra})

    def top(self):
        """The innermost element that is written out; unwrapped wrappers do not count."""
        return next((r for r in reversed(self.stack) if r["out"]), None)

    def inside(self, src: str) -> bool:
        return any(r["src"] == src for r in self.stack)

    def in_inline_code(self) -> bool:
        return any(r.get("inline_code") for r in self.stack)

    # -- panels: bare inline content directly inside a panel goes in a <p>
    def before_inline(self):
        t = self.top()
        if t and t.get("panel") and not t.get("para"):
            self.emit("<p>")
            t["para"] = True

    def before_block(self):
        t = self.top()
        if t and t.get("panel") and t.get("para"):
            self.emit("</p>")
            t["para"] = False

    # -- media
    def media_entry(self, keys: list[str], what: str):
        for k in keys:
            if k in self.media:
                return self.media[k]
        self.errors.append(f"{what}: no --media entry (tried {', '.join(repr(k) for k in keys)}); upload the PNG first")
        return None

    def emit_media(self, entry: dict, alt: str, fallback_png: Path | None):
        collection = entry.get("collection") or (f"contentId-{self.page_id}" if self.page_id else None)
        if not entry.get("fileId") or not collection:
            self.errors.append(f"{alt or 'chart'}: media entry needs fileId, and collection or --page-id")
            return
        size = None
        if entry.get("width") and entry.get("height"):
            size = (int(entry["width"]), int(entry["height"]))
        else:
            for p in ([self.base / entry["file"]] if entry.get("file") else []) + ([fallback_png] if fallback_png else []):
                size = png_size(p)
                if size:
                    break
        fig_width = min(self.figure_width, size[0]) if size else self.figure_width
        fig = next((r for r in reversed(self.stack) if r["src"] == "figure"), None)
        if fig and fig.get("media_open"):
            self.emit("</figure>")
            fig["media_open"] = False
        t = self.top()
        in_p = t is not None and t["out"] == "p"
        if in_p:
            self.emit("</p>")
        self.before_block()
        self.open_tag("figure", {"data-type": "media-single", "data-layout": "center",
                                 "data-width": fig_width, "data-width-type": "pixel"})  # fmt: skip
        attrs = {"data-type": "media", "data-media-type": "file", "data-id": entry["fileId"],
                 "data-collection": collection, "data-alt": alt}  # fmt: skip
        if size:
            attrs.update({"data-width": size[0], "data-height": size[1]})
        else:
            print(f"warning: {alt or entry['fileId']}: native size unknown, add width/height to its media entry",
                  file=sys.stderr)  # fmt: skip
        self.open_tag("div", attrs)
        self.emit("</div>")
        if fig is not None:  # left open so a <figcaption> can join it
            fig["media_open"] = True
        else:
            self.emit("</figure>")
        if in_p:
            self.emit("<p>")

    # -- parser callbacks
    def handle_starttag(self, tag, attrs):
        self.start(tag, dict(attrs), void=tag in VOID)

    def handle_startendtag(self, tag, attrs):
        self.start(tag, dict(attrs), void=True)

    def start(self, tag, a, void):
        if self.skip_svg:
            if tag == "svg" and not void:
                self.skip_svg += 1
            self.svg_title_on = tag == "title" and not void
            return
        if self.drop:
            if tag in DROP and not void:
                self.drop += 1
            return
        if tag in DROP:
            if not void:
                self.drop += 1
            return
        classes = set((a.pop("class", "") or "").casefold().split())

        if self.inside("pre"):
            if tag == "code":
                lang = next((c for c in classes if LANG.fullmatch(c)), None)
                self.open_tag("code", {"class": lang} if lang else {})
                self.push("code", "code")
            return
        if self.in_inline_code():
            return

        if tag == "svg":
            self.svgs += 1
            self.svg = {"id": a.get("id"), "label": a.get("aria-label", ""), "n": self.svgs}
            self.svg_title = ""
            if not void:
                self.skip_svg = 1
            else:
                self.end_svg()
            return
        if tag == "img":
            src = a.get("src", "")
            if src.startswith(("http://", "https://")):
                self.before_inline()
                self.open_tag("img", a)
                return
            entry = self.media_entry([src, Path(src).name], f"<img src={src!r}>")
            if entry:
                self.emit_media(entry, a.get("alt", "") or Path(src).name, self.base / src)
            return

        if tag in UNWRAP or (tag == "section" and "data-type" not in a):
            return self.push(tag, None)
        if tag == "figure" and "data-type" not in a:
            return self.push("figure", None)
        if tag == "figcaption":
            fig = next((r for r in reversed(self.stack) if r["src"] == "figure"), None)
            if fig and (fig.get("media_open") or fig["out"]):
                self.emit("<figcaption>")
                return self.push("figcaption", "figcaption")
            self.before_block()
            self.emit("<p>")
            return self.push("figcaption", "p")

        if tag in ("div", "aside") and (tag == "aside" or classes & PANEL) and "data-type" not in a:
            kind = next((k for k, words in PANEL_TYPES.items() if classes & words), "info")
            self.before_block()
            self.emit(f'<div data-type="panel-{kind}">')
            return self.push(tag, "div", panel=True)

        if tag == "span" and classes & PILL and "data-type" not in a:
            color = next((c for c, words in COLORS.items() if classes & words), "neutral")
            self.before_inline()
            self.emit(f'<span data-type="status" data-color="{color}">')
            return self.push("span", "span")
        if tag in ("span", "div") and not a:
            return self.push(tag, None)

        if tag == "table":
            info = next(self.tables, {"headers": {}, "longest": {}})
            a["data-layout"] = "full-width"
            self.before_block()
            self.open_tag("table", a)
            return self.push("table", "table", info=info, grid=Grid())
        if tag == "tr":
            t = next((r for r in reversed(self.stack) if r["src"] == "table"), None)
            if t:
                t["grid"].next_row()
        if tag in ("th", "td"):
            t = next((r for r in reversed(self.stack) if r["src"] == "table"), None)
            if t:
                span, rowspan = spans(a)
                col = t["grid"].place(span, rowspan)
                a["data-colwidth"] = ",".join(str(self.width(t["info"], col + k)) for k in range(span))

        out = RENAME.get(tag, tag)
        if out == "code":  # inline code may not carry other marks: close them around it
            reopen = [r for r in self.stack if r["out"] in MARKS]
            for r in reversed(reopen):
                self.emit(f"</{r['out']}>")
            self.before_inline()
            self.open_tag("code", a)
            return self.push("code", "code", inline_code=True, reopen=reopen)

        (self.before_block if out in BLOCK else self.before_inline)()
        self.open_tag(out, a)
        if not void:
            self.push(tag, out)

    def width(self, info: dict, col: int) -> int:
        header = info["headers"].get(col, "")
        if norm(header) in self.widths:
            return self.widths[norm(header)]
        w = estimate(max(info["longest"].get(col, 0), len(header)))
        self.estimated[header or f"column {col + 1}"] = w
        return w

    def end_svg(self):
        s = self.svg
        keys = ([f"#{s['id']}", s["id"]] if s["id"] else []) + [f"svg-{s['n']}"]
        entry = self.media_entry(keys, f"<svg> #{s['n']}" + (f" id={s['id']!r}" if s["id"] else ""))
        if entry:
            alt = s["label"] or " ".join(self.svg_title.split()) or keys[0].lstrip("#")
            self.emit_media(entry, alt, None)

    def handle_endtag(self, tag):
        if self.skip_svg:
            self.svg_title_on = False
            if tag == "svg":
                self.skip_svg -= 1
                if not self.skip_svg:
                    self.end_svg()
            return
        if self.drop:
            if tag in DROP:
                self.drop -= 1
            return
        if self.inside("pre") and tag not in ("code", "pre"):
            return
        if self.in_inline_code() and tag != "code":
            return
        if not any(r["src"] == tag for r in self.stack):
            return
        while self.stack:
            r = self.stack.pop()
            self.close_rec(r)
            if r["src"] == tag:
                break

    def close_rec(self, r: dict):
        if r.get("para"):
            self.emit("</p>")
        if r.get("media_open"):
            self.emit("</figure>")
        if r["out"]:
            self.emit(f"</{r['out']}>")
        for m in r.get("reopen", []):
            self.emit(f"<{m['out']}>")

    def handle_data(self, data):
        if self.skip_svg:
            if self.svg_title_on:
                self.svg_title += data
            return
        if self.drop:
            return
        if data.strip() and not self.inside("pre"):
            self.before_inline()
        self.emit(html.escape(data, quote=False))

    def finish(self) -> str:
        while self.stack:
            self.close_rec(self.stack.pop())
        body = "".join(self.out)
        while True:  # marks closed and reopened around inline code can leave empty pairs
            body, n = re.subn(r"<(strong|em|u|s|sub|sup)></\1>", "", body)
            if not n:
                break
        return re.sub(r"\n\s*\n(\s*\n)+", "\n\n", body).strip() + "\n"


class Lint(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.problems, self.marks, self.pre = [], [], 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        where = f"line {self.getpos()[0]}: <{tag}>"
        if tag in ("b", "i"):
            self.problems.append(f"{where} use <{RENAME[tag]}>")
        if "class" in a:
            ok = (tag == "code" and self.pre and LANG.fullmatch(a["class"] or "")) or (tag == "span" and a["class"] == "annotation")
            if not ok:
                self.problems.append(f'{where} class="{a["class"]}" is not allowed')
        if tag in ("th", "td") and not re.fullmatch(r"\d+(,\d+)*", a.get("data-colwidth") or ""):
            self.problems.append(f"{where} needs data-colwidth (px, comma-separated for colspan)")
        if tag == "table" and a.get("data-layout") != "full-width":
            self.problems.append(f'{where} needs data-layout="full-width"')
        if tag == "svg":
            self.problems.append(f"{where} inline svg does not survive; render a PNG and attach it")
        if tag == "img" and not (a.get("src") or "").startswith(("http://", "https://")):
            self.problems.append(f"{where} local image; upload it and use a media figure")
        if tag in ("html", "head", "body", "style", "script"):
            self.problems.append(f"{where} emit a body fragment only")
        if tag == "figure" and a.get("data-width-type") == "percentage":
            self.problems.append(f"{where} a percentage width renders a thumbnail; use data-width-type=\"pixel\"")
        if tag == "pre":
            self.pre += 1
        if tag == "code" and not self.pre and self.marks:
            self.problems.append(f"{where} inline code inside <{self.marks[-1]}>; code cannot carry other marks")
        if tag in MARKS:
            self.marks.append(tag)

    def handle_endtag(self, tag):
        if tag == "pre":
            self.pre = max(0, self.pre - 1)
        if tag in MARKS and tag in self.marks:
            del self.marks[len(self.marks) - 1 - self.marks[::-1].index(tag)]


def lint(body: str) -> list[str]:
    p = Lint()
    p.feed(body)
    p.close()
    return p.problems


def convert(report: str, widths: dict, media: dict, page_id: str | None, base: Path, figure_width: int = 1800):
    scan = TableScan()
    scan.feed(report)
    scan.close()
    c = Converter(scan.tables, {norm(k): int(v) for k, v in widths.items()}, media, page_id, base, figure_width)
    c.feed(report)
    c.close()
    return c.finish(), c.errors, c.estimated


def load_json(value: str | None) -> dict:
    if not value:
        return {}
    p = Path(value)
    return json.loads(p.read_text(encoding="utf-8") if p.is_file() else value)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input", type=Path, help="the report HTML, or with --lint the body to check")
    ap.add_argument("-o", "--out", type=Path, help="write the body here (default: stdout)")
    ap.add_argument("--widths", help="header -> px, as inline JSON or a JSON file")
    ap.add_argument("--media", help="media map JSON file (or inline JSON)")
    ap.add_argument("--page-id", help="page id; media collection defaults to contentId-<page-id>")
    ap.add_argument("--figure-width", type=int, default=1800, help="figure pixel width (clamps to the content area)")
    ap.add_argument("--lint", action="store_true", help="only check an existing body")
    args = ap.parse_args(argv)

    text = args.input.read_text(encoding="utf-8")
    if args.lint:
        problems = lint(text)
        for p in problems:
            print(p, file=sys.stderr)
        return 1 if problems else 0

    body, errors, estimated = convert(text, load_json(args.widths), load_json(args.media), args.page_id,
                                      args.input.resolve().parent, args.figure_width)  # fmt: skip
    if estimated:
        print("estimated widths (pin them with --widths): " + json.dumps(estimated), file=sys.stderr)
    problems = errors + lint(body)
    for p in problems:
        print(f"error: {p}", file=sys.stderr)
    if args.out:
        args.out.write_text(body, encoding="utf-8")
    else:
        sys.stdout.write(body)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
