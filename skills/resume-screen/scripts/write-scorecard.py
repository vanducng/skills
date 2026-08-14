#!/usr/bin/env python3
"""Write a resume-screen Excel workbook with formula Totals and hyperlinks.

Stdlib only. Agents must not hand-type Total as a number — this script emits
=SUM(H{row}:N{row}) and =HYPERLINK(...) for File / LinkedIn_URL.

Usage:
    write-scorecard.py --input candidates.json --out scorecard.xlsx
    write-scorecard.py --input sample-scorecard.csv --out /tmp/demo.xlsx
    write-scorecard.py --input candidates.json --out scorecard.xlsx --check
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

FACTORS_DEFAULT = [
    {"id": "Pipelines_25", "max": 25, "meaning": "ELT/ETL, dbt, Airflow or similar, data quality, models in use"},
    {"id": "CoreStack_20", "max": 20, "meaning": "Python + SQL, Snowflake or equivalent warehouse depth"},
    {"id": "Cloud_15", "max": 15, "meaning": "AWS (or JD cloud), Lambda, Terraform/IaC, Git + CI/CD"},
    {"id": "Extras_10", "max": 10, "meaning": "Streamlit or internal tools, APIs, Docker/K8s, warehouse AI/LLMs"},
    {"id": "Band_10", "max": 10, "meaning": "Mid-level band fit (~3–7 relevant years; above-band or too junior loses points)"},
    {"id": "Location_10", "max": 10, "meaning": "Hours/location vs JD; unknown is mid-band, not a knockout"},
    {"id": "FactIntegrity_10", "max": 10, "meaning": "Verified 9–10; Partial 6–8; Unverified 3–5; Contradicted 0"},
]

KNOCKOUTS_DOC = [
    "Missing required languages / core tools (DPE: Python or SQL)",
    "Under ~3 years relevant (role-defined; DPE: data/platform/cloud engineering)",
    "Missing required platform (DPE: Snowflake or BigQuery/Redshift/Databricks/Synapse)",
    "Cannot meet hours/location — only if the resume clearly says so",
    "Material fact-check fail: employer, title, dates, or stack contradicted",
]

TIERS_DOC = [
    "P1 Advance: Total >= 75 AND Fact_check is Verified or Partial (unless Low-fit cap)",
    "P2 Maybe: Total 55–74, OR high score but Unverified, OR P1 capped by Low startup fit",
    "P3 Hold: Total 40–54",
    "Out: knockout, Contradicted, or Total < 40",
    "Waiver: High startup fit + years-knockout only — flag, do not promote Out → P1",
    "Overlays never change Total. Low startup fit caps P1 → P2 only.",
]

LEADING = ["Rank", "Name", "File", "Tier", "Decision", "Total", "Knockouts"]
OVERLAYS = [
    ("Claim_feasibility", "claim_feasibility"),
    ("Company_type", "company_type"),
    ("Startup_fit", "startup_fit"),
    ("Fit_decision", "fit_decision"),
    ("Timeline_gaps", "timeline_gaps"),
    ("Timeline_consistency", "timeline_consistency"),
    ("Years_relevant", "years_relevant"),
    ("Fact_check", "fact_check"),
    ("Waiver", "waiver"),
    ("LinkedIn_URL", "linkedin_url"),
    ("GitHub_URL", "github_url"),
    ("Portfolio_URL", "portfolio_url"),
    ("Certs_claimed", "certs_claimed"),
    ("Certs_verified", "certs_verified"),
    ("Certs_unverified", "certs_unverified"),
    ("Cert_notes", "cert_notes"),
    ("Screen_questions", "screen_questions"),
    ("Notes", "notes"),
]

TIER_ORDER = {"P1": 0, "P2": 1, "P3": 2, "Out": 3}


def col_letter(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def xml_esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def norm_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", key.lower())


def lookup(row: dict, *names: str):
    index = {norm_key(k): v for k, v in row.items() if k is not None}
    for name in names:
        if norm_key(name) in index:
            return index[norm_key(name)]
    return ""


def as_number(value, default=0):
    parsed = parse_number(value)
    return default if parsed is None else parsed


def parse_number(value):
    """Return int/float, or None if missing / empty / non-numeric."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    if not text or text.startswith("="):
        return None
    try:
        return int(text) if re.fullmatch(r"-?\d+", text) else float(text)
    except ValueError:
        return None


