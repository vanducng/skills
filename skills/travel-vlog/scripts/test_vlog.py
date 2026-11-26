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

    def test_english_the_is_not_a_card_and_doubtful_hits_are_listen(self):
        f = self.tmp / "LRV_20261125_080000_01_001.transcript.json"
        f.write_text(json.dumps({"clip": "LRV_20261125_080000_01_001.lrv", "segments": [
            {"start": 1.0, "end": 2.0, "text": "look at the waterfall"},
            {"start": 3.0, "end": 4.0, "text": "đưa thẻ đây"},
            {"start": 5.0, "end": 6.0, "text": "1 2 3 4 5 6 7 8 9", "doubtful": True}]}))
        rep = vlog.sound_report(self.edit(), self.tmp, [])
        self.assertEqual([r["source"][0] for r in rep["flagged_unmuted"]], [3.0])
        self.assertEqual([r["source"][0] for r in rep["listen"]], [5.0])

    def test_ordinary_speech_stays_audible(self):
        for s in ("the view is nice", "we're going to the market", "locally famous", "a so-called night market",
                  "a master shot", "in the river"):
            self.assertIsNone(vlog.FLAG_RE.search(s), s)
        for s in ("mật khẩu là 4821", "pay by Mastercard", "gọi cho anh", "call me", "đưa thẻ"):
            self.assertIsNotNone(vlog.FLAG_RE.search(s), s)

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


class Picture(unittest.TestCase):
    def test_wide_360_view_is_refused(self):
        e = {"shots": [{"view": {"fov": 110}}, {"view": {"fov": 85, "fov_end": 100}}, {"view": {"type": "tiny-planet", "fov": 160}}]}
        self.assertEqual(len(vlog.fov_problems(e)), 2)
        self.assertEqual(vlog.fov_problems({"shots": [{"view": {"fov": 85}}]}), [])

    def test_non_square_pixels(self):
        portrait = {"width": 1920, "height": 1080, "sar": (81, 256)}
        self.assertIn("scale=trunc(iw*81/256/2)*2:ih,setsar=1", vlog.square_pixels(portrait))
        self.assertTrue(vlog.is_portrait(portrait))
        self.assertEqual(vlog.square_pixels({"width": 1920, "height": 1080, "sar": (1, 1)}), "")
        self.assertFalse(vlog.is_portrait({"width": 1920, "height": 1080, "sar": (1, 1)}))
        self.assertTrue(vlog.is_portrait({"width": 1920, "height": 1080, "sar": (1, 1)}, {"rotate": 90}))
        self.assertIn("gblur", vlog.view_filter({}, "flat", 1920, 1080, portrait=True))
        self.assertNotIn("gblur", vlog.view_filter({"fit": "crop"}, "flat", 1920, 1080, portrait=True))
        rolled = vlog.view_filter({"roll": 10}, "flat", 1920, 1080, portrait=True)
        self.assertLess(rolled.index("rotate="), rolled.index("crop=w='iw/"))

    def test_style_block(self):
        vlog.use_style({"style": {"text": "#F6F1E7", "badge": "#E8553D"}})
        self.assertEqual(vlog.rgb(vlog.STYLE["text"]), (246, 241, 231))
        self.assertEqual(vlog.rgb(vlog.STYLE["badge"], 255), (232, 85, 61, 255))
        self.assertEqual(vlog.STYLE["accent"], "#FFD666")
        vlog.use_style({})

    def test_camera_holder_screen_time(self):
        shot = lambda d, h=False: {"in": 0, "out": d, **({"holder": True} if h else {})}
        e = {"shots": [shot(3, True), shot(30), shot(3, True), shot(30), shot(30)]}
        self.assertEqual(vlog.holder_problems(e), [])
        e["shots"][1] = shot(3, True)
        self.assertTrue(any("in a row" in p for p in vlog.holder_problems(e)))
        e = {"shots": [shot(4, True), shot(1), shot(4, True), shot(1), shot(4, True), shot(10)]}
        self.assertTrue(any("on screen 12.0 s" in p for p in vlog.holder_problems(e)))
        self.assertTrue(vlog.holder_problems({"shots": [], "thumbnail": {"holder": True}}))

    def test_lens_filter(self):
        self.assertEqual(vlog.lens_filter(None, 1920, 1080), "")
        self.assertIn("lenscorrection", vlog.lens_filter("x5", 1920, 1080))
        self.assertIn("k1=0.2", vlog.lens_filter({"k1": 0.2, "k2": 0.0, "crop": 1.2}, 1920, 1080))


if __name__ == "__main__":
    unittest.main()
