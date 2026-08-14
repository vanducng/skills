#!/usr/bin/env python3
"""Tests for write-scorecard.py: formula Totals, hyperlinks, sample CSV, validation."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "write_scorecard", Path(__file__).with_name("write-scorecard.py")
)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)

SAMPLE_CSV = Path(__file__).resolve().parent.parent / "examples" / "sample-scorecard.csv"

JORDAN = {
    "name": "Jordan Hale",
    "file": "resumes/jordan-hale.pdf",
    "tier": "P1",
    "decision": "Advance",
    "Pipelines_25": 22,
    "CoreStack_20": 18,
    "Cloud_15": 13,
    "Extras_10": 7,
    "Band_10": 9,
    "Location_10": 8,
    "FactIntegrity_10": 9,
    "linkedin_url": "https://example.com/in/jordan-hale",
    "fact_check": "Verified",
    "waiver": "No",
}


def write_xlsx(tmp: Path, candidates, **meta) -> Path:
    out = tmp / "out.xlsx"
    payload = tmp / "in.json"
    payload.write_text(json.dumps({"profile": "data-platform-engineer", "candidates": candidates, **meta}))
    m.main(["--input", str(payload), "--out", str(out), "--check"])
    return out


def sheet1(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        return zf.read("xl/worksheets/sheet1.xml").decode("utf-8")


class WriteScorecardTests(unittest.TestCase):
    def test_total_is_sum_formula_not_literal(self):
        with tempfile.TemporaryDirectory() as raw:
            path = write_xlsx(Path(raw), [JORDAN])
            xml = sheet1(path)
            self.assertIn("<f>SUM(H2:N2)</f>", xml)
            self.assertNotRegex(xml, r'<c r="F2"[^>]*>\s*<v>')

    def test_file_and_linkedin_are_hyperlinks(self):
        with tempfile.TemporaryDirectory() as raw:
            path = write_xlsx(Path(raw), [JORDAN])
            xml = sheet1(path)
            self.assertIn("HYPERLINK(&quot;resumes/jordan-hale.pdf&quot;", xml)
            self.assertIn("HYPERLINK(&quot;https://example.com/in/jordan-hale&quot;", xml)

    def test_file_display_uses_basename_not_txt(self):
        with tempfile.TemporaryDirectory() as raw:
            path = write_xlsx(Path(raw), [JORDAN])
            xml = sheet1(path)
            self.assertIn("jordan-hale.pdf", xml)
            self.assertNotIn("jordan-hale.txt", xml)

    def test_two_sheets_named(self):
        with tempfile.TemporaryDirectory() as raw:
            path = write_xlsx(Path(raw), [JORDAN])
            with zipfile.ZipFile(path) as zf:
                wb = zf.read("xl/workbook.xml").decode("utf-8")
                self.assertIn('name="Candidates"', wb)
                self.assertIn('name="Scorecard"', wb)
                key = zf.read("xl/worksheets/sheet2.xml").decode("utf-8")
            self.assertIn("data-platform-engineer", key)
            self.assertIn("Overlays never change Total", key)

    def test_xml_special_chars_escaped(self):
        row = dict(JORDAN)
        row["name"] = 'Ann & "Kit" <Jr>'
        row["notes"] = "a < b & c"
        with tempfile.TemporaryDirectory() as raw:
            path = write_xlsx(Path(raw), [row])
            xml = sheet1(path)
            self.assertIn("Ann &amp; &quot;Kit&quot; &lt;Jr&gt;", xml)
            self.assertNotIn("Ann & ", xml)

    def test_factor_out_of_range_fails(self):
        row = dict(JORDAN)
        row["Pipelines_25"] = 26
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            payload = tmp / "in.json"
            payload.write_text(json.dumps({"candidates": [row]}))
            with self.assertRaises(SystemExit):
                m.main(["--input", str(payload), "--out", str(tmp / "out.xlsx")])

    def test_missing_file_fails(self):
        row = dict(JORDAN)
        del row["file"]
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            payload = tmp / "in.json"
            payload.write_text(json.dumps({"candidates": [row]}))
            with self.assertRaises(SystemExit):
                m.main(["--input", str(payload), "--out", str(tmp / "out.xlsx")])

    def test_omitted_factor_fails(self):
        row = dict(JORDAN)
        del row["Pipelines_25"]
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            payload = tmp / "in.json"
            payload.write_text(json.dumps({"candidates": [row]}))
            with self.assertRaises(SystemExit) as ctx:
                m.main(["--input", str(payload), "--out", str(tmp / "out.xlsx")])
            self.assertIn("Pipelines_25", str(ctx.exception))

    def test_non_numeric_factor_fails(self):
        row = dict(JORDAN)
        row["Pipelines_25"] = "22 pts"
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            payload = tmp / "in.json"
            payload.write_text(json.dumps({"candidates": [row]}))
            with self.assertRaises(SystemExit) as ctx:
                m.main(["--input", str(payload), "--out", str(tmp / "out.xlsx")])
            self.assertIn("Pipelines_25", str(ctx.exception))

    def test_empty_factor_fails(self):
        row = dict(JORDAN)
        row["Cloud_15"] = ""
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            payload = tmp / "in.json"
            payload.write_text(json.dumps({"candidates": [row]}))
            with self.assertRaises(SystemExit):
                m.main(["--input", str(payload), "--out", str(tmp / "out.xlsx")])

    def test_sort_puts_waiver_before_other_out(self):
        out_row = {
            "name": "Riley Chen",
            "file": "resumes/riley-chen.pdf",
            "tier": "Out",
            "decision": "Out",
            "Pipelines_25": 10,
            "CoreStack_20": 12,
            "Cloud_15": 8,
            "Extras_10": 4,
            "Band_10": 6,
            "Location_10": 8,
            "FactIntegrity_10": 0,
            "waiver": "No",
        }
        waiver = {
            "name": "Avery Kim",
            "file": "resumes/avery-kim.pdf",
            "tier": "Out",
            "decision": "Waiver candidate",
            "Pipelines_25": 16,
            "CoreStack_20": 15,
            "Cloud_15": 11,
            "Extras_10": 8,
            "Band_10": 3,
            "Location_10": 9,
            "FactIntegrity_10": 9,
            "waiver": "Yes — years knockout only",
        }
        with tempfile.TemporaryDirectory() as raw:
            path = write_xlsx(Path(raw), [out_row, JORDAN, waiver])
            xml = sheet1(path)
            jordan_at = xml.index("Jordan Hale")
            avery_at = xml.index("Avery Kim")
            riley_at = xml.index("Riley Chen")
            self.assertLess(jordan_at, avery_at)
            self.assertLess(avery_at, riley_at)

    def test_sample_csv_roundtrip_sums(self):
        self.assertTrue(SAMPLE_CSV.is_file(), SAMPLE_CSV)
        with tempfile.TemporaryDirectory() as raw:
            out = Path(raw) / "sample.xlsx"
            m.main([
                "--input", str(SAMPLE_CSV),
                "--out", str(out),
                "--profile", "data-platform-engineer",
                "--jd", "sample-jd.md",
                "--check",
            ])
            xml = sheet1(out)
            self.assertIn("<f>SUM(H2:N2)</f>", xml)
            self.assertIn("<f>SUM(H3:N3)</f>", xml)
            self.assertIn("<f>SUM(H4:N4)</f>", xml)
            self.assertIn("<f>SUM(H5:N5)</f>", xml)
            # Factor cells for Jordan (row 2) — 22+18+13+7+9+8+9 = 86
            self.assertIn(">22</v>", xml)
            self.assertIn("Cap P1 → P2", xml)
            self.assertIn("Waiver candidate", xml)
            self.assertIn("Contradicted", xml)

    def test_resolve_file_href_beside_workbook(self):
        examples = Path(__file__).resolve().parent.parent / "examples"
        self.assertEqual(
            m.resolve_file_href("resumes/jordan-hale.md", examples),
            "resumes/jordan-hale.md",
        )
        self.assertEqual(
            m.resolve_file_href("examples/resumes/jordan-hale.md", examples),
            "resumes/jordan-hale.md",
        )
        self.assertTrue((examples / "resumes/jordan-hale.md").is_file())

    def test_computed_total_matches_seven_factors(self):
        self.assertEqual(m.computed_total(JORDAN, m.FACTORS_DEFAULT), 86)
        self.assertEqual(
            m.computed_total(
                {
                    "Pipelines_25": 24,
                    "CoreStack_20": 19,
                    "Cloud_15": 14,
                    "Extras_10": 6,
                    "Band_10": 4,
                    "Location_10": 8,
                    "FactIntegrity_10": 9,
                },
                m.FACTORS_DEFAULT,
            ),
            84,
        )


if __name__ == "__main__":
    unittest.main()