def load_input(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if isinstance(data, list):
            return {"candidates": data}
        if not isinstance(data, dict) or "candidates" not in data:
            sys.exit("JSON must be {candidates: [...]} or a list of candidate objects")
        return data
    reader = csv.DictReader(text.splitlines())
    return {"candidates": list(reader)}


def factor_value(row: dict, factor_id: str) -> float:
    parsed = parse_number(lookup(row, factor_id))
    if parsed is None:
        raise ValueError(f"{factor_id} missing or not a number")
    return parsed


def computed_total(row: dict, factors: list[dict]) -> float:
    return sum(factor_value(row, f["id"]) for f in factors)


def is_waiver(row: dict) -> bool:
    decision = str(lookup(row, "decision") or "").lower()
    waiver = str(lookup(row, "waiver") or "").lower()
    return "waiver" in decision or waiver.startswith("yes")


def sort_candidates(rows: list[dict], factors: list[dict]) -> list[dict]:
    def key(row: dict):
        tier = str(lookup(row, "tier") or "Out")
        order = TIER_ORDER.get(tier, 4)
        if tier == "Out" and is_waiver(row):
            order = 2.5
        return (order, -computed_total(row, factors), str(lookup(row, "name") or ""))

    return sorted(rows, key=key)


def validate(rows: list[dict], factors: list[dict]) -> None:
    errors = []
    for i, row in enumerate(rows, 1):
        if not lookup(row, "name"):
            errors.append(f"row {i}: missing name")
        if not lookup(row, "file"):
            errors.append(f"row {i}: missing file (operator-provided resume path or URL)")
        for factor in factors:
            raw = lookup(row, factor["id"])
            value = parse_number(raw)
            if value is None:
                errors.append(
                    f"row {i}: {factor['id']} missing or not a number ({raw!r})"
                )
                continue
            maximum = factor["max"]
            if value < 0 or value > maximum:
                errors.append(f"row {i}: {factor['id']}={value} outside 0–{maximum}")
    if errors:
        sys.exit("validation failed:\n  " + "\n  ".join(errors))


def headers(factors: list[dict]) -> list[str]:
    return LEADING + [f["id"] for f in factors] + [h for h, _ in OVERLAYS]


def hyperlink_formula(url: str, display: str | None = None) -> str:
    target = str(url).replace('"', '""')
    label = (display or url).replace('"', '""')
    return f'HYPERLINK("{target}","{label}")'


def resolve_file_href(file_path: str, file_base: Path) -> str:
    """Make File a hyperlink that resolves next to the workbook when possible.

    Relative paths that already exist under file_base (the --out directory) are
    kept. A repo-relative `examples/resumes/...` path is stripped to
    `resumes/...` when that file sits beside the xlsx. Absolute operator paths
    are left absolute.
    """
    raw = str(file_path).strip()
    if not raw:
        return raw
    p = Path(raw)
    if p.is_absolute():
        return p.as_posix()
    base = file_base.resolve()
    if (base / p).is_file():
        return p.as_posix()
    if p.parts and p.parts[0] == "examples":
        stripped = Path(*p.parts[1:])
        if (base / stripped).is_file():
            return stripped.as_posix()
    if p.is_file():
        try:
            return p.resolve().relative_to(base).as_posix()
        except ValueError:
            return p.resolve().as_posix()
    return raw


def candidate_cells(rank: int, row: dict, factors: list[dict], excel_row: int, file_base: Path) -> list[tuple]:
    """Return list of (col_idx, value, kind) where kind is n|s|f."""
    file_path = resolve_file_href(str(lookup(row, "file")), file_base)
    file_label = Path(file_path).name or file_path
    linkedin = str(lookup(row, "linkedin_url", "LinkedIn_URL") or "").strip()
    cells = [
        (1, rank, "n"),
        (2, lookup(row, "name"), "s"),
        (3, hyperlink_formula(file_path, file_label), "f"),
        (4, lookup(row, "tier"), "s"),
        (5, lookup(row, "decision"), "s"),
        (6, f"SUM(H{excel_row}:N{excel_row})", "f"),
        (7, lookup(row, "knockouts"), "s"),
    ]
    for offset, factor in enumerate(factors):
        cells.append((8 + offset, factor_value(row, factor["id"]), "n"))
    overlay_start = 8 + len(factors)
    for i, (header, key) in enumerate(OVERLAYS):
        col = overlay_start + i
        value = lookup(row, header, key)
        if header == "LinkedIn_URL" and str(value).strip():
            cells.append((col, hyperlink_formula(str(value).strip()), "f"))
        elif header == "Years_relevant" and value != "":
            cells.append((col, as_number(value, value), "n" if isinstance(as_number(value, None), (int, float)) else "s"))
        else:
            cells.append((col, value, "s"))
    return cells


def cell_xml(col: int, row: int, value, kind: str, style: int | None = None) -> str:
    ref = f"{col_letter(col)}{row}"
    style_attr = f' s="{style}"' if style is not None else ""
    if kind == "n":
        if value == "" or value is None:
            return f'<c r="{ref}"{style_attr}/>'
        return f'<c r="{ref}"{style_attr}><v>{xml_esc(value)}</v></c>'
    if kind == "f":
        return f'<c r="{ref}"{style_attr}><f>{xml_esc(value)}</f></c>'
    text = "" if value is None else str(value)
    return f'<c r="{ref}" t="inlineStr"{style_attr}><is><t xml:space="preserve">{xml_esc(text)}</t></is></c>'


def build_sheet(rows: list[list[tuple]], freeze: bool = True) -> str:
    max_col = 1
    for row in rows:
        for item in row:
            max_col = max(max_col, item[0])
    max_row = max(len(rows), 1)
    dim = f"A1:{col_letter(max_col)}{max_row}"
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
        f'<dimension ref="{dim}"/>',
        '<sheetViews><sheetView workbookViewId="0">',
    ]
    if freeze:
        parts.append('<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>')
    parts.append("</sheetView></sheetViews>")
    parts.append('<sheetFormatPr defaultRowHeight="15"/>')
    parts.append("<sheetData>")
    for r_idx, row in enumerate(rows, 1):
        cells = []
        for item in row:
            col, value, kind = item[0], item[1], item[2]
            style = item[3] if len(item) > 3 else None
            cells.append(cell_xml(col, r_idx, value, kind, style))
        parts.append(f'<row r="{r_idx}">{"".join(cells)}</row>')
    parts.append("</sheetData></worksheet>")
    return "".join(parts)


