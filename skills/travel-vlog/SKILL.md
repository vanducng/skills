---
name: travel-vlog
description: "Turns a day of travel footage from a 360 or action camera (Insta360 X-series .insv/.lrv, GoPro, phone) into short topic videos for YouTube: index every clip into contact sheets and timestamped notes with starred moments, split the day into topics, write one edit list per video with a hook in the first seconds, reframe 360 shots headless with ffmpeg v360, cut, lay music under the camera sound with ducking, normalise to -14 LUFS, make a 1280x720 thumbnail with a face and two to four big words, name everything by one convention, and verify the render and thumbnail before upload. Use when the user says 'make a travel video', 'cut today's footage', 'day 1 video', 'vlog from my Insta360 clips', 'reframe this 360 clip', 'make the thumbnail', 'name the episodes' or 'is this video ready to upload'. Not for HTML motion graphics or explainers (video), AI-generated footage (omnimedia) or photo stitching with the Insta360 SDK."
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
---

# travel-vlog

A day of footage becomes short videos, one topic each. `scripts/vlog.py` runs the fragile steps. Sources: [research](references/research.md), [source repos](references/sources.md).

## Rules

1. **Originals are read-only.** Work files go outside the footage and any repo.
2. **Look before cutting.** `index` the proxies, open every sheet, write each `<clip>.md`: one line per moment, `*` on key moments, `!` on private ones.
3. **One topic per video, 3 to 6 minutes, one arc:** arrive, explore, a moment, leave. Shots of 3 to 8 s. Owner taste wins.
4. **A taste of the place.** Open each scene on an establishing shot held 4 to 6 s with real ambient sound; the first seconds may tease the best moment.
5. **One name everywhere.** Stem `<series>-d<dd>-<nn>-<topic-slug>` (for example `tw26-d01-01-arrival`), title `<Series> · Day <d> · <Topic>`; the `.mp4`, the thumbnail `.jpg`, the edit list and the recipe share the stem. Check with `vlog.py name <stem> --title "..."`.
6. **Undistorted, one look.** 360 views at 75 to 90° (over 95° is refused), level with `roll`; straighten flat clips with `lens` (`"x5"`); portrait clips fit over a blur. One `grade` and one `style` from the channel's written style guide. Look at a full-size still of every shot.
7. **No seam.** The two lenses meet at yaw ±90. A subject within 50° of it is shot with `view.stitch: "flow"` (the `.insv` master; aligns the join, then blends), aimed straight at it: aiming away cuts it. `verify` refuses an unstitched view on the join.
8. **Point the view at the people of the story,** or a named `landmark` when nobody is there. On 360, follow them with `view.track`; on flat footage, pick the ranges `find-people` lists. **The camera holder stays behind the camera:** tag their few seconds `holder`; `verify` caps them. A map card is a `still`; a `caption` names a place or a moment.
9. **Frame the whole subject.** Each shot names its `subject` (people, sign, object or `place`: a street, a crowd) and is aimed at its middle with fov = its width + 15% (`fit` on 360; a place by eye). No face or head touches an edge; a sign is whole, level and held 2 s + 0.3 s a word (max 5 s). Too wide: faces or text first, then a pan. `verify` fails an empty view, a cut subject and a short sign.
10. **Thumbnail: the place or the moment, not the camera holder, two to four big words,** the lower-right corner clear, one layout per series. Look at the phone-size preview.
11. **Sound.** Camera sound stays over a ducked music bed, about -14 LUFS. Music: unclaimed instrumental unless the owner accepts claims. Licence and credit in the edit list, title in the description.
12. **Privacy, picture.** Cut or `blur` any card, receipt, booking, passport, address, screen, live location or person who has not agreed, and keep it out of the title and description.
13. **Privacy, sound.** `transcribe` every clip, run `sound` on each edit list and read every audible line, listening to the ones marked doubtful (`LISTEN`: Whisper invents words over music and water). `mute` or cut passwords, money, booking or passport numbers, the hotel or an address, names of people who have not agreed (`private_names`), calls, private or tense moments, strangers close to the mic. When unsure, cut.
14. **Verify pixels.** `verify` must print `ok`; then open `<stem>.sheet.jpg` and the thumbnail.

## Workflow

```bash
V=scripts/vlog.py   # inside this skill
python3 $V index /footage/LRV_*.lrv --out WORK/index --every 8 --clock-offset-hours 1
python3 $V transcribe /footage/LRV_*.lrv --out WORK/index --language vi   # once per clip, cached
# read the sheets, fill WORK/index/<clip>.md, group the day into topics
# each edit list sets "transcripts": "WORK/index" so sound and verify find them
python3 $V find-people /footage/VID_*.mp4             # source ranges with people, for picking shots
python3 $V name tw26-d01-01-arrival --title "Taiwan 2026 · Day 1 · Arrival"
python3 $V sound  WORK/tw26-d01-01-arrival.json            # every audible line; exit 1 on an unmuted flag
python3 $V people WORK/tw26-d01-01-arrival.json           # people, signs, cut subjects per view (Apple Vision)
python3 $V fit /footage/VID_x.insv 258 --yaw -110 --pitch -30   # a 360 view holding the whole subject
python3 $V render WORK/tw26-d01-01-arrival.json --draft   # quick look, then without --draft
python3 $V thumb  WORK/tw26-d01-01-arrival.json
python3 $V verify WORK/tw26-d01-01-arrival.json           # exit 0 = ready to upload
```

`--clock-offset-hours` is local time minus the camera clock. Edit list fields: [references/edit-list.md](references/edit-list.md). 360 views (yaw, pitch, fov, pans, tiny planet) and the X5 file layout: [references/insta360-360.md](references/insta360-360.md).

## Upload

Use the `youtube-upload` skill. Confirm the signed-in account and channel first. Upload Private unless the owner says otherwise (Unlisted is public to anyone with the link), with the thumbnail, title, a short description (places, music credit) and the series playlist. Public, deleting and messages wait for the owner.

## Report

Per video: stem, length, loudness, music, privacy cuts, link.
