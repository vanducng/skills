#!/usr/bin/env python3
"""Unit tests for the parts of vlog.py that need no footage: naming, view filters, sound flags."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import vlog  # noqa: E402


class Naming(unittest.TestCase):
    def test_good(self):
        self.assertEqual(vlog.check_name("tw26-d01-01-arrival", "Taiwan 2026 · Day 1 · Arrival"), [])

    def test_bad_stem(self):
        self.assertTrue(vlog.check_name("Taiwan_day1_arrival"))
        self.assertTrue(vlog.check_name("tw26-d1-01-arrival"))

    def test_day_mismatch(self):
        errs = vlog.check_name("tw26-d02-01-market", "Taiwan 2026 · Day 3 · Market")
        self.assertTrue(any("does not match" in e for e in errs))


class Views(unittest.TestCase):
    def test_dfisheye_uses_v360(self):
        f = vlog.view_filter({"yaw": 180, "fov": 100}, "dfisheye", 1920, 1080)
        self.assertIn("v360=input=dfisheye", f)
        self.assertIn("yaw=180.0", f)

    def test_insv_joins_streams(self):
        self.assertTrue(vlog.video_in("insv").startswith("[0:v:1][0:v:0]hstack"))
        self.assertEqual(vlog.video_in("flat"), "[0:v]")

    def test_flat_rotate(self):
        self.assertIn("transpose=clock", vlog.view_filter({"rotate": 90}, "flat", 1920, 1080))


class Sound(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "LRV_20261125_080000_01_001.transcript.json").write_text(json.dumps({
            "clip": "LRV_20261125_080000_01_001.lrv",
            "segments": [
                {"start": 1.0, "end": 3.0, "text": "nice view here"},
                {"start": 5.0, "end": 7.0, "text": "mật khẩu là 4821"},
                {"start": 8.0, "end": 9.0, "text": "say hi to Lan"},
            ]}))

    def edit(self, mute=()):
        return {"stem": "tw26-d01-01-test", "transcripts": str(self.tmp),
                "shots": [{"src": "/x/VID_20261125_080000_00_001.mp4", "in": 0, "out": 10, "mute": list(mute)}]}

    def test_flags_unmuted_password_and_name(self):
        rep = vlog.sound_report(self.edit(), self.tmp, ["Lan"])
        self.assertEqual([r["source"][0] for r in rep["flagged_unmuted"]], [5.0, 8.0])

    def test_mute_clears_flags(self):
        rep = vlog.sound_report(self.edit(mute=[[4.5, 9.5]]), self.tmp, ["Lan"])
        self.assertEqual(rep["flagged_unmuted"], [])

    def test_missing_transcript(self):
        e = self.edit()
        e["shots"][0]["src"] = "/x/VID_20261125_090000_00_002.mp4"
        self.assertTrue(vlog.sound_report(e, self.tmp, [])["missing"])

    def test_timelapse_is_silent(self):
        e = self.edit()
        e["shots"][0]["speed"] = 10
        rep = vlog.sound_report(e, self.tmp, ["Lan"])
        self.assertEqual(rep["lines"], [])


class ThumbLines(unittest.TestCase):
    def test_phrases_split_into_balanced_lines(self):
        self.assertEqual(vlog.thumb_lines(["TAXI TO", "TAIPEI"]), ["TAXI TO", "TAIPEI"])
        self.assertEqual(vlog.thumb_lines(["FIRST", "TIME", "TAIWAN"]), ["FIRST TIME", "TAIWAN"])
        self.assertEqual(vlog.thumb_lines(["ZHONGSHAN", "WALK"]), ["ZHONGSHAN", "WALK"])


if __name__ == "__main__":
    unittest.main()