def candidates_sheet(rows: list[dict], factors: list[dict], file_base: Path) -> str:
    heads = headers(factors)
    header_row = [(i, h, "s", 1) for i, h in enumerate(heads, 1)]
    data_rows = [header_row]
    for rank, row in enumerate(rows, 1):
        excel_row = rank + 1
        cells = candidate_cells(rank, row, factors, excel_row, file_base)
        data_rows.append([(c, v, k) for c, v, k in cells])
    return build_sheet(data_rows, freeze=True)


def scorecard_sheet(meta: dict, factors: list[dict]) -> str:
    built: list[list[tuple]] = [
        [(1, "Resume screen — scoring key", "s", 1)],
        [(1, "Profile", "s", 1), (2, meta.get("profile", ""), "s")],
        [(1, "JD", "s", 1), (2, meta.get("jd", ""), "s")],
        [(1, "Generated_UTC", "s", 1), (2, meta.get("generated", ""), "s")],
        [(1, "", "s")],
        [(1, "Factors (Total = SUM of H:N on Candidates; overlays do not change Total)", "s", 1)],
        [(1, "Id", "s", 1), (2, "Max", "s", 1), (3, "Meaning", "s", 1)],
    ]
    for factor in factors:
        built.append([(1, factor["id"], "s"), (2, factor["max"], "n"), (3, factor.get("meaning", ""), "s")])
    built.append([(1, "", "s")])
    built.append([(1, "Layer 1 knockouts (any one = Out; still fill scores)", "s", 1)])
    for i, line in enumerate(KNOCKOUTS_DOC, 1):
        built.append([(1, i, "n"), (2, line, "s")])
    built.append([(1, "", "s")])
    built.append([(1, "Tiers", "s", 1)])
    for line in TIERS_DOC:
        built.append([(1, line, "s")])
    built.append([(1, "", "s")])
    built.append([(1, "File column", "s", 1), (2, "Hyperlink to the operator-provided resume path or URL — never an extracted .txt name", "s")])
    built.append([(1, "Screen_questions", "s", 1), (2, "P1/P2/waiver only. No hybrid, timezone, salary, or band-acceptance questions.", "s")])
    return build_sheet(built, freeze=False)


CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>
"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
"""

WB_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
"""

WORKBOOK = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Candidates" sheetId="1" r:id="rId1"/>
    <sheet name="Scorecard" sheetId="2" r:id="rId2"/>
  </sheets>
