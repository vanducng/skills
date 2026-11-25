---
name: travel-vlog
description: "Turns a day of travel footage from a 360 or action camera (Insta360 X-series .insv/.lrv, GoPro, phone) into short topic videos for YouTube: index every clip into contact sheets and timestamped notes with starred moments, split the day into topics, write one edit list per video with a hook in the first seconds, reframe 360 shots headless with ffmpeg v360, cut, lay music under the camera sound with ducking, normalise to -14 LUFS, make a 1280x720 thumbnail with a face and two to four big words, name everything by one convention, and verify the render and thumbnail before upload. Use when the user says 'make a travel video', 'cut today's footage', 'day 1 video', 'vlog from my Insta360 clips', 'reframe this 360 clip', 'make the thumbnail', 'name the episodes' or 'is this video ready to upload'. Not for HTML motion graphics or explainers (video), AI-generated footage (omnimedia) or photo stitching with the Insta360 SDK."
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
---

# travel-vlog

A day of footage becomes several short videos, one topic each. The fragile steps are in `scripts/vlog.py`; run it, do not hand-roll ffmpeg. The craft rules below come from [research](references/research.md) and the [three source repos](references/sources.md).

## Rules

1. **Originals are read-only.** Write renders, sheets and notes to a work folder outside the footage folder and outside any repo. `render` refuses an output folder that is the footage folder.
2. **Look before cutting.** Run `index` on the proxies (`.lrv`, or the smallest copy), open every contact sheet, and write each clip's `<clip>.md`: one line per moment, `mm:ss-mm:ss` and what is seen, `*` on three to five key moments, `!` on anything private. A cut chosen from file names or chat alone is a guess.
3. **One topic per video, 60 to 120 s.** Split the day where the place or activity changes. A memory film, not a log: cut hard, shots of 2 to 5 s, a long shot only when something happens in it. Over 2 minutes needs a reason.
4. **Hook first.** The first 3 seconds show the best moment of the topic, with a `hook` line of a few words or a `title` naming the place. No logo, no slow intro: retention lost in the first 15 s does not come back.
5. **One name everywhere.** Stem `<series>-d<dd>-<nn>-<topic-slug>` (for example `tw26-d01-01-arrival`), title `<Series> · Day <d> · <Topic>`; the `.mp4`, the thumbnail `.jpg`, the edit list and the recipe share the stem. Check with `vlog.py name <stem> --title "..."`.
6. **Thumbnail: one face or one strong frame, two to four big words, high contrast,** text clear of the lower-right corner (the duration badge). Same layout across the series. Look at the phone-size preview before you accept it.
7. **Sound.** Every video has a music bed. Camera sound stays; music sits under it and ducks where people talk (`duck`), integrated loudness about -14 LUFS, true peak at or below -1 dBTP, fades in and out. Music only from a source YouTube will not claim (its Audio Library or music made for you); record the licence and credit line in the edit list.
8. **Privacy, picture.** Cut or `blur` any frame with a card, receipt, booking number, passport, address, a live location or a person who has not agreed. None of it goes in the title or description, and links lose their tracking ids.
9. **Privacy, sound.** Transcribe every clip before its sound is used (`transcribe`, local Whisper), then run `sound` on each edit list and read every audible line. Mute (`mute`) or cut passwords, card, bank and money details, booking or passport numbers, the hotel or an address, names of people who have not agreed (`private_names`), phone or bot calls, private or tense moments, strangers close to the mic. When unsure, cut. `sound` flags the obvious ones; reading the lines is still your job.
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

`--clock-offset-hours` is local time minus the camera clock, so sheets show the local time of day. Whisper's language detection reads the first 30 s only: pass `--language` for the language most spoken. `transcribe` uses `mlx_whisper` (Apple Silicon) or the command in `TRAVEL_VLOG_WHISPER`. Edit list fields: [references/edit-list.md](references/edit-list.md). 360 views (yaw, pitch, fov, pans, tiny planet) and the X5 file layout: [references/insta360-360.md](references/insta360-360.md).

## Upload

Upload as Private unless the owner names another privacy (Unlisted is public to anyone with the link), with the thumbnail, the title by the convention, a short description (places, the music credit) and the series playlist. Confirm the signed-in account and channel first. Making a video public, deleting one, or messaging anyone waits for the owner.

## Report

Per video: the stem, length, loudness from `verify`, the music and its licence, what was cut for privacy, and the link once uploaded.
