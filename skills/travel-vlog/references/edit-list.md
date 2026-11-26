# Edit list

One JSON file per video, named `<stem>.json`. `render`, `thumb` and `verify` read it.

```json
{
  "stem": "tw26-d01-01-arrival",
  "title": "Taiwan 2026 · Day 1 · Arrival",
  "description": "Landing at Taoyuan on our first morning in Taiwan.\n\nMusic: <title> by <artist> (YouTube Audio Library)",
  "output_dir": "/path/to/work/day1/out",
  "size": [1920, 1080],
  "fps": 25,
  "length_s": [45, 150],
  "loudness_lufs": -14,
  "fade_s": 0.8,
  "music": [
    {"file": "/path/to/work/music/track.mp3", "title": "Track", "artist": "Artist",
     "licence": "YouTube Audio Library licence", "credit": "",
     "from": 0, "at": 0, "gain_db": -16, "fade_in": 1.5, "fade_out": 2.5}
  ],
  "duck": {"threshold": 0.03, "ratio": 6, "attack": 80, "release": 600},
  "thumbnail": {"src": "/footage/clip.mp4", "t": 31.2, "words": ["FIRST", "TIME", "TAIWAN"],
                "side": "left", "view": {"x": 0.6}, "badge": "DAY 1"},
  "shots": [
    {"src": "/footage/LRV_..._083.lrv", "in": 48.0, "out": 52.5,
     "view": {"yaw": 0, "pitch": 5, "fov": 85, "yaw_end": 40},
     "hook": "First time in Taiwan"},
    {"src": "/footage/VID_..._084.mp4", "in": 12.0, "out": 15.0,
     "title": {"text": "Taoyuan Airport", "sub": "06:40"}, "audio": 0.8},
    {"src": "/footage/VID_..._089.mp4", "in": 60, "out": 300, "speed": 20, "audio": 0,
     "blur": [{"x": 0.62, "y": 0.70, "w": 0.15, "h": 0.12}]}
  ]
}
```

| Field | Notes |
|---|---|
| `stem`, `title` | Must pass `vlog.py name`. The day in the title matches the stem. |
| `output_dir` | Never the footage folder. Defaults to the edit list's folder. |
| `fps` | 25 for 50p sources (clean halving); 30 when most shots are 29.97 or 60. |
| `length_s` | `verify` fails outside it. Default 45 to 150 s. |
| `shots[].in/out` | Seconds on the source. `speed` above 1 makes a time-lapse (audio is sped up between 0.5 and 2, otherwise set `audio: 0`). |
| `shots[].view` | See [insta360-360.md](insta360-360.md). 360 `fov` defaults to 85 and may not exceed 95. `projection` forces `flat` or `dfisheye` when the frame shape misleads. |
| `shots[].view.fit` | `blur` places a portrait (or rotated) clip whole over a blurred copy of itself; `crop` fills 16:9 by cropping. Portrait defaults to `blur`. Clips stored with non-square pixels (an X5 portrait clip is 1920x1080 at SAR 81:256, really 608x1080) are resampled to square pixels first, always. With `roll`, a blur fit keeps the largest upright rectangle of the turned frame, so no black wedges show. |
| `style` | The channel look from its written style guide: `font` (a .ttf path), `text`, `accent`, `rule`, `badge`, `shade`, `stroke` as `#RRGGBB`. Titles, hooks and the thumbnail draw with it; without it they draw white and yellow on black. |
| `lens`, `shots[].lens` | Straighten a barrel-distorted flat clip before the view: `"x5"` (Insta360 X5 single-lens: k1 0.12, k2 0.015, 14% crop) or `{"k1", "k2", "crop"}`. Off by default; the shot's value wins. |
| `grade` | One ffmpeg filter chain applied to every shot and the thumbnail, from the channel style guide. |
| `length_s` | Allowed length in seconds for `verify`; default `[180, 360]`. |
| `shots[].hook` | Big centred words over the first seconds of the shot. Use on shot 1. |
| `shots[].title` | Lower-left place and time; `at` and `hold` in seconds. |
| `shots[].audio` | Camera sound gain, 0 to mute. |
| `shots[].mute` | `[[a, b], ...]` source seconds where the camera sound is silenced (the music keeps playing). |
| `transcripts` | Folder of `<clip>.transcript.json` from `transcribe`; default the output folder. |
| `private_names` | Names that must not be heard; `sound` and `verify` flag them. |
| `shots[].blur` | Boxes as fractions of the frame, blurred for the whole shot. Prefer cutting the shot. |
| `music[]` | `at` is where it starts in the video, `from` where in the track, `length` how long (default to the end). Several entries mix. `licence` and `credit` are required by `verify`. |
| `duck` | Sidechain from the camera sound's speech band; `false` turns it off. |
| `thumbnail` | `src` and `t` pick the frame; `view` as for a shot; `lines` overrides how the words break; `colors` per line. |
