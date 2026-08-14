#!/usr/bin/env python3
"""End-to-end assertions for the fictional resume-screen example packet.

No real PII. No Drive. Writes the workbook under tempfile — never overwrites
the committed examples/sample-scorecard.xlsx. SKILL.md / fact-check.md routing
is contract-tested regardless of whether browser CLIs are on PATH.
"""

from __future__ import annotations

import importlib.util
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
EXAMPLES = SKILL / "examples"
RESUMES = EXAMPLES / "resumes"
SCORED = EXAMPLES / "scored-candidates.json"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

SPEC = importlib.util.spec_from_file_location(
    "write_scorecard", Path(__file__).with_name("write-scorecard.py")
)
writer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(writer)

REQUIRED_HEADERS = {
    "Rank",
    "Name",
    "File",
    "Tier",
    "Decision",
    "Total",
    "Knockouts",
    "Pipelines_25",
    "CoreStack_20",
    "Cloud_15",
    "Extras_10",
    "Band_10",
    "Location_10",
    "FactIntegrity_10",
    "Claim_feasibility",
    "Company_type",
    "Startup_fit",
    "Fit_decision",
    "Timeline_gaps",
    "Timeline_consistency",
    "Fact_check",
    "LinkedIn_URL",
    "Certs_claimed",
    "Certs_verified",
    "Certs_unverified",
    "Cert_notes",
    "Screen_questions",
}

FORBIDDEN_PII = (
    "Career Now",
    "Career Now Brands",
    "Royal Oak",
    "Praneetha",
    "Vinay",
    "Sai Teja",
    "Ankit",
    "Rama Krishna",
)

# Lever as an ATS product name in a hiring packet — allow "leverage"
PII_LEVER = re.compile(r"(?<![A-Za-z])Lever(?![A-Za-z])")

SCREEN_FORBIDDEN = re.compile(
    r"cert(?:ificate)?\s*id|badge id|show me the badge|show (?:me )?(?:the )?(?:badge|cert)"
    r"|hybrid|on-?site|relocat|time\s*zone|salary|compensation|does this band|visa|work auth",
    re.I,
)

FACTORS = [f["id"] for f in writer.FACTORS_DEFAULT]


def cell_text(el: ET.Element) -> str:
    f = el.find("m:f", NS)
    if f is not None and (f.text or "").strip():
        return f"={f.text}"
    t = el.find("m:is/m:t", NS)
    if t is not None:
        return t.text or ""
    v = el.find("m:v", NS)
    if v is not None:
        return v.text or ""
    return ""


def col_of(ref: str) -> str:
    return re.match(r"[A-Z]+", ref).group(0)


def load_candidates_sheet(path: Path) -> tuple[list[str], list[dict]]:
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
        wb = zf.read("xl/workbook.xml").decode("utf-8")
    assert 'name="Candidates"' in wb and 'name="Scorecard"' in wb
    rows_xml = root.findall("m:sheetData/m:row", NS)
    headers = []
    header_map = {}
    for c in rows_xml[0].findall("m:c", NS):
        ref = c.attrib["r"]
        letter = col_of(ref)
        headers.append(cell_text(c))
        header_map[letter] = cell_text(c)
    rows = []
    for row in rows_xml[1:]:
        item = {}
        for c in row.findall("m:c", NS):
            letter = col_of(c.attrib["r"])
            item[header_map[letter]] = cell_text(c)
        rows.append(item)
    return headers, rows


def write_xlsx_to(tmp: Path) -> Path:
    out = tmp / "sample-scorecard.xlsx"
    writer.main([
        "--input", str(SCORED),
        "--out", str(out),
        "--file-base", str(EXAMPLES),
        "--profile", "data-platform-engineer",
        "--jd", "sample-jd.md",
        "--check",
    ])
    return out


class ExampleScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls.xlsx = write_xlsx_to(Path(cls._tmpdir.name))
        cls.headers, cls.rows = load_candidates_sheet(cls.xlsx)
        cls.by_name = {r["Name"]: r for r in cls.rows}

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir.cleanup()

    def test_does_not_rewrite_committed_workbook(self):
        self.assertTrue(self.xlsx.is_file())
        self.assertNotEqual(self.xlsx.resolve(), (EXAMPLES / "sample-scorecard.xlsx").resolve())

    def test_committed_workbook_matches_json_source(self):
        committed = EXAMPLES / "sample-scorecard.xlsx"
        self.assertTrue(committed.is_file(), committed)
        self.assertNotEqual(self.xlsx.resolve(), committed.resolve())
        with zipfile.ZipFile(self.xlsx) as fresh, zipfile.ZipFile(committed) as tracked:
            self.assertEqual(
                fresh.read("xl/worksheets/sheet1.xml"),
                tracked.read("xl/worksheets/sheet1.xml"),
                "examples/sample-scorecard.xlsx drifted from scored-candidates.json; "
                "run scripts/build-example-workbook.py",
            )

    def test_resume_files_exist_and_are_the_file_targets(self):
        for slug in ("jordan-hale", "morgan-ellis", "riley-chen", "avery-kim"):
            beside_xlsx = EXAMPLES / "resumes" / f"{slug}.md"
            self.assertTrue(beside_xlsx.is_file(), beside_xlsx)
            row = next(r for r in self.rows if slug in r["File"])
            self.assertIn(f"resumes/{slug}.md", row["File"])
            self.assertNotIn("examples/resumes/", row["File"])
            self.assertNotIn(".txt", row["File"])
            self.assertTrue(row["File"].startswith("=HYPERLINK("))
            href = re.search(r'HYPERLINK\("([^"]+)"', row["File"])
            self.assertIsNotNone(href)
            self.assertTrue((EXAMPLES / href.group(1)).is_file(), href.group(1))

    def test_required_columns(self):
        missing = REQUIRED_HEADERS - set(self.headers)
        self.assertFalse(missing, f"missing columns: {sorted(missing)}")
        # Fact_check is the skill's FactCheck_status column
        self.assertIn("Fact_check", self.headers)
        self.assertIn("Startup_fit", self.headers)

    def test_total_is_formula_and_equals_factor_sum(self):
        for i, row in enumerate(self.rows, start=2):
            total = row["Total"]
            self.assertRegex(total, rf"^=SUM\(H{i}:N{i}\)$", total)
            displayed = sum(float(row[fid]) for fid in FACTORS)
            expected = {
                "Jordan Hale": 86,
                "Morgan Ellis": 84,
                "Avery Kim": 71,
                "Riley Chen": 48,
            }[row["Name"]]
            self.assertEqual(displayed, expected, f"{row['Name']}: SUM(H{i}:N{i}) cells")

    def test_archetype_decisions(self):
        jordan = self.by_name["Jordan Hale"]
        self.assertEqual(jordan["Tier"], "P1")
        self.assertEqual(jordan["Decision"], "Advance")
        self.assertEqual(jordan["Fact_check"], "Verified")

        morgan = self.by_name["Morgan Ellis"]
        self.assertEqual(morgan["Tier"], "P2")
        self.assertEqual(morgan["Decision"], "Maybe")
        self.assertIn("Cap P1 → P2", morgan["Fit_decision"])
        self.assertEqual(morgan["Startup_fit"], "Low")
        self.assertEqual(morgan["Company_type"], "enterprise")
        self.assertGreaterEqual(sum(float(morgan[f]) for f in FACTORS), 75)

        avery = self.by_name["Avery Kim"]
        self.assertEqual(avery["Tier"], "Out")
        self.assertEqual(avery["Decision"], "Waiver candidate")
        self.assertTrue(str(avery["Waiver"]).startswith("Yes"))
        self.assertNotEqual(avery["Tier"], "P1")
        self.assertIn("years", avery["Knockouts"].lower())

        riley = self.by_name["Riley Chen"]
        self.assertEqual(riley["Tier"], "Out")
        self.assertEqual(riley["Decision"], "Out")
        self.assertEqual(riley["Fact_check"], "Contradicted")
        self.assertEqual((riley.get("Screen_questions") or "").strip(), "")

    def test_screen_questions_have_no_hr_or_cert_id_asks(self):
        for row in self.rows:
            text = row.get("Screen_questions") or ""
            self.assertIsNone(
                SCREEN_FORBIDDEN.search(text),
                f"{row['Name']}: forbidden screen question language: {text!r}",
            )

    def test_no_real_hiring_pii_in_skill_tree(self):
        roots = [SKILL / "SKILL.md", SKILL / "references", SKILL / "examples"]
        files = []
        for root in roots:
            if root.is_file():
                files.append(root)
            else:
                files.extend(p for p in root.rglob("*") if p.is_file())
        for path in files:
            if path.suffix in {".pyc"} or "__pycache__" in path.parts:
                continue
            if path.suffix == ".xlsx":
                with zipfile.ZipFile(path) as zf:
                    text = "\n".join(zf.read(n).decode("utf-8", errors="ignore") for n in zf.namelist())
            else:
                text = path.read_text(encoding="utf-8", errors="ignore")
            for needle in FORBIDDEN_PII:
                self.assertNotIn(needle, text, f"{path}: found {needle!r}")
            if PII_LEVER.search(text):
                self.fail(f"{path}: found standalone 'Lever'")

    def test_linkedin_urls_are_example_placeholders(self):
        for row in self.rows:
            url = row.get("LinkedIn_URL") or ""
            if not url:
                continue
            self.assertIn("example.com", url)
            self.assertNotIn("linkedin.com/in/", url)


class BrowserRoutingContractTests(unittest.TestCase):
    """Routing contract is independent of whether browser CLIs are on PATH."""

    def setUp(self):
        self.skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.facts = (SKILL / "references" / "fact-check.md").read_text(encoding="utf-8")

    def test_routes_to_sibling_skills_by_name(self):
        for body in (self.skill, self.facts):
            self.assertIn("vd:ego-browser", body)
            self.assertIn("vd:agent-browser", body)
            self.assertIn("vd:browser-profile", body)
            self.assertIn("skills/ego-browser/", body)
            self.assertIn("agent-browser --profile", body)
        self.assertIn("do not invent a third driver", self.skill.lower())
        self.assertIn("does **not** invent a third driver", self.facts)

    def test_fallback_marks_login_walled_linkedin_unverified(self):
        for body in (self.skill, self.facts):
            self.assertIn("login-walled LinkedIn", body)
            self.assertIn("Unverified", body)
        self.assertIn("Do not invent profile content", self.facts)
        self.assertIn("If neither browser skill is runnable", self.facts)

    def test_sibling_skill_dirs_exist(self):
        root = SKILL.parent
        for name in ("ego-browser", "agent-browser", "browser-profile"):
            self.assertTrue((root / name / "SKILL.md").is_file(), name)


if __name__ == "__main__":
    unittest.main()