</workbook>
"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><name val="Calibri"/></font>
  </fonts>
  <fills count="2">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
  </fills>
  <borders count="1"><border/></borders>
  <cellStyleXfs count="1"><xf/></cellStyleXfs>
  <cellXfs count="2">
    <xf xfId="0"/>
    <xf xfId="0" fontId="1" applyFont="1"/>
  </cellXfs>
</styleSheet>
"""


def write_xlsx(path: Path, candidates_xml: str, scorecard_xml: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", RELS)
        zf.writestr("xl/workbook.xml", WORKBOOK)
        zf.writestr("xl/_rels/workbook.xml.rels", WB_RELS)
        zf.writestr("xl/styles.xml", STYLES)
        zf.writestr("xl/worksheets/sheet1.xml", candidates_xml)
        zf.writestr("xl/worksheets/sheet2.xml", scorecard_xml)


def check_xlsx(path: Path) -> None:
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        required = {
            "xl/worksheets/sheet1.xml",
            "xl/worksheets/sheet2.xml",
            "xl/workbook.xml",
        }
        missing = required - names
        if missing:
            sys.exit(f"--check failed: missing {sorted(missing)}")
        sheet1 = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
        workbook = zf.read("xl/workbook.xml").decode("utf-8")
        if "SUM(H" not in sheet1:
            sys.exit("--check failed: Candidates sheet has no SUM(H…) Total formula")
        if "HYPERLINK(" not in sheet1:
            sys.exit("--check failed: Candidates sheet has no HYPERLINK formula")
        if 'name="Candidates"' not in workbook or 'name="Scorecard"' not in workbook:
            sys.exit("--check failed: workbook is missing Candidates/Scorecard sheet names")
        # Hardcoded totals look like <v>86</v> on column F without a <f>
        if re.search(r'<c r="F\d+"[^>]*>\s*<v>', sheet1):
            sys.exit("--check failed: a Total (column F) cell has a cached number without a formula")
        ET.fromstring(sheet1)
        ET.fromstring(zf.read("xl/worksheets/sheet2.xml"))
    print(f"check ok: {path}")


def parse_factors(raw) -> list[dict]:
    if not raw:
        return list(FACTORS_DEFAULT)
    out = []
    for item in raw:
        if not isinstance(item, dict) or "id" not in item or "max" not in item:
            sys.exit("each factors[] entry needs id and max")
        out.append({
            "id": str(item["id"]),
            "max": int(item["max"]),
            "meaning": str(item.get("meaning", "")),
        })
    if len(out) != 7:
        sys.exit("factors must be exactly 7 slots (H–N); got %d" % len(out))
    if sum(f["max"] for f in out) != 100:
        sys.exit("factor max values must sum to 100")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a resume-screen .xlsx with formula Totals")
    parser.add_argument("--input", required=True, help="JSON or CSV of candidates")
    parser.add_argument("--out", required=True, help="Output .xlsx path")
    parser.add_argument("--profile", default="", help="Profile id (overrides JSON)")
    parser.add_argument("--jd", default="", help="JD path or label (overrides JSON)")
    parser.add_argument("--no-sort", action="store_true", help="Keep input order instead of P1/P2/P3/waiver/Out")
    parser.add_argument("--check", action="store_true", help="After write, assert SUM/HYPERLINK formulas exist")
    parser.add_argument(
        "--file-base",
        default="",
        help="Directory File hyperlinks are resolved against (default: parent of --out)",
    )
    args = parser.parse_args(argv)

    src = Path(args.input)
    if not src.is_file():
        sys.exit(f"input not found: {src}")
    payload = load_input(src)
    factors = parse_factors(payload.get("factors"))
    rows = list(payload.get("candidates") or [])
    if not rows:
        sys.exit("no candidates in input")
    validate(rows, factors)
    if not args.no_sort:
        rows = sort_candidates(rows, factors)

    meta = {
        "profile": args.profile or payload.get("profile") or "data-platform-engineer",
        "jd": args.jd or payload.get("jd") or "",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    out = Path(args.out)
    file_base = Path(args.file_base) if args.file_base else out.parent
    write_xlsx(out, candidates_sheet(rows, factors, file_base), scorecard_sheet(meta, factors))
    print(f"wrote {out} ({len(rows)} candidates, profile={meta['profile']})")
    if args.check:
        check_xlsx(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
