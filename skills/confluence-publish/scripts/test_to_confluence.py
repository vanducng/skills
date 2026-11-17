#!/usr/bin/env python3
"""to_confluence.py rules, and the eval checks: each passes a good run and fails the usual bad one.

    python3 skills/confluence-publish/scripts/test_to_confluence.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVALS = HERE.parent / "evals"
sys.path.insert(0, str(HERE))
from to_confluence import convert, lint  # noqa: E402

NEW_ID = "c3e1f9a7-6b2d-4e8f-a1c4-5d7b9e0f2a02"
OLD_ID = "0a4b7c1d-2e3f-4a5b-8c6d-9e0f1a2b3c01"


def run(html, widths=None, media=None, page_id="42", base=HERE):
    return convert(html, widths or {}, media or {}, page_id, base)


class Convert(unittest.TestCase):
    def test_marks_classes_pills_panels(self):
        body, errors, _ = run(
            '<div class="note">Heads up <b>now</b></div>'
            '<p class=lede><i>x</i> <span class="pill amber">Late</span> <span class="badge">n/a</span></p>'
            '<div class="callout warning"><p>careful</p></div>'
        )
        self.assertEqual(errors, [])
        self.assertIn('<div data-type="panel-info"><p>Heads up <strong>now</strong></p></div>', body)
        self.assertIn('<span data-type="status" data-color="yellow">Late</span>', body)
        self.assertIn('<span data-type="status" data-color="neutral">n/a</span>', body)
        self.assertIn('<div data-type="panel-warning"><p>careful</p></div>', body)
        self.assertNotIn("class", body)
        self.assertEqual(lint(body), [])

    def test_inline_code_sheds_marks_code_block_keeps_language(self):
        body, _, _ = run('<p><strong>run <code>make</code> now</strong></p><pre class=x><code class="hl language-sql"><span class=k>select</span> 1</code></pre>')
        self.assertIn("<strong>run </strong><code>make</code><strong> now</strong>", body)
        self.assertIn('<pre><code class="language-sql">select 1</code></pre>', body)
        self.assertEqual(lint(body), [])

    def test_every_cell_gets_a_width_by_column(self):
        body, _, estimated = run(
            "<table><tr><th>Key</th><th>Notes</th><th>Status</th></tr>"
            '<tr><td rowspan="2">A-1</td><td colspan="2">spans two</td></tr>'
            "<tr><td>second</td><td>ok</td></tr></table>",
            widths={"key": 100, "STATUS": 90},
        )
        self.assertIn('<table data-layout="full-width">', body)
        self.assertIn('<td rowspan="2" data-colwidth="100">', body)
        notes = estimated["Notes"]
        self.assertIn(f'<td colspan="2" data-colwidth="{notes},90">', body)
        self.assertIn(f'<td data-colwidth="{notes}">second</td><td data-colwidth="90">ok</td>', body)
        self.assertNotIn("Key", estimated)
        self.assertEqual(lint(body), [])

    def test_images_and_svg_become_pixel_width_media(self):
        fixture = EVALS / "02-charts-full-width" / "fixture"
        html = (fixture / "report.html").read_text()
        media = {"burndown.png": {"fileId": "f1"}, "svg-1": {"fileId": "f2", "width": 2400, "height": 1400}}
        body, errors, _ = run(html, media=media, page_id="7", base=fixture)
        self.assertEqual(errors, [])
        self.assertIn(
            '<figure data-type="media-single" data-layout="center" data-width="1800" data-width-type="pixel">'
            '<div data-type="media" data-media-type="file" data-id="f1" data-collection="contentId-7" '
            'data-alt="Sprint burndown" data-width="2400" data-height="1200"></div>',
            body,
        )
        self.assertIn("<figcaption>Burndown, sprint 42</figcaption>\n</figure>", body)
        self.assertIn('data-id="f2" data-collection="contentId-7" data-alt="Velocity by sprint"', body)
        self.assertNotIn("<svg", body)
        self.assertNotIn("<text", body)

    def test_unmapped_chart_is_an_error(self):
        _, errors, _ = run('<p><img src="a.png"></p><svg><rect/></svg>')
        self.assertEqual(len(errors), 2)

    def test_image_in_paragraph_splits_it(self):
        body, _, _ = run('<p>see <img src="a.png" alt="A"> above</p>', media={"a.png": {"fileId": "f", "width": 800, "height": 400}})
        self.assertIn('<p>see </p><figure data-type="media-single" data-layout="center" data-width="800"', body)
        self.assertIn("</figure><p> above</p>", body)

    def test_output_is_stable_when_converted_again(self):
        fixture = EVALS / "01-report-to-body" / "fixture"
        once, _, _ = run((fixture / "report.html").read_text())
        twice, _, _ = run(once)
        self.assertEqual(once, twice)

    def test_lint_flags_what_confluence_mangles(self):
        bad = '<b>x</b><p class=a>y</p><table><tr><td>1</td></tr></table><figure data-width-type="percentage"></figure><img src="c.png"><strong><code>z</code></strong>'
        self.assertEqual(len(lint(bad)), 7)


def check(scenario: str, files: dict[str, str], reply: str = "") -> int:
    """Runs a scenario's checks.sh on a fake run: the fixture plus `files` written by "the agent"."""
    work = Path(tempfile.mkdtemp())
    orig, out = work / "orig", work / "run"
    fixture = EVALS / scenario / "fixture"
    for d in (orig, out):
        shutil.copytree(fixture, d) if fixture.is_dir() else d.mkdir()
    for name, body in files.items():
        (out / name).write_text(body)
    (work / "reply.txt").write_text(reply)
    env = {"PATH": os.environ["PATH"], "EVAL_OUTPUT": str(work / "reply.txt"), "EVAL_ORIG": str(orig)}
    done = subprocess.run(["sh", str(EVALS / scenario / "checks.sh")], cwd=out, env=env, capture_output=True, text=True)
    shutil.rmtree(work)
    return done.returncode


