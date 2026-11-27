---
name: travel-vlog
description: "Turns a day of travel footage from a 360 or action camera (Insta360 X-series .insv/.lrv, GoPro, phone) into short topic videos for YouTube: index every clip into contact sheets and timestamped notes with starred moments, split the day into topics, write one edit list per video with a hook in the first seconds, reframe 360 shots headless with ffmpeg v360, cut, lay music under the camera sound with ducking, normalise to -14 LUFS, make a 1280x720 thumbnail with a face and two to four big words, name everything by one convention, and verify the render and thumbnail before upload. Use when the user says 'make a travel video', 'cut today's footage', 'day 1 video', 'vlog from my Insta360 clips', 'reframe this 360 clip', 'make the thumbnail', 'name the episodes' or 'is this video ready to upload'. Not for HTML motion graphics or explainers (video), AI-generated footage (omnimedia) or photo stitching with the Insta360 SDK."
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
---

# travel-vlog

A day of footage becomes short videos, one topic each. `scripts/vlog.py` runs the fragile steps; do not hand-roll ffmpeg. Sources: [research](references/research.md), [source repos](references/sources.md).

## Rules

1. **Originals are read-only.** Work files go to a folder outside the footage and outside any repo.
2. **Look before cutting.** `index` the proxies, open every sheet, write each `<clip>.md`: one line per moment (`mm:ss-mm:ss`), `*` on key moments, `!` on anything private.
3. **One topic per video, 3 to 6 minutes, one arc:** arrive, explore, a moment, leave. Shots of 3 to 8 s; a moment may run 10 to 20 s. The owner's taste overrides the platform averages in the research.
4. **A taste of the place.** Open each scene on an establishing shot held 4 to 6 s with real ambient sound before the music; the video's first seconds may tease its best moment first. Design each topic for what it conveys, not one template.
5. **One name everywhere.** Stem `<series>-d<dd>-<nn>-<topic-slug>` (for example `tw26-d01-01-arrival`), title `<Series> · Day <d> · <Topic>`; the `.mp4`, the thumbnail `.jpg`, the edit list and the recipe share the stem. Check with `vlog.py name <stem> --title "..."`.
6. **Undistorted, one look.** 360 views at 75 to 90° (over 95° is refused), level with `roll`; straighten flat clips with `lens` (`"x5"`); portrait clips fit over a blur. Never stretch. One `grade` and one `style` from the channel's written style guide (write one first). Look at a full-size still of every shot before the render.
7. **Point the view at the people of the story.** A shot faces the kids, the partner, the family, or a named `landmark` when nobody is there; never a wall of trees while the people are elsewhere. On 360, follow them with `view.track`; on flat footage, pick the ranges `find-people` lists. `people` and `verify` fail a view with nobody in it for over 3 s. **The camera holder stays behind the camera:** their face only where it carries a moment, a few seconds at most. Tag those shots `holder`; `verify` caps the total and any stretch over 4 s. A map card is a `still` shot; a short `caption` names a place or a moment.
8. **Thumbnail: the place or the moment, not the camera holder, two to four big words, high contrast,** the lower-right corner clear (duration badge), one layout per series. Look at the phone-size preview.
9. **Sound.** Camera sound stays over a ducked music bed, about -14 LUFS. Only instrumental music YouTube will not claim (its Audio Library); licence and credit in the edit list, title in the description.
10. **Privacy, picture.** Cut, crop or `blur` any card, receipt, booking, passport, address, phone or laptop screen, live location or person who has not agreed. None of it goes in the title or description.
11. **Privacy, sound.** `transcribe` every clip, run `sound` on each edit list and read every audible line, listening to the ones marked doubtful (`LISTEN`: Whisper invents words over music and water). `mute` or cut passwords and PINs, money details, booking or passport numbers, the hotel or an address, names of people who have not agreed (`private_names`), phone or bot calls, private or tense moments, strangers close to the mic. When unsure, cut.
12. **Verify pixels, not exit codes.** `verify` must print `ok`; then open `<stem>.sheet.jpg` and the thumbnail yourself.

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
python3 $V people WORK/tw26-d01-01-arrival.json           # who is in each view; exit 1 on an empty one (Apple Vision)
python3 $V render WORK/tw26-d01-01-arrival.json --draft   # quick look, then without --draft
python3 $V thumb  WORK/tw26-d01-01-arrival.json
python3 $V verify WORK/tw26-d01-01-arrival.json           # exit 0 = ready to upload
```

`--clock-offset-hours` is local time minus the camera clock. Pass `--language` (Whisper guesses from 30 s). Edit list fields: [references/edit-list.md](references/edit-list.md). 360 views (yaw, pitch, fov, pans, tiny planet) and the X5 file layout: [references/insta360-360.md](references/insta360-360.md).

## Upload

Use the `youtube-upload` skill when it is installed. Confirm the signed-in account and channel first. Upload Private unless the owner says otherwise (Unlisted is public to anyone with the link), with the thumbnail, the title, a short description (places, music credit) and the series playlist. Public, deleting and messages wait for the owner.

## Report

Per video: stem, length, loudness, music and licence, privacy cuts, link.
