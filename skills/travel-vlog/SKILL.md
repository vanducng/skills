---
name: travel-vlog
description: "Turns a day of travel footage from a 360 or action camera (Insta360 X-series .insv/.lrv, GoPro, phone) into short topic videos for YouTube: index every clip into contact sheets and timestamped notes with starred moments, split the day into topics, write one edit list per video with a hook in the first seconds, reframe 360 shots headless with ffmpeg v360, cut, lay music under the camera sound with ducking, normalise to -14 LUFS, make a 1280x720 thumbnail with a face and two to four big words, name everything by one convention, and verify the render and thumbnail before upload. Use when the user says 'make a travel video', 'cut today's footage', 'day 1 video', 'vlog from my Insta360 clips', 'reframe this 360 clip', 'make the thumbnail', 'name the episodes' or 'is this video ready to upload'. Not for HTML motion graphics or explainers (video), AI-generated footage (omnimedia) or photo stitching with the Insta360 SDK."
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
---

# travel-vlog

A day of footage becomes several short videos, one topic each. Run `scripts/vlog.py` for the fragile steps; do not hand-roll ffmpeg. Rules come from the [research](references/research.md) and [three source repos](references/sources.md).

## Rules

1. **Originals are read-only.** Work files go to a folder outside the footage and outside any repo.
2. **Look before cutting.** Run `index` on the proxies, open every contact sheet, and write each `<clip>.md`: one line per moment (`mm:ss-mm:ss`, what is seen), `*` on three to five key moments, `!` on anything private.
3. **One topic per video, 60 to 120 s.** Split where the place or activity changes. Cut hard: shots of 2 to 5 s, a long one only when something happens in it.
4. **Hook first.** The first 3 seconds show the topic's best moment with a short `hook` or a `title` naming the place. No logo, no slow intro.
5. **One name everywhere.** Stem `<series>-d<dd>-<nn>-<topic-slug>` (for example `tw26-d01-01-arrival`), title `<Series> · Day <d> · <Topic>`; the `.mp4`, the thumbnail `.jpg`, the edit list and the recipe share the stem. Check with `vlog.py name <stem> --title "..."`.
6. **Thumbnail: a face or one strong frame, two to four big words, high contrast,** the lower-right corner clear (duration badge), one layout per series. Look at the phone-size preview.
7. **Sound.** Camera sound stays; a music bed sits under it, ducked where people talk, about -14 LUFS, fades in and out. Only instrumental music YouTube will not claim (its Audio Library, or made for you); put the licence and credit in the edit list and the title in the description.
8. **Privacy, picture.** Cut, crop or `blur` any card, receipt, booking, passport, address, phone or laptop screen, live location or person who has not agreed. None of it goes in the title or description.
9. **Privacy, sound.** `transcribe` every clip, run `sound` on each edit list and read every audible line, listening to the ones marked doubtful. `mute` or cut passwords and PINs, money details, booking or passport numbers, the hotel or an address, names of people who have not agreed (`private_names`), phone or bot calls, private or tense moments, strangers close to the mic. When unsure, cut.
10. **Verify pixels, not exit codes.** `verify` must print `ok`; then open `<stem>.sheet.jpg` and the thumbnail yourself.

## Workflow

```bash
V=scripts/vlog.py   # inside this skill
python3 $V index /footage/LRV_*.lrv --out WORK/index --every 8 --clock-offset-hours 1
python3 $V transcribe /footage/LRV_*.lrv --out WORK/index --language vi   # once per clip, cached
# read the sheets, fill WORK/index/<clip>.md, group the day into topics
python3 $V name tw26-d01-01-arrival --title "Taiwan 2026 · Day 1 · Arrival"
python3 $V sound  WORK/tw26-d01-01-arrival.json            # every audible line; exit 1 on an unmuted flag
python3 $V render WORK/tw26-d01-01-arrival.json --draft   # quick look, then without --draft
python3 $V thumb  WORK/tw26-d01-01-arrival.json
python3 $V verify WORK/tw26-d01-01-arrival.json           # exit 0 = ready to upload
```

`--clock-offset-hours` is local time minus the camera clock. Pass `--language`: Whisper guesses from the first 30 s only. `transcribe` runs `mlx_whisper` or `TRAVEL_VLOG_WHISPER`. Edit list fields: [references/edit-list.md](references/edit-list.md). 360 views (yaw, pitch, fov, pans, tiny planet) and the X5 file layout: [references/insta360-360.md](references/insta360-360.md).

## Upload

Confirm the signed-in account and channel first. Upload Private unless the owner says otherwise (Unlisted is public to anyone with the link), with the thumbnail, the title, a short description (places, music credit) and the series playlist. Public, deleting and messages wait for the owner.

## Report

Per video: the stem, length, loudness from `verify`, the music and its licence, what was cut for privacy, and the link once uploaded.
