#!/usr/bin/env python3
"""Unit tests for the parts of vlog.py that need no footage: naming, view filters, sound flags."""
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import vlog  # noqa: E402

needs_pil = unittest.skipUnless(importlib.util.find_spec("PIL"), "needs Pillow")
needs_ffmpeg = unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")


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
                  "a master shot", "in the river", "in 2026", "meet at 10 30", "walk 12-15 minutes",
                  "about 10.5 km"):
            self.assertIsNone(vlog.FLAG_RE.search(s), s)
        for s in ("mật khẩu là 4821", "pay by Mastercard", "gọi cho anh", "call me", "đưa thẻ"):
            self.assertIsNotNone(vlog.FLAG_RE.search(s), s)

    def test_short_number_flags_only_beside_a_secret_word(self):
        f = self.tmp / "LRV_20261125_080000_01_001.transcript.json"
        f.write_text(json.dumps({"clip": "LRV_20261125_080000_01_001.lrv", "segments": [
            {"start": 1.0, "end": 2.0, "text": "we landed in 2026"},
            {"start": 3.0, "end": 4.0, "text": "the PIN is 4821"}]}))
        rep = vlog.sound_report(self.edit(), self.tmp, [])
        self.assertEqual([r["source"][0] for r in rep["flagged_unmuted"]], [3.0])

    def test_timelapse_is_silent(self):
        e = self.edit()
        e["shots"][0]["speed"] = 10
        rep = vlog.sound_report(e, self.tmp, ["Lan"])
        self.assertEqual(rep["lines"], [])


class Stills(unittest.TestCase):
    def test_still_shot_is_a_silent_card(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "map.png").write_bytes(b"png")
        p = tmp / "e.json"
        p.write_text(json.dumps({"stem": "tw26-d02-01-test", "title": "Taiwan 2026 · Day 2 · Test",
                                 "output_dir": str(tmp), "shots": [{"still": str(tmp / "map.png"), "dur": 4}]}))
        e, _ = vlog.load_edit(str(p))
        s = e["shots"][0]
        self.assertEqual((s["src"], s["in"], s["out"], s["audio"]), (str(tmp / "map.png"), 0.0, 4.0, 0))
        self.assertEqual(vlog.planned_duration(e), 4.0)
        self.assertEqual(vlog.sound_report(e, tmp, [])["missing"], [])

    def test_card_keeps_its_own_in_and_out(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "map.png").write_bytes(b"png")
        p = tmp / "e.json"
        p.write_text(json.dumps({"stem": "tw26-d02-01-test", "title": "Taiwan 2026 · Day 2 · Test", "output_dir": str(tmp),
                                 "shots": [{"src": str(p), "in": 0, "out": 5, "title": {"text": "T"}},
                                           {"still": str(tmp / "map.png"), "in": 0, "out": 6}]}))
        e, _ = vlog.load_edit(str(p), writing=False)
        vlog.use_style(e)
        self.assertIn("2.5 to 4 s", " | ".join(vlog.card_problems(e)))

    @needs_ffmpeg
    def test_silence_at_the_start_counts(self):
        out = Path(tempfile.mkdtemp()) / "g.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "anullsrc=d=4", "-f", "lavfi", "-i", "sine=d=4",
                        "-filter_complex", "[0][1]concat=n=2:v=0:a=1", str(out)], check=True)
        self.assertEqual(len(vlog.bed_gaps(out, 8.0)), 1)

    def test_card_and_caption_limits(self):
        vlog.use_style({})
        shot = lambda **k: {"src": "x", "in": 0, "out": 12, **k}
        ok = {"shots": [shot(title={"text": "Shifen"}), {"still": "m.png", "in": 0, "out": 3},
                        shot(caption="Lanterns up, wishes written"), shot(caption={"text": "The train", "at": 2})]}
        self.assertEqual(vlog.card_problems(ok), [])
        bad = {"shots": [shot(caption="On the opener"), {"still": "m.png", "in": 0, "out": 6},
                         {"still": "n.png", "in": 0, "out": 3}, shot(caption="x" * 43, title={"text": "T"}),
                         shot(caption={"text": "Late", "at": 11}), shot(caption="Close"), shot(caption="Too close")]}
        probs = " | ".join(vlog.card_problems(bad))
        for want in ("opening shot", "2.5 to 4 s", "over 42", "same shot", "ends after", "one map card", "less than 10 s apart"):
            self.assertIn(want, probs)
        card_text = {"shots": [shot(title={"text": "T"}), {"still": "m.png", "in": 0, "out": 3, "caption": "Shifen"}]}
        self.assertIn("a card draws no caption", " | ".join(vlog.card_problems(card_text)))

    @needs_pil
    def test_caption_box_is_centred_low_with_the_text_inside(self):
        from PIL import Image
        vlog.use_style({"style": {"caption": {"box": "#000000", "box_alpha": 1.0, "color": "#FFFFFF"}}})
        out = Path(tempfile.mkdtemp()) / "c.png"
        vlog.caption_png("Lanterns up, wishes written", 1920, 1080, out)
        alpha = Image.open(out).getchannel("A")
        x0, y0, x1, y1 = alpha.getbbox()
        self.assertLessEqual(abs((x0 + x1) / 2 - 960), 2)
        self.assertEqual(y1 - 1, 1080 - 112)  # getbbox ends one past the last row
        self.assertTrue(60 <= y1 - y0 <= 110, y1 - y0)
        inside = Image.open(out).convert("RGB").crop((x0 + 30, y0 + 10, x1 - 30, y1 - 10))
        self.assertEqual(inside.getextrema()[0][1], 255)