class Checks(unittest.TestCase):
    def test_01_report(self):
        fixture = EVALS / "01-report-to-body" / "fixture"
        good, _, _ = run((fixture / "report.html").read_text(), widths={"Ticket": 120, "Status": 110, "Summary": 480})
        self.assertEqual(check("01-report-to-body", {"body.html": good}), 0)
        raw = (fixture / "report.html").read_text()
        self.assertEqual(check("01-report-to-body", {"body.html": raw}), 1)
        self.assertEqual(check("01-report-to-body", {"body.html": good.replace(' data-colwidth="480"', "")}), 1)

    def test_02_charts(self):
        fixture = EVALS / "02-charts-full-width" / "fixture"
        media = {
            "charts/burndown.png": {"fileId": "5d0c2a3e-1b7f-4c55-9a51-2f6c0e8b1a01"},
            "#velocity": {"fileId": "5d0c2a3e-1b7f-4c55-9a51-7d9e4f2a3b02", "file": "charts/velocity.png"},
        }
        good, errors, _ = run((fixture / "report.html").read_text(), media=media, page_id="100002", base=fixture)
        self.assertEqual(errors, [])
        self.assertEqual(check("02-charts-full-width", {"body.html": good}), 0)
        thumb = good.replace('data-width="1800" data-width-type="pixel"', 'data-width="100" data-width-type="percentage"')
        self.assertEqual(check("02-charts-full-width", {"body.html": thumb}), 1)

    def test_03_reupload(self):
        old = (EVALS / "03-reupload-update" / "fixture" / "body.html").read_text()
        sh = (
            "TOKEN=$(scripts/twgj.sh --from get.out | jq -r .data.snapshotToken)\n"
            'twg confluence content update --id 100003 --snapshot-token "$TOKEN" --body-file body.html '
            "--format html --ack-body-formats --content-width max -y\n"
        )
        self.assertEqual(check("03-reupload-update", {"body.html": old.replace(OLD_ID, NEW_ID), "publish.sh": sh}), 0)
        self.assertEqual(check("03-reupload-update", {"publish.sh": sh}), 1)
        self.assertEqual(check("03-reupload-update", {"body.html": old.replace(OLD_ID, NEW_ID), "publish.sh": sh.replace(" --content-width max", "")}), 1)

    def test_04_rename_is_clean(self):
        sh = 'twg confluence content update --id 100004 --snapshot-token snap-91bd04aa7c --title "Sprint 42 report (final)" -y\n'
        self.assertEqual(check("04-rename-only", {"rename.sh": sh}), 0)
        resend = sh.replace(" -y", " --body-file body.html --format html --ack-body-formats -y")
        self.assertEqual(check("04-rename-only", {"rename.sh": resend}), 1)


if __name__ == "__main__":
    unittest.main()
