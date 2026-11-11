#!/usr/bin/env python3
"""The eval checks are deterministic: each passes a hand-written good run and fails the usual bad ones.

    python3 skills/bi-dash/evals/test_checks.py
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def check(scenario: str, reply: str, files: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """Runs a scenario's checks.sh on a fake run: the fixture, plus `files` written by "the agent", and its reply."""
    work = Path(tempfile.mkdtemp())
    orig, run = work / "orig", work / "run"
    fixture = HERE / scenario / "fixture"
    for d in (orig, run):
        shutil.copytree(fixture, d) if fixture.is_dir() else d.mkdir()
    for name, body in (files or {}).items():
        (run / name).parent.mkdir(parents=True, exist_ok=True)
        (run / name).write_text(body)
    (work / "out.txt").write_text(reply)
    env = {"PATH": os.environ["PATH"], "EVAL_OUTPUT": str(work / "out.txt"), "EVAL_ORIG": str(orig)}  # no TMPDIR, as on Linux
    done = subprocess.run(["sh", str(HERE / scenario / "checks.sh")], cwd=run, env=env, capture_output=True, text=True)
    shutil.rmtree(work)
    return done


SHEET = """| # | Question | Audience | Decision supported | Metric (definition) | Grain | Filters | Refresh | Time to read |
|---|---|---|---|---|---|---|---|---|
| 1 | Are customers coming back? | ? | ? | repeat-purchase rate: customers with 2+ orders / customers with 1+ order | month | region | daily | 10 s |
"""
FIELD_MAP = """| Mockup field | Model.column | Status | Note |
|---|---|---|---|
| order date (week) | orders.created_at / orders.order_date | variant | two candidates: UTC timestamp or local day; choose one |
| region | orders.region | exists | 4 values, no nulls |
| sales channel | - | missing | no column holds the channel |
"""


class Checks(unittest.TestCase):
    def ok(self, done):
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def bad(self, done, why):
        self.assertNotEqual(done.returncode, 0, done.stdout)
        self.assertIn(why, done.stdout)

    def test_01_sheet_and_questions_pass_and_a_chart_fails(self):
        ask = "Who is the audience for this, and what decision will it support?"
        self.ok(check("01-dashboard-ask", ask, {"question-sheet.md": SHEET}))
        self.bad(check("01-dashboard-ask", ask, {"question-sheet.md": SHEET, "dashboard.html": "<svg/>"}), "built something")
        self.bad(check("01-dashboard-ask", "Here is your dashboard.", {"dashboard.py": "import plotly"}), "built something")
        self.bad(check("01-dashboard-ask", ask), "no question sheet")
        self.ok(check("01-dashboard-ask", "1. Who reads this dashboard, and how often?\n2. What will they decide when the rate drops?", {"question-sheet.md": SHEET}))
        self.ok(check("01-dashboard-ask", "1. Who reads this dashboard?\n2. What will they do differently when the rate is high or low?", {"question-sheet.md": SHEET}))
        # Seen in a with-skill run (Opus): the decision asked as "what do they do when ...".
        self.ok(check("01-dashboard-ask", "1. Who reads this and how often, and what do they do when the number is high or low?", {"question-sheet.md": SHEET}))
        self.ok(check("01-dashboard-ask", "Who reads it, and what would they do if repeat buyers fell?", {"question-sheet.md": SHEET}))
        # Broad words alone are not a decision question.
        self.bad(check("01-dashboard-ask", "Who reads this? Which colours do you like?", {"question-sheet.md": SHEET}), "does not ask")
        self.bad(check("01-dashboard-ask", "Who reads this? Any action items for me? What do you think?", {"question-sheet.md": SHEET}), "does not ask")
        self.bad(check("01-dashboard-ask", "Who reads this? I will do it when the data loads.", {"question-sheet.md": SHEET}), "does not ask")
        self.bad(check("01-dashboard-ask", "Done.", {"question-sheet.md": SHEET}), "does not ask")

    def test_02_field_map_flags_the_missing_and_the_variant_field(self):
        self.ok(check("02-field-map", "Field map written.", {"field-map.md": FIELD_MAP}))
        self.bad(check("02-field-map", "Channel is missing; dates are created_at and order_date."), "sales channel missing")
        no_variant = FIELD_MAP.replace("orders.created_at / orders.order_date | variant | two candidates: UTC timestamp or local day; choose one", "orders.created_at | exists | ")
        self.bad(check("02-field-map", "ok", {"field-map.md": no_variant}), "both candidate date columns")
        self.bad(check("02-field-map", "ok", {"field-map.md": FIELD_MAP, "dashboard.html": "<p/>"}), "built something")

    def test_03_reconciliation_states_the_tolerance_and_fails(self):
        good = "Not ready. Orders: 1150 vs 1250 in the finance report, 8.0% short, outside the 1% tolerance. Revenue is within 0.4%."
        self.ok(check("03-kpi-off-reference", good))
        self.ok(check("03-kpi-off-reference", "See reconciliation.md", {"reconciliation.md": good}))
        table = ("Not ready to publish.\n\n| KPI | Ours | Reference | Gap % | Tolerance | Result |\n|---|---|---|---|---|---|\n"
                 "| Orders | 1,150 | 1,250 | -8.0% | 1% (default) | **Fail** |\n| Revenue | 71,707 | 71,994 | -0.40% | 1% | Pass |\n")
        self.ok(check("03-kpi-off-reference", table))
        self.ok(check("03-kpi-off-reference", table.replace("-8.0%", "-8.00%")))
        self.ok(check("03-kpi-off-reference", table.replace("-8.0%", "-8.7% of ours")))
        self.bad(check("03-kpi-off-reference", table.replace("1% (default)", "agree with finance").replace("| 1% |", "| ? |")), "no tolerance")
        self.bad(check("03-kpi-off-reference", "Not ready: orders are 8% below the finance report."), "no tolerance")
        self.bad(check("03-kpi-off-reference", "Ready to publish. Tolerance 1%, orders 8% off but fine."), "not called a failure")
        self.bad(check("03-kpi-off-reference", "Not ready; 100 orders short, tolerance 1%."), "8% gap")

    def test_04_a_plain_number_is_answered_without_the_flow(self):
        self.ok(check("04-plain-number", "216 orders last week (2026-03-02 to 2026-03-08)."))
        self.bad(check("04-plain-number", "About 200."), "216")
        self.bad(check("04-plain-number", "216. I also drafted a question sheet.", {"question-sheet.md": SHEET}), "dashboard flow")
        self.bad(check("04-plain-number", "216. Want a question sheet and a mockup for a dashboard?"), "starts the dashboard flow")


if __name__ == "__main__":
    unittest.main()