class TitleShade(unittest.TestCase):
    @needs_pil
    def test_shade_sits_in_the_lower_left_corner(self):
        from PIL import Image
        vlog.use_style({"style": {"title_shade": 0.55}})
        out = Path(tempfile.mkdtemp()) / "t.png"
        vlog.title_png({"text": ""}, 1920, 1080, out)
        a = Image.open(out).getchannel("A")
        self.assertGreater(a.getpixel((5, 1075)), 100)
        for corner in ((5, 5), (1915, 1075), (1915, 5)):
            self.assertEqual(a.getpixel(corner), 0, corner)
        vlog.use_style({})
        vlog.title_png({"text": ""}, 1920, 1080, out)
        self.assertIsNone(Image.open(out).getchannel("A").getbbox())


class People(unittest.TestCase):
    def test_track_eases_the_short_way_round(self):
        track = [[0, 170, 0], [2, -170, 10]]
        self.assertEqual(vlog.track_at(track, 0), (170.0, 0.0))
        y, p = vlog.track_at(track, 1)
        self.assertAlmostEqual(y, 180.0)
        self.assertAlmostEqual(p, 5.0)
        self.assertEqual(vlog.track_at(track, 5), (-170.0, 10.0))

    def test_empty_view_fails_only_with_people_elsewhere_or_flat(self):
        e = {"shots": [{"src": "a"}, {"src": "b"}, {"src": "c", "landmark": "waterfall"}, {"src": "d"}]}
        nobody = [{"t": t, "in_view": 0} for t in range(6)]
        missed = [{"t": t, "in_view": 0, "sphere": [[90.0, 0.0]]} for t in range(6)]
        empty360 = [{"t": t, "in_view": 0, "sphere": []} for t in range(6)]
        rep = {"shots": {"1": {"projection": "insv", "every": 1, "samples": missed},
                         "2": {"projection": "flat", "every": 1, "samples": nobody},
                         "3": {"projection": "flat", "every": 1, "samples": nobody},
                         "4": {"projection": "insv", "every": 1, "samples": empty360}}}
        probs = vlog.people_problems(e, rep)
        self.assertEqual([p.split(":")[0] for p in probs], ["shot 1", "shot 2"])
        self.assertIn("view.track", probs[0])
        self.assertTrue(vlog.people_problems(e, None))

    def test_track_filter_sends_relative_steps(self):
        out = Path(tempfile.mkdtemp()) / "c.cmd"
        f = vlog.track_filter({"track": [[0, 0, 0], [1, 90, 0]]}, 1920, 1080, 1.0, 10, out)
        self.assertIn("yaw=0.0", f)
        steps = [float(l.split("yaw ")[1].split(",")[0]) for l in out.read_text().splitlines()]
        self.assertAlmostEqual(sum(steps), 90.0, places=3)


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

    @needs_pil
    def test_upright_turns_a_photo_by_its_exif_orientation(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "p.jpg"
            ex = Image.Exif()
            ex[0x0112] = 6
            Image.new("RGB", (40, 30)).save(src, exif=ex)
            with Image.open(vlog.upright(src, Path(td))) as im:
                self.assertEqual(im.size, (30, 40))
            plain = Path(td) / "q.jpg"
            Image.new("RGB", (40, 30)).save(plain)
            self.assertEqual(vlog.upright(plain, Path(td)), plain)

    def test_pose_at_follows_a_pan_and_a_track(self):
        pan = {"yaw": 0, "yaw_end": 90, "pitch": -10, "fov": 85}
        self.assertEqual(vlog.pose_at(pan, 0, 4)["yaw"], 0)
        self.assertAlmostEqual(vlog.pose_at(pan, 2, 4)["yaw"], 45)
        self.assertEqual(vlog.pose_at(pan, 4, 4)["yaw"], 90)
        self.assertNotIn("yaw_end", vlog.pose_at(pan, 2, 4))
        tr = {"track": [[0, 170, 0], [2, -170, 0]], "fov": 85}
        self.assertAlmostEqual(vlog.pose_at(tr, 1, 2)["yaw"], 180)

    def test_stitched_builds_the_command_once_and_caches_it(self):
        calls = []
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "VID_x.insv"
            src.write_bytes(b"x")
            home = Path(td) / "home"

            def fake_run(cmd, **kw):
                calls.append(cmd)
                Path(cmd[cmd.index(str(vlog.STITCH)) + 4]).write_bytes(b"mp4")

            with mock.patch.object(vlog, "run", fake_run), \
                    mock.patch.object(vlog, "media_info", lambda p: {}), \
                    mock.patch.object(vlog, "projection_of", lambda i, p: "insv"), \
                    mock.patch.object(vlog.shutil, "which", lambda n: "/usr/bin/" + n), \
                    mock.patch.object(vlog.Path, "home", lambda: home):
                shot = {"src": str(src), "in": 90, "out": 96}
                view = {"yaw": -100, "pitch": -30, "fov": 95, "stitch": "flow", "lens_fov": 195}
                a = vlog.stitched(shot, view, 1920, 1080, 25)
                b = vlog.stitched(shot, view, 1920, 1080, 25)
                c = vlog.stitched(shot, {**view, "yaw": -90}, 1920, 1080, 25)
            self.assertEqual(a, b)
            self.assertNotEqual(a, c)
            self.assertEqual(len(calls), 2)
            cmd = calls[0]
            self.assertEqual(cmd[cmd.index("--yaw") + 1], "-100.0")
            self.assertEqual(cmd[cmd.index("--lens-fov") + 1], "195.0")
            with mock.patch.object(vlog, "projection_of", lambda i, p: "insv"), \
                    mock.patch.object(vlog, "media_info", lambda p: {}):
                with self.assertRaises(SystemExit):
                    vlog.stitched(shot, {**view, "yaw_end": 0}, 1920, 1080, 25)

    def test_subject_problems_cut_subject_and_short_sign(self):
        cut = {"people": 1, "sign": 0, "object": 0}
        whole = {"people": 0, "sign": 0, "object": 0}
        rep = {"shots": {
            "1": {"samples": [{"t": 0, "cut": cut, "words": 0}, {"t": 1, "cut": cut, "words": 0}]},
            "2": {"samples": [{"t": 0, "cut": cut, "words": 0}, {"t": 1, "cut": whole, "words": 0}]},
            "3": {"samples": [{"t": 0, "cut": whole, "words": 9}]}}}
        e = {"shots": [{"in": 0, "out": 2}, {"in": 0, "out": 2}, {"in": 0, "out": 3, "subject": "sign"}]}
        probs = vlog.subject_problems(e, rep)
        self.assertEqual([p.split(":")[0] for p in probs], ["shot 1", "shot 3"])
        for place in ({"subject": "place"}, {"landmark": "the old street"}):
            e["shots"][0] = {"in": 0, "out": 2, **place}
            self.assertEqual([p.split(":")[0] for p in vlog.subject_problems(e, rep)], ["shot 3"])
        self.assertIn("4.7 s", probs[1])

    def test_edge_cuts_sees_a_face_past_the_edge_in_the_wider_look(self):
        wide = {"faces": [[0.8, 0.4, 0.1, 0.1]], "people": [], "text": [], "objects": []}
        around = vlog.in_view(wide, 2.0)  # 0.8-0.9 in the wide look is 1.1-1.3 in the view: outside it
        self.assertEqual(vlog.edge_cuts({}, around)["people"], 0)
        wide["faces"] = [[0.7, 0.4, 0.1, 0.1]]  # 0.9-1.1: half out
        self.assertEqual(vlog.edge_cuts({}, vlog.in_view(wide, 2.0))["people"], 1)
        self.assertEqual(vlog.edge_cuts({"people": [[0.3, 0.5, 0.2, 0.6]]})["people"], 0)  # body out at the bottom

    def test_fit_step_aims_at_the_boxes_and_sizes_the_view(self):
        v = vlog.fit_step({"yaw": 0, "pitch": 0, "fov": 90}, [[0.7, 0.4, 0.2, 0.2]])
        self.assertGreater(v["yaw"], 20)
        self.assertLessEqual(v["fov"], vlog.MAX_FOV)

    @needs_ffmpeg
    def test_seam_problems_flags_a_view_on_the_lens_join(self):
        e = {"shots": [{"view": {"yaw": -110, "pitch": -30, "fov": 95}},  # the Duc flies 1:08 view
                       {"view": {"yaw": 0, "pitch": -30, "fov": 95}},
                       {"view": {"yaw": 170, "fov": 85, "yaw_end": 120}},
                       {"view": {"x": 0.5}},
                       {"view": {"fov": 85, "yaw_end": -90}}]}
        self.assertEqual([p.split(":")[0] for p in vlog.seam_problems(e)], ["shot 1", "shot 3", "shot 5"])

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
