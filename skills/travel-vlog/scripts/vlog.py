#!/usr/bin/env python3
"""travel-vlog: the fragile steps of turning a day of camera footage into short videos.

  vlog.py index  <clip>... --out DIR [--every 10] [--clock-offset-hours 0]
  vlog.py name   <stem>  [--title "..."]
  vlog.py render <edit.json> [--draft]
  vlog.py thumb  <edit.json>
  vlog.py transcribe <clip>... --out DIR
  vlog.py sound  <edit.json> [--names NAME...]
  vlog.py verify <edit.json>
  vlog.py sheet  <video> --out SHEET.jpg [--every 5]

Originals are only read. Every output gets a recipe .json beside it.
Needs ffmpeg/ffprobe (with v360, loudnorm, sidechaincompress) and Pillow.
"""
from __future__ import annotations

import argparse
import array
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

STEM_RE = re.compile(r"^(?P<series>[a-z0-9]{2,8})-d(?P<day>\d{2})-(?P<nn>\d{2})-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)$")
TITLE_RE = re.compile(r"^.+ · Day \d{1,2} · .+$")
CLIP_TIME_RE = re.compile(r"(?P<d>\d{8})_(?P<t>\d{6})_\d{2}_(?P<n>\d{3})")
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Black.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Black.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]
THUMB_W, THUMB_H, THUMB_MAX_BYTES = 1280, 720, 2 * 1024 * 1024


def die(msg: str, code: int = 2) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def run(cmd: list[str], capture: bool = False) -> subprocess.CompletedProcess:
    p = subprocess.run(cmd, stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                       stderr=subprocess.PIPE, text=not capture or None)
    if p.returncode != 0:
        err = p.stderr if isinstance(p.stderr, str) else p.stderr.decode(errors="replace")
        die(f"{cmd[0]} failed ({p.returncode}): {err.strip()[-1500:]}")
    return p


def ffmpeg(args: list[str]) -> None:
    run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y", *args])


def probe(path: str | Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        die(f"ffprobe cannot read {path}: {out.stderr.strip()}")
    return json.loads(out.stdout)


def media_info(path: str | Path) -> dict:
    j = probe(path)
    v = next((s for s in j["streams"] if s.get("codec_type") == "video"), None)
    a = next((s for s in j["streams"] if s.get("codec_type") == "audio"), None)
    info = {"path": str(path), "duration": float(j["format"].get("duration", 0) or 0),
            "has_audio": a is not None, "video_streams": sum(1 for s in j["streams"] if s.get("codec_type") == "video")}
    if v:
        num, den = (v.get("avg_frame_rate") or v.get("r_frame_rate") or "0/1").split("/")
        sn, sd = (v.get("sample_aspect_ratio") or "1:1").replace("0:1", "1:1").split(":")
        rot = next((int(float(sd_.get("rotation", 0))) for sd_ in v.get("side_data_list", []) if "rotation" in sd_), 0)
        w, h = int(v["width"]), int(v["height"])
        # ffmpeg applies a display-matrix rotation on input, so filters see the rotated size.
        if rot % 180:
            w, h, sn, sd = h, w, sd, sn
        info.update(width=w, height=h, codec=v.get("codec_name"), rotation=rot % 360,
                    fps=round(float(num) / float(den or 1), 3) if float(den or 1) else 0.0,
                    sar=(int(sn), int(sd) or 1))
    return info


def square_pixels(info: dict) -> str:
    """Resample non-square pixels to square ones: a portrait clip stored squeezed in a 16:9 grid (SAR 81:256) is
    really 608x1080, and filters that read iw/ih would stretch it 3.2x wide."""
    n, d = info.get("sar", (1, 1))
    return "" if n == d else f"scale=trunc(iw*{n}/{d}/2)*2:ih,setsar=1,"


def is_portrait(info: dict, view: dict | None = None) -> bool:
    n, d = info.get("sar", (1, 1))
    w, h = info.get("width", 0) * n / d, info.get("height", 0)
    if int((view or {}).get("rotate", 0)) % 180:
        w, h = h, w
    return bool(h) and w < h


def projection_of(info: dict, path: str) -> str:
    """dfisheye for a dual-fisheye frame (360 proxy: two circles side by side), else flat."""
    if path.lower().endswith(".insv"):
        return "insv"
    w, h = info.get("width", 0), info.get("height", 0)
    return "dfisheye" if h and abs(w / h - 2.0) < 0.01 else "flat"


def clip_clock(path: str, offset_hours: float) -> dict:
    m = CLIP_TIME_RE.search(Path(path).name)
    if not m:
        return {}
    cam = dt.datetime.strptime(m["d"] + m["t"], "%Y%m%d%H%M%S")
    local = cam + dt.timedelta(hours=offset_hours)
    return {"clip_no": m["n"], "camera_start": cam.isoformat(), "local_start": local.isoformat()}


DEFAULT_FOV = 85
MAX_FOV = 95  # wider than this stretches the edges of a 360 reframe
# X5 flat (single-lens) clips are barrel-distorted; this straightens them and crops away the bent edges
LENS = {"x5": {"k1": 0.12, "k2": 0.015, "crop": 1.14}}


def lens_filter(lens, w: int, h: int) -> str:
    """Straighten a barrel-distorted flat clip and crop until no edge is empty; '' when lens is off."""
    if not lens:
        return ""
    p = LENS[lens] if isinstance(lens, str) else lens
    z = float(p["crop"])
    return (f"lenscorrection=cx=0.5:cy=0.5:k1={p['k1']}:k2={p['k2']}:i=bilinear,"
            f"scale=iw*{z}:ih*{z},crop=iw/{z}:ih/{z},")


def fov_problems(e: dict) -> list[str]:
    """360 views wider than MAX_FOV, per shot and thumbnail."""
    out = []
    views = [(f"shot {i + 1}", s.get("view") or {}) for i, s in enumerate(e.get("shots", []))]
    if e.get("thumbnail"):
        views.append(("thumbnail", e["thumbnail"].get("view") or {}))
    for name, v in views:
        if v.get("type") == "tiny-planet":
            continue
        for k in ("fov", "fov_end"):
            if k in v and float(v[k]) > MAX_FOV:
                out.append(f"{name}: {k} {v[k]} is over {MAX_FOV}; edges stretch")
    return out


def holder_problems(e: dict) -> list[str]:
    """The camera holder's face (shots tagged "holder": true) stays brief: at most `holder_max_s` in all (default 10 %
    of the planned length, at least 4 s), no single stretch over `holder_stretch_s` (default 4 s), never the thumbnail."""
    shots = e.get("shots", [])
    durs = [(float(s["out"]) - float(s["in"])) / float(s.get("speed", 1)) for s in shots]
    limit = float(e.get("holder_max_s", max(4.0, 0.1 * sum(durs))))
    stretch_max = float(e.get("holder_stretch_s", 4))
    out, total, run = [], 0.0, 0.0
    for i, (s, d) in enumerate(zip(shots, durs)):
        run = run + d if s.get("holder") else 0.0
        total += d if s.get("holder") else 0.0
        if run > stretch_max:
            out.append(f"shot {i + 1}: the camera holder's face runs {run:.1f} s in a row (max {stretch_max:g} s); "
                       "reframe toward what they look at")
            run = 0.0
    if total > limit:
        out.append(f"the camera holder's face is on screen {total:.1f} s (max {limit:.1f} s)")
    if (e.get("thumbnail") or {}).get("holder"):
        out.append("thumbnail: features the camera holder's face; use the place or the moment")
    return out


STYLE_DEFAULT = {"font": None, "text": "#FFFFFF", "accent": "#FFD666", "rule": None, "badge": "#DC1E28",
                 "shade": "#000000", "stroke": "#000000"}
STYLE = dict(STYLE_DEFAULT)


def use_style(e: dict) -> None:
    """Channel look from the edit list's `style` block (font and colours from the written style guide)."""
    STYLE.clear()
    STYLE.update(STYLE_DEFAULT, **(e.get("style") or {}))
    if STYLE["font"] and not Path(STYLE["font"]).is_file():
        die(f"style font {STYLE['font']} not found")


def rgb(hex_or_list, alpha: int | None = None) -> tuple:
    c = tuple(hex_or_list) if isinstance(hex_or_list, (list, tuple)) else \
        tuple(int(hex_or_list.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    return c[:3] + ((alpha,) if alpha is not None else ())


def load_font(size: int):
    from PIL import ImageFont
    env = os.environ.get("TRAVEL_VLOG_FONT")
    for cand in [STYLE["font"], env] + FONT_CANDIDATES:
        if cand and Path(cand).is_file():
            return ImageFont.truetype(cand, size)
    die("no bold TrueType font found; set TRAVEL_VLOG_FONT to a .ttf path")


def need_pillow() -> None:
    try:
        import PIL  # noqa: F401
    except ImportError:
        die("Pillow is required for sheets, titles and thumbnails: python3 -m pip install --user pillow")


def fmt_t(t: float) -> str:
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


# ---------- view filters ----------

INSV_JOIN = "[0:v:1][0:v:0]hstack=inputs=2"  # lens 1 left, lens 0 right: the .lrv layout v360 dfisheye reads


def video_in(proj: str) -> str:
    """filter_complex source pad: an .insv's two fisheye streams joined side by side, else the first video stream."""
    return f"{INSV_JOIN}," if proj == "insv" else "[0:v]"


def view_filter(view: dict, proj: str, w: int, h: int, portrait: bool = False) -> str:
    """ffmpeg filter that turns a source frame into a w x h flat frame.

    A portrait frame is fitted whole over a blurred, darkened copy of itself (`fit: blur`, the default for portrait)
    rather than cropped to 16:9, which would upscale a third of it; `fit: crop` forces the crop.
    """
    v = view or {}
    if proj in ("dfisheye", "insv"):
        fov = float(v.get("fov", DEFAULT_FOV))
        vfov = 2 * math.degrees(math.atan(math.tan(math.radians(fov / 2)) * h / w))
        lens_fov = float(v.get("lens_fov", 200))
        if v.get("type") == "tiny-planet":
            return (f"v360=input=dfisheye:output=stereographic:ih_fov={lens_fov}:iv_fov={lens_fov}"
                    f":pitch=-90:h_fov={fov}:v_fov={fov}:w={h}:h={h}:interp=lanczos,"
                    f"pad={w}:{h}:(ow-iw)/2:0:black")
        return (f"v360=input=dfisheye:output=flat:ih_fov={lens_fov}:iv_fov={lens_fov}"
                f":yaw={float(v.get('yaw', 0))}:pitch={float(v.get('pitch', 0))}:roll={float(v.get('roll', 0))}"
                f":h_fov={fov}:v_fov={vfov:.3f}:w={w}:h={h}:interp=lanczos")
    pre = {90: "transpose=clock,", -90: "transpose=cclock,", 270: "transpose=cclock,",
           180: "hflip,vflip,"}.get(int(v.get("rotate", 0)), "")
    roll = float(v.get("roll", 0))
    cx, cy = float(v.get("x", 0.5)), float(v.get("y", 0.5))
    zoom = float(v.get("zoom", 1.0))
    fit = v.get("fit", "blur" if portrait else "crop")
    if roll:
        r = math.radians(abs(roll))
        cover = f"(cos({r:.5f})+sin({r:.5f})*max(iw/ih,ih/iw))"
        pre += f"rotate={math.radians(roll):.5f}:fillcolor=black,"
        if fit == "blur":
            # keep the largest upright rectangle of the rotated frame: no black wedges at the sides
            pre += f"crop=w='iw/{cover}':h='ih/{cover}',"
        else:
            # rotating needs extra zoom so the corners stay filled
            zoom *= math.cos(r) + math.sin(r) * max(w / h, h / w)
    if fit == "blur":
        return (f"{pre}split[vfg][vbg];[vbg]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
                f"gblur=sigma=40,eq=brightness=-0.08[vbgb];"
                f"[vfg]scale={w}*{zoom:.4f}:{h}*{zoom:.4f}:force_original_aspect_ratio=decrease,"
                f"crop='min(iw,{w})':'min(ih,{h})'[vfgs];[vbgb][vfgs]overlay=(W-w)/2:(H-h)/2")
    return (f"{pre}scale={w}*{zoom:.4f}:{h}*{zoom:.4f}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h}:(iw-{w})*{cx}:(ih-{h})*{cy}")


def pan_filter(view: dict, w: int, h: int, dur: float, fps: float, path: Path) -> str | None:
    """Filter chain for a yaw/pitch/fov move across a 360 shot, or None when the view is static.

    v360 applies a yaw or pitch command as a step relative to the current view, and with both
    axes in one instance the steps compose in the wrong order. So yaw turns the sphere in a
    first equirect stage and pitch and fov aim the flat camera in a second one.
    """
    v = view or {}
    keys = [k for k in ("yaw", "pitch", "fov") if f"{k}_end" in v]
    if not keys:
        return None
    start = {"yaw": float(v.get("yaw", 0)), "pitch": float(v.get("pitch", 0)), "fov": float(v.get("fov", DEFAULT_FOV))}
    stage = {"yaw": "v360@sphere yaw", "pitch": "v360@camera pitch", "fov": "v360@camera h_fov"}
    vfov_of = lambda hf: 2 * math.degrees(math.atan(math.tan(math.radians(hf / 2)) * h / w))
    lines, n, prev = [], max(2, int(dur * fps)), dict(start)
    for i in range(1, n + 1):
        f = i / n
        ease = f * f * (3 - 2 * f)
        cmds = []
        for k in keys:
            val = start[k] + (float(v[f"{k}_end"]) - start[k]) * ease
            cmds.append(f"{stage[k]} {val if k == 'fov' else val - prev[k]:.4f}")
            if k == "fov":
                cmds.append(f"v360@camera v_fov {vfov_of(val):.4f}")
            prev[k] = val
        lines.append(f"{f * dur:.4f} " + ",".join(cmds) + ";")
    path.write_text("\n".join(lines) + "\n")
    lens_fov = float(v.get("lens_fov", 200))
    vfov = vfov_of(start["fov"])
    return (f"sendcmd=f='{path}',"
            f"v360@sphere=input=dfisheye:output=equirect:ih_fov={lens_fov}:iv_fov={lens_fov}"
            f":yaw={start['yaw']}:roll={float(v.get('roll', 0))}:w=4096:h=2048,"
            f"v360@camera=input=equirect:output=flat:pitch={start['pitch']}:h_fov={start['fov']}"
            f":v_fov={vfov:.3f}:w={w}:h={h}:interp=lanczos")


# ---------- text overlays ----------

def title_png(title: dict, w: int, h: int, out: Path) -> None:
    """Lower-left place/time title with a soft shadow, transparent PNG."""
    from PIL import Image, ImageDraw, ImageFilter
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    main = title.get("text", "").strip()
    sub = title.get("sub", "").strip()
    f1, f2 = load_font(int(h * 0.062)), load_font(int(h * 0.034))
    x, y = int(w * 0.055), int(h * 0.80)
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for dx, dy in ((3, 3),):
        sd.text((x + dx, y + dy), main, font=f1, fill=(0, 0, 0, 200))
        if sub:
            sd.text((x + dx, y - int(h * 0.05) + dy), sub, font=f2, fill=(0, 0, 0, 200))
    shadow = shadow.filter(ImageFilter.GaussianBlur(4))
    img.alpha_composite(shadow)
    d = ImageDraw.Draw(img)
    if sub:
        d.text((x, y - int(h * 0.05)), sub.upper(), font=f2, fill=rgb(STYLE["accent"], 255))
    if STYLE["rule"]:
        d.rectangle([x, y - int(h * 0.068), x + int(w * 0.045), y - int(h * 0.062)], fill=rgb(STYLE["rule"], 255))
    d.text((x, y), main, font=f1, fill=rgb(STYLE["text"], 255))
    img.save(out)


def hook_png(text: str, w: int, h: int, out: Path) -> None:
    """Big centred hook line for the first seconds."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    size = int(h * 0.11)
    font = load_font(size)
    while d.textlength(text, font=font) > w * 0.86 and size > 20:
        size -= 4
        font = load_font(size)
    tw = d.textlength(text, font=font)
    x, y = (w - tw) / 2, h * 0.42
    d.text((x, y), text, font=font, fill=rgb(STYLE["text"], 255), stroke_width=max(3, size // 14),
           stroke_fill=rgb(STYLE["stroke"], 230))
    img.save(out)


# ---------- index ----------

def frame_grabs(src: str, proj: str, every: float, dur: float, tmp: Path, w: int) -> list[tuple[float, Path]]:
    every = min(every, max(dur / 2, 0.05))  # a clip shorter than the step still gets frames
    h = w // 2 if proj in ("dfisheye", "insv") else int(w * 9 / 16)
    vf = (f"v360=input=dfisheye:output=equirect:ih_fov=200:iv_fov=200:w={w}:h={h}" if proj != "flat"
          else f"{square_pixels(media_info(src))}scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2")
    pattern = tmp / "f_%05d.jpg"
    ffmpeg(["-i", src, "-filter_complex", f"{video_in(proj)}fps=1/{every},{vf}", "-q:v", "4", str(pattern)])
    frames = sorted(tmp.glob("f_*.jpg"))
    return [(min(i * every, dur), f) for i, f in enumerate(frames)]


def contact_sheet(grabs: list[tuple[float, Path]], out: Path, cols: int, label: str) -> None:
    from PIL import Image, ImageDraw
    if not grabs:
        return
    first = Image.open(grabs[0][1])
    tw, th = first.size
    rows = math.ceil(len(grabs) / cols)
    head = 34
    sheet = Image.new("RGB", (cols * tw, rows * th + head), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    d.text((8, 6), label, font=load_font(20), fill=(255, 255, 255))
    small = load_font(max(12, tw // 16))
    for i, (t, f) in enumerate(grabs):
        im = Image.open(f).convert("RGB")
        x, y = (i % cols) * tw, (i // cols) * th + head
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + tw // 3, y + tw // 14 + 4], fill=(0, 0, 0))
        d.text((x + 4, y + 2), fmt_t(t), font=small, fill=(255, 230, 0))
    sheet.save(out, quality=82)


def audio_activity(src: str, dur: float) -> list[float]:
    """Per-second loudness (dBFS) of the speech band, a cheap hint for where people talk."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-i", src, "-vn",
                        "-af", "highpass=f=250,lowpass=f=3500", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                       capture_output=True)
    if p.returncode != 0 or not p.stdout:
        return []
    a = array.array("h")
    a.frombytes(p.stdout[: len(p.stdout) // 2 * 2])
    out = []
    for i in range(0, len(a), 8000):
        seg = a[i:i + 8000]
        rms = math.sqrt(sum(x * x for x in seg) / max(1, len(seg))) or 1e-9
        out.append(round(20 * math.log10(rms / 32768), 1))
    return out


def cmd_index(args) -> None:
    need_pillow()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    index = {"generated": dt.datetime.now().isoformat(timespec="seconds"), "every_s": args.every,
             "clock_offset_hours": args.clock_offset_hours, "clips": []}
    for src in args.clips:
        info = media_info(src)
        proj = projection_of(info, src)
        stem = Path(src).stem
        clock = clip_clock(src, args.clock_offset_hours)
        every = args.every if info["duration"] / args.every <= args.max_frames else info["duration"] / args.max_frames
        with tempfile.TemporaryDirectory() as td:
            grabs = frame_grabs(src, proj, every, info["duration"], Path(td), 320 if proj == "flat" else 400)
            sheets = []
            per = args.cols * args.rows
            for k in range(0, len(grabs), per):
                sp = out / f"{stem}_sheet{k // per + 1:02d}.jpg"
                contact_sheet(grabs[k:k + per], sp, args.cols,
                              f"{Path(src).name}  {clock.get('local_start', '')}  {fmt_t(info['duration'])}  {proj}")
                sheets.append(sp.name)
        act = audio_activity(src, info["duration"]) if info["has_audio"] else []
        loud = [i for i, v in enumerate(act) if v > args.talk_db]
        entry = {"clip": Path(src).name, "path": str(Path(src).resolve()), "projection": proj, **clock,
                 **{k: info.get(k) for k in ("duration", "width", "height", "fps", "codec", "has_audio")},
                 "every_s": round(every, 2), "sheets": sheets, "speech_band_db": act,
                 "loud_seconds": loud}
        index["clips"].append(entry)
        md = out / f"{stem}.md"
        if not md.exists():
            lines = [f"# {Path(src).name}", "", f"- local start: {clock.get('local_start', 'unknown')}",
                     f"- length: {fmt_t(info['duration'])}, {proj}, {info.get('width')}x{info.get('height')}",
                     f"- sheets: {', '.join(sheets)}", f"- loud seconds (speech band > {args.talk_db} dBFS): "
                     f"{compress_ranges(loud) or 'none'}", "", "## Shots", "",
                     "<!-- one line per moment: `mm:ss-mm:ss` what is seen; `*` marks a key moment, "
                     "`!` marks private content to cut (card, receipt, booking ref, passport, address, a third person) -->",
                     ""]
            md.write_text("\n".join(lines))
        print(f"indexed {Path(src).name}: {len(sheets)} sheet(s), {fmt_t(info['duration'])}, {proj}")
    idx = out / "index.json"
    old = json.loads(idx.read_text()) if idx.exists() else {"clips": []}
    keep = {c["clip"]: c for c in old.get("clips", [])}
    keep.update({c["clip"]: c for c in index["clips"]})
    index["clips"] = sorted(keep.values(), key=lambda c: c.get("local_start") or c["clip"])
    idx.write_text(json.dumps(index, indent=2))
    print(f"wrote {idx}")


def compress_ranges(xs: list[int], gap: int = 3) -> str:
    """Seconds list to 'mm:ss-mm:ss' ranges, bridging gaps up to `gap` seconds."""
    if not xs:
        return ""
    out, start, prev = [], xs[0], xs[0]
    for x in xs[1:] + [None]:
        if x is not None and x <= prev + gap:
            prev = x
            continue
        out.append(f"{fmt_t(start)}-{fmt_t(prev + 1)}")
        if x is not None:
            start = prev = x
    return ", ".join(out)


# ---------- naming ----------

def check_name(stem: str, title: str | None = None) -> list[str]:
    errs = []
    if not STEM_RE.match(stem):
        errs.append(f"stem {stem!r} is not <series>-d<dd>-<nn>-<topic-slug> (for example tw26-d01-01-arrival)")
    if title is not None:
        if not TITLE_RE.match(title):
            errs.append(f"title {title!r} is not '<Series> · Day <d> · <Topic>'")
        m = STEM_RE.match(stem)
        dm = re.search(r"· Day (\d{1,2}) ·", title)
        if m and dm and int(m["day"]) != int(dm[1]):
            errs.append(f"title day {dm[1]} does not match stem day {m['day']}")
        if len(title) > 100:
            errs.append("title is over YouTube's 100 characters")
    return errs


def cmd_name(args) -> None:
    errs = check_name(args.stem, args.title)
    for e in errs:
        print(f"FAIL {e}")
    if errs:
        sys.exit(1)
    print("ok")


# ---------- edit list ----------

def load_edit(path: str, writing: bool = True) -> tuple[dict, Path]:
    p = Path(path)
    e = json.loads(p.read_text())
    for k in ("stem", "title", "shots"):
        if k not in e:
            die(f"{p}: missing '{k}'")
    errs = check_name(e["stem"], e["title"])
    if errs:
        die("; ".join(errs))
    if not e["shots"]:
        die(f"{p}: no shots")
    outdir = Path(e.get("output_dir") or p.parent)
    for i, s in enumerate(e["shots"]):
        if not Path(s["src"]).is_file():
            die(f"shot {i}: source not found: {s['src']}")
        if float(s["out"]) <= float(s["in"]):
            die(f"shot {i}: out must be after in")
        if writing and outdir.resolve() == Path(s["src"]).resolve().parent:
            die("output_dir is the footage folder; originals stay read-only, write elsewhere")
    return e, outdir


def planned_duration(e: dict) -> float:
    return sum((float(s["out"]) - float(s["in"])) / float(s.get("speed", 1)) for s in e["shots"])


def render_shot(i: int, s: dict, e: dict, w: int, h: int, fps: float, tmp: Path, draft: bool) -> Path:
    src = s["src"]
    info = media_info(src)
    proj = s.get("projection") or projection_of(info, src)
    tin, tout = float(s["in"]), float(s["out"])
    speed = float(s.get("speed", 1))
    dur = (tout - tin) / speed
    view = s.get("view", {})
    vf = []
    cmdfile = tmp / f"shot{i:02d}.cmd"
    pan = proj in ("dfisheye", "insv") and pan_filter(view, w, h, dur * speed, info.get("fps", fps) or fps, cmdfile)
    lens = s.get("lens", e.get("lens")) if proj == "flat" else None
    flat = square_pixels(info) + lens_filter(lens, w, h) if proj == "flat" else ""
    vf.append(flat + (pan or view_filter(view, proj, w, h, is_portrait(info, view))))
    if e.get("grade"):
        vf.append(e["grade"])
    if speed != 1:
        vf.append(f"setpts=PTS/{speed}")
    vf += [f"fps={fps}", "format=yuv420p", "setsar=1"]
    chain = ",".join(vf)
    inputs = ["-ss", f"{tin}", "-to", f"{tout}", "-i", src]
    fc = f"{video_in(proj)}{chain}[base]"
    last = "base"
    n_in = 1
    for j, b in enumerate(s.get("blur", [])):
        bx, by, bw, bh = (int(float(b[k]) * (w if k in "xw" else h)) for k in "xywh")
        fc += (f";[{last}]split[m{j}][c{j}];[c{j}]crop={bw}:{bh}:{bx}:{by},gblur=sigma=30[bl{j}];"
               f"[m{j}][bl{j}]overlay={bx}:{by}[b{j}]")
        last = f"b{j}"
    overlays = []
    if s.get("hook"):
        hp = tmp / f"hook{i:02d}.png"
        hook_png(s["hook"], w, h, hp)
        overlays.append((hp, 0.15, min(dur - 0.1, float(s.get("hook_s", 2.6)))))
    if s.get("title"):
        tp = tmp / f"title{i:02d}.png"
        title_png(s["title"], w, h, tp)
        t0 = float(s["title"].get("at", 0.4))
        overlays.append((tp, t0, min(dur - 0.1, t0 + float(s["title"].get("hold", 3.2)))))
    for k, (png, a, b) in enumerate(overlays):
        inputs += ["-loop", "1", "-t", f"{dur}", "-i", str(png)]
        fc += (f";[{n_in}:v]format=rgba,fade=t=in:st={a}:d=0.35:alpha=1,fade=t=out:st={max(a, b - 0.35)}:d=0.35:alpha=1[o{k}]"
               f";[{last}][o{k}]overlay=0:0:shortest=1[v{k}]")
        last = f"v{k}"
        n_in += 1
    gain = float(s.get("audio", 1.0)) if 0.5 <= speed <= 2 else 0.0
    if info["has_audio"] and 0.5 <= speed <= 2:
        atempo = f"atempo={speed}," if speed != 1 else ""
        mutes = "".join(
            f"volume=enable='between(t,{max(0.0, (float(a) - tin) / speed):.3f},{(float(b) - tin) / speed:.3f})':volume=0,"
            for a, b in s.get("mute", []) if float(b) > tin and float(a) < tout)
        fc += (f";[0:a]{atempo}aresample=48000,aformat=channel_layouts=stereo,volume={gain},{mutes}"
               f"afade=t=in:d=0.04,afade=t=out:st={max(0, dur - 0.06)}:d=0.06[a]")
    else:
        inputs += ["-f", "lavfi", "-t", f"{dur}", "-i", "anullsrc=r=48000:cl=stereo"]
        fc += f";[{n_in}:a]anull[a]"
    out = tmp / f"shot{i:02d}.mp4"
    ffmpeg([*inputs, "-filter_complex", fc, "-map", f"[{last}]", "-map", "[a]", "-t", f"{dur}",
            "-c:v", "libx264", "-preset", "ultrafast" if draft else "medium", "-crf", "26" if draft else "17",
            "-c:a", "pcm_s16le", str(out).replace(".mp4", ".mov")])
    return Path(str(out).replace(".mp4", ".mov"))


def loudnorm_pass(src: Path, target: float, tp: float) -> dict:
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(src), "-vn", "-af",
                        f"loudnorm=I={target}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p.stderr, re.S)
    if not m:
        die("loudnorm measurement failed")
    return json.loads(m.group(0))


def cmd_render(args) -> None:
    need_pillow()
    e, outdir = load_edit(args.edit)
    use_style(e)
    if fov_problems(e) or holder_problems(e):
        die("; ".join(fov_problems(e) + holder_problems(e)))
    outdir.mkdir(parents=True, exist_ok=True)
    w, h = e.get("size", [1920, 1080])
    fps = float(e.get("fps", 25))
    target = float(e.get("loudness_lufs", -14))
    tp = float(e.get("true_peak_db", -1.5))
    fade = float(e.get("fade_s", 0.8))
    stem = e["stem"]
    final = outdir / f"{stem}{'.draft' if args.draft else ''}.mp4"
    with tempfile.TemporaryDirectory(prefix="travel-vlog-") as td:
        tmp = Path(td)
        parts = [render_shot(i, s, e, w, h, fps, tmp, args.draft) for i, s in enumerate(e["shots"])]
        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts))
        joined = tmp / "joined.mov"
        ffmpeg(["-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)])
        total = media_info(joined)["duration"]
        inputs = ["-i", str(joined)]
        fc = f"[0:v]fade=t=in:d={fade},fade=t=out:st={max(0, total - fade)}:d={fade}[v];"
        music = e.get("music") or []
        if music:
            cam_parts, mus_labels = "[0:a]asplit=2[cam][sc];", []
            fc += cam_parts
            for k, m in enumerate(music):
                inputs += ["-stream_loop", "-1", "-i", m["file"]]
                start = float(m.get("at", 0))
                length = float(m.get("length", total - start))
                fc += (f"[{k + 1}:a]atrim=start={float(m.get('from', 0))}:duration={length},asetpts=PTS-STARTPTS,"
                       f"aresample=48000,aformat=channel_layouts=stereo,volume={float(m.get('gain_db', -14))}dB,"
                       f"afade=t=in:d={float(m.get('fade_in', 1.5))},"
                       f"afade=t=out:st={max(0, length - float(m.get('fade_out', 2.5)))}:d={float(m.get('fade_out', 2.5))},"
                       f"adelay={int(start * 1000)}:all=1[m{k}];")
                mus_labels.append(f"[m{k}]")
            if len(mus_labels) > 1:
                fc += "".join(mus_labels) + f"amix=inputs={len(mus_labels)}:normalize=0[mus];"
            else:
                fc += f"{mus_labels[0]}anull[mus];"
            duck = e.get("duck", {"threshold": 0.03, "ratio": 6, "attack": 80, "release": 600})
            if duck:
                fc += ("[sc]highpass=f=250,lowpass=f=3500[scf];"
                       f"[mus][scf]sidechaincompress=threshold={duck.get('threshold', 0.03)}:ratio={duck.get('ratio', 6)}"
                       f":attack={duck.get('attack', 80)}:release={duck.get('release', 600)}:makeup=1[musd];"
                       "[cam][musd]amix=inputs=2:normalize=0:duration=first[mix];")
            else:
                fc += "[cam][mus]amix=inputs=2:normalize=0:duration=first[mix];"
        else:
            fc += "[0:a]anull[mix];"
        fc += f"[mix]afade=t=in:d={fade / 2},afade=t=out:st={max(0, total - fade)}:d={fade}[am]"
        mixed = tmp / "mixed.mov"
        ffmpeg([*inputs, "-filter_complex", fc, "-map", "[v]", "-map", "[am]", "-t", f"{total}",
                "-c:v", "libx264", "-preset", "ultrafast" if args.draft else "slow", "-crf", "26" if args.draft else "18",
                "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", str(mixed)])
        meas = loudnorm_pass(mixed, target, tp)
        finite = all(math.isfinite(float(meas[k])) for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset"))
        ln = f"loudnorm=I={target}:TP={tp}:LRA=11" if not finite else (f"loudnorm=I={target}:TP={tp}:LRA=11:measured_I={meas['input_i']}:measured_TP={meas['input_tp']}"
              f":measured_LRA={meas['input_lra']}:measured_thresh={meas['input_thresh']}"
              f":offset={meas['target_offset']}:linear=true")
        ffmpeg(["-i", str(mixed), "-map", "0:v", "-map", "0:a", "-c:v", "copy", "-af", f"{ln},aresample=48000",
                "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart",
                "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", str(final)])
    recipe = {"tool": "travel-vlog/scripts/vlog.py render", "rendered": dt.datetime.now().isoformat(timespec="seconds"),
              "edit_list": str(Path(args.edit).resolve()), "edit_sha256": sha256(Path(args.edit)),
              "output": str(final), "draft": args.draft, "size": [w, h], "fps": fps, "loudness_target": target,
              "loudnorm_first_pass": meas, "sources": sorted({s["src"] for s in e["shots"]}),
              "music": [{k: m.get(k) for k in ("file", "title", "artist", "licence", "credit")} for m in music]}
    final.with_suffix(".recipe.json").write_text(json.dumps(recipe, indent=2))
    print(f"rendered {final} ({fmt_t(media_info(final)['duration'])})")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------- thumbnail ----------

def thumb_lines(words: list[str]) -> list[str]:
    """Two lines balanced by length, so each word stays big at phone size."""
    tokens = " ".join(words).split()
    if len(tokens) < 2:
        return tokens
    return min(([" ".join(tokens[:k]), " ".join(tokens[k:])] for k in range(1, len(tokens))),
               key=lambda pair: max(len(pair[0]), len(pair[1])))


def cmd_thumb(args) -> None:
    need_pillow()
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
    e, outdir = load_edit(args.edit)
    use_style(e)
    th = e.get("thumbnail") or die("edit list has no 'thumbnail' block")
    words = th.get("words", "").split() if isinstance(th.get("words"), str) else th.get("words", [])
    if not 2 <= len(" ".join(words).split()) <= 4:
        die("thumbnail words: use two to four big words")
    outdir.mkdir(parents=True, exist_ok=True)
    src, t = th["src"], float(th["t"])
    info = media_info(src)
    proj = th.get("projection") or projection_of(info, src)
    with tempfile.TemporaryDirectory() as td:
        fr = Path(td) / "f.png"
        ffmpeg(["-ss", f"{t}", "-i", src, "-frames:v", "1", "-filter_complex",
                f"{video_in(proj)}"
                + (square_pixels(info) + lens_filter(th.get('lens', e.get('lens')), THUMB_W, THUMB_H) if proj == 'flat' else "")
                + view_filter(th.get('view', {}), proj, THUMB_W, THUMB_H, is_portrait(info, th.get('view')))
                + (f",{e['grade']}" if e.get("grade") else ""),
                str(fr)])
        img = Image.open(fr).convert("RGB")
    img = ImageEnhance.Contrast(img).enhance(float(th.get("contrast", 1.12)))
    img = ImageEnhance.Color(img).enhance(float(th.get("saturation", 1.2)))
    side = th.get("side", "left")
    grad = Image.new("L", (THUMB_W, THUMB_H), 0)
    gd = ImageDraw.Draw(grad)
    for x in range(THUMB_W):
        f = x / THUMB_W if side == "right" else 1 - x / THUMB_W
        gd.line([(x, 0), (x, THUMB_H)], fill=int(170 * max(0, f - 0.25) / 0.75))
    img = Image.composite(Image.new("RGB", img.size, rgb(STYLE["shade"])), img, grad.filter(ImageFilter.GaussianBlur(30)))
    d = ImageDraw.Draw(img)
    lines = [ln for ln in (th.get("lines") or thumb_lines(words)) if ln]
    colors = [rgb(c) for c in th.get("colors", [STYLE["text"], STYLE["accent"]])]
    y = int(THUMB_H * float(th.get("y", 0.18)))
    for k, ln in enumerate(lines):
        size = 190
        font = load_font(size)
        while d.textlength(ln.upper(), font=font) > THUMB_W * float(th.get("width", 0.5)) and size > 60:
            size -= 6
            font = load_font(size)
        tw = d.textlength(ln.upper(), font=font)
        x = int(THUMB_W * 0.05) if side == "left" else int(THUMB_W * 0.95 - tw)
        d.text((x, y), ln.upper(), font=font, fill=colors[k % len(colors)], stroke_width=max(6, size // 16),
               stroke_fill=rgb(STYLE["stroke"]))
        y += int(size * 1.08)
    if th.get("badge"):
        f = load_font(44)
        bw = d.textlength(th["badge"], font=f) + 36
        bx = THUMB_W - bw - 30 if side == "left" else 30
        d.rounded_rectangle([bx, 28, bx + bw, 96], radius=14, fill=rgb(STYLE["badge"]))
        d.text((bx + 18, 38), th["badge"], font=f, fill=rgb(STYLE["text"]))
    out = outdir / f"{e['stem']}.jpg"
    q = 92
    while True:
        img.save(out, "JPEG", quality=q, optimize=True, progressive=True)
        if out.stat().st_size < THUMB_MAX_BYTES or q < 60:
            break
        q -= 6
    phone = outdir / f"{e['stem']}.phone.jpg"
    img.resize((320, 180), Image.LANCZOS).save(phone, quality=85)
    (outdir / f"{e['stem']}.thumb.json").write_text(json.dumps(
        {"tool": "travel-vlog/scripts/vlog.py thumb", "src": src, "t": t, "words": words, "lines": lines,
         "output": str(out), "bytes": out.stat().st_size}, indent=2))
    print(f"thumbnail {out} ({out.stat().st_size // 1024} KB); phone-size preview {phone}")


# ---------- verify ----------

def frame_stats(video: Path, times: list[float]) -> list[tuple[float, float, float]]:
    from PIL import Image, ImageStat
    res = []
    with tempfile.TemporaryDirectory() as td:
        for k, t in enumerate(times):
            fp = Path(td) / f"v{k}.png"
            ffmpeg(["-ss", f"{t}", "-i", str(video), "-frames:v", "1", "-vf", "scale=320:-2", str(fp)])
            st = ImageStat.Stat(Image.open(fp).convert("L"))
            res.append((t, st.mean[0], st.stddev[0]))
    return res


def measure_loudness(video: Path) -> tuple[float, float]:
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(video), "-vn", "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True)
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr)
    tpk = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", p.stderr)
    return (float(i[-1]) if i else float("nan"), float(tpk[-1]) if tpk else float("nan"))


def cmd_verify(args) -> None:
    need_pillow()
    from PIL import Image
    e, outdir = load_edit(args.edit, writing=False)
    stem = e["stem"]
    video = outdir / f"{stem}.mp4"
    fails, notes = [], []
    w, h = e.get("size", [1920, 1080])
    lo, hi = e.get("length_s", [180, 360])
    fails += fov_problems(e) + holder_problems(e)
    if not video.is_file():
        die(f"no render at {video}", 1)
    info = media_info(video)
    if (info.get("width"), info.get("height")) != (w, h):
        fails.append(f"size {info.get('width')}x{info.get('height')}, expected {w}x{h}")
    if not info["has_audio"]:
        fails.append("no audio stream")
    if not lo <= info["duration"] <= hi:
        fails.append(f"length {info['duration']:.1f}s is outside {lo}-{hi}s")
    if abs(info["duration"] - planned_duration(e)) > 1.0:
        fails.append(f"length {info['duration']:.1f}s differs from the edit list's {planned_duration(e):.1f}s")
    li, tpk = measure_loudness(video)
    target = float(e.get("loudness_lufs", -14))
    if not abs(li - target) <= 1.0:
        fails.append(f"loudness {li} LUFS, target {target} +/- 1")
    if tpk > -0.5:
        fails.append(f"true peak {tpk} dBFS is above -0.5")
    times = [min(info["duration"] - 0.5, max(0.5, info["duration"] * f)) for f in (0.03, 0.2, 0.4, 0.6, 0.8, 0.97)]
    hook_t = min(2.0, info["duration"] / 2)
    for t, mean, sd in frame_stats(video, [hook_t] + times):
        if mean < 8 or sd < 4:
            fails.append(f"frame at {t:.1f}s looks blank (mean {mean:.0f}, stddev {sd:.0f})")
    if not any(s.get("hook") or s.get("title") for s in e["shots"][:1]):
        fails.append("first shot has no hook or title: the first seconds must say what this video is")
    thumb = outdir / f"{stem}.jpg"
    if not thumb.is_file():
        fails.append(f"no thumbnail {thumb.name}")
    else:
        im = Image.open(thumb)
        if im.size != (THUMB_W, THUMB_H) or im.format != "JPEG":
            fails.append(f"thumbnail is {im.format} {im.size}, expected JPEG 1280x720")
        if thumb.stat().st_size >= THUMB_MAX_BYTES:
            fails.append("thumbnail is 2 MB or more")
    if not video.with_suffix(".recipe.json").is_file():
        fails.append("no recipe .json beside the render")
    if not e.get("music") and e.get("music") is not False:
        fails.append("no music bed: add an Audio Library track (or set \"music\": false on purpose)")
    for m in e.get("music") or []:
        if not (m.get("licence") and m.get("credit") is not None):
            fails.append(f"music {Path(m['file']).name}: record its licence and credit line (credit may be empty)")
        if m.get("title") and m["title"] not in e.get("description", ""):
            fails.append(f"description does not name the music ({m['title']}) and its licence")
    desc = e.get("description", "")
    for pat, what in ((r"\b\d{4}\b.*\b\d{4}\b", "number groups (card or booking?)"), (r"https?://\S*slack", "a Slack link"),
                      (r"[?&](utm_|si=|fbclid)", "a tracking id")):
        if re.search(pat, desc):
            notes.append(f"description has {what}: check it is not private")
    snd = sound_report(e, outdir, e.get("private_names", []))
    fails += snd["missing"]
    fails += [f"audible line flagged at shot {r['shot']} {r['source']}: '{r['text']}' ({r['flag']})"
              for r in snd["flagged_unmuted"]]
    if not (outdir / f"{stem}.sound.md").is_file():
        fails.append(f"no {stem}.sound.md: run `vlog.py sound` and read every audible line")
    sheet = outdir / f"{stem}.sheet.jpg"
    cmd_sheet(argparse.Namespace(video=str(video), out=str(sheet), every=max(2.0, info["duration"] / 24)))
    report = {"video": str(video), "duration": round(info["duration"], 2), "loudness_lufs": li, "true_peak_db": tpk,
              "fails": fails, "notes": notes, "sheet": str(sheet)}
    (outdir / f"{stem}.verify.json").write_text(json.dumps(report, indent=2))
    for f in fails:
        print(f"FAIL {f}")
    for n in notes:
        print(f"NOTE {n}")
    print(f"{'ok' if not fails else 'not ready'}: {video.name} {info['duration']:.1f}s {li} LUFS; look at {sheet}")
    sys.exit(1 if fails else 0)



# ---------- sound: transcripts and sensitive speech ----------

FLAG_RE = re.compile(
    r"\d[\d .,-]{2,}\d|password|passcode|\bpin\b|m[aậ]t kh[aẩ]u|\bcard\b|\bthẻ\b|\bvisa\b|mastercard|\bbank\b|ng[aâ]n h[aà]ng|"
    r"t[aà]i kho[aả]n|\baccount\b|\bti[eề]n\b|dollar|NT\$|booking|[đd][aặ]t ph[oò]ng|passport|h[oộ] chi[eế]u|address|"
    r"[đd][iị]a ch[iỉ]|hotel|kh[aá]ch s[aạ]n|ph[oò]ng s[oố]|room number|\balo\b|\bg[oọ]i\b|(?<!-)\bcall(ed|ing)?\b(?! market)|\bslack\b|"
    r"密碼|信用卡|護照|地址|飯店|房號", re.I)


HALLUCINATION_RE = re.compile(r"subscribe|đăng ký kênh|ghiền mì gõ|thank you\.?$|the end$|cảm ơn các bạn đã theo dõi|字幕", re.I)


def doubtful(sg: dict) -> bool:
    """Whisper invents text on music, wind and silence: repeated tokens, low confidence, stock outro phrases."""
    text = sg.get("text", "").strip()
    return bool(float(sg.get("compression_ratio", 0)) > 2.4 or float(sg.get("avg_logprob", 0)) < -1.0
                or float(sg.get("no_speech_prob", 0)) > 0.6 or HALLUCINATION_RE.search(text))


def whisper_cmd() -> list[str]:
    env = os.environ.get("TRAVEL_VLOG_WHISPER")
    if env:
        return env.split()
    if shutil.which("mlx_whisper"):
        return ["mlx_whisper"]
    uvx = shutil.which("uvx")
    # A version-manager shim can exist on PATH and still fail outside its project, so run it once.
    if uvx and subprocess.run([uvx, "--version"], capture_output=True).returncode == 0:
        return [uvx, "--from", "mlx-whisper", "mlx_whisper"]
    die("no local Whisper: install mlx-whisper (Apple Silicon) or set TRAVEL_VLOG_WHISPER to a whisper CLI "
        "that takes '<audio> --output-format json --output-dir DIR'")


def cmd_transcribe(args) -> None:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for src in args.clips:
        dest = out / f"{Path(src).stem}.transcript.json"
        if dest.exists() and not args.force:
            print(f"have {dest.name}")
            continue
        with tempfile.TemporaryDirectory() as td:
            wav = Path(td) / f"{Path(src).stem}.wav"
            ffmpeg(["-i", src, "-vn", "-ac", "1", "-ar", "16000", str(wav)])
            cmd = whisper_cmd() + [str(wav), "--model", args.model, "--output-format", "json", "--output-dir", td,
                                   "--condition-on-previous-text", "False", "--word-timestamps", "True",
                                   "--hallucination-silence-threshold", "2", "--verbose", "False"]
            if args.language:
                cmd += ["--language", args.language]
            p = subprocess.run(cmd, capture_output=True, text=True)
            js = Path(td) / f"{wav.stem}.json"
            if p.returncode != 0 or not js.exists():
                die(f"whisper failed on {src}: {p.stderr.strip()[-800:]}")
            raw = json.loads(js.read_text())
        segs = [{"start": round(float(sg["start"]), 2), "end": round(float(sg["end"]), 2), "text": sg["text"].strip(),
                 "no_speech": round(float(sg.get("no_speech_prob", 0)), 2),
                 "logprob": round(float(sg.get("avg_logprob", 0)), 2),
                 "doubtful": doubtful(sg)} for sg in raw.get("segments", [])]
        dest.write_text(json.dumps({"clip": Path(src).name, "path": str(Path(src).resolve()), "model": args.model,
                                    "language": raw.get("language"), "segments": segs}, ensure_ascii=False, indent=1))
        print(f"transcribed {Path(src).name}: {len(segs)} segments, {raw.get('language')}")


def clip_key(path: str) -> str:
    m = CLIP_TIME_RE.search(Path(path).name)
    return f"{m['d']}_{m['t']}_{m['n']}" if m else Path(path).stem


def sound_report(e: dict, outdir: Path, names: list[str]) -> dict:
    tdir = Path(e.get("transcripts") or outdir)
    trans = {}
    for f in tdir.glob("*.transcript.json"):
        d = json.loads(f.read_text())
        trans[clip_key(d["clip"])] = d
    name_re = re.compile("|".join(re.escape(n) for n in names), re.I) if names else None
    rows, missing, flagged, listen, pos = [], [], [], [], 0.0
    for i, s in enumerate(e["shots"]):
        tin, tout, speed = float(s["in"]), float(s["out"]), float(s.get("speed", 1))
        audible = float(s.get("audio", 1.0)) > 0 and 0.5 <= speed <= 2
        if audible:
            d = trans.get(clip_key(s["src"]))
            if d is None:
                missing.append(f"shot {i + 1}: no transcript for {Path(s['src']).name}")
            else:
                for sg in d["segments"]:
                    if sg["end"] <= tin or sg["start"] >= tout or not sg["text"]:
                        continue
                    muted = any(float(a) <= max(sg["start"], tin) and float(b) >= min(sg["end"], tout)
                                for a, b in s.get("mute", []))
                    hit = FLAG_RE.search(sg["text"]) or (name_re.search(sg["text"]) if name_re else None)
                    row = {"shot": i + 1, "src": Path(s["src"]).name, "source": [sg["start"], sg["end"]],
                           "video": round(pos + (max(sg["start"], tin) - tin) / speed, 2), "text": sg["text"],
                           "muted": muted, "flag": hit.group(0) if hit else "", "doubtful": sg.get("doubtful", False)}
                    rows.append(row)
                    if hit and not muted and not row["doubtful"]:
                        flagged.append(row)
                    elif hit and not muted:
                        listen.append(row)
        pos += (tout - tin) / speed
    mutes = [{"shot": i + 1, "src": Path(s["src"]).name, "source": m} for i, s in enumerate(e["shots"])
             for m in s.get("mute", [])]
    return {"stem": e["stem"], "lines": rows, "muted_ranges": mutes, "missing": missing, "flagged_unmuted": flagged,
            "listen": listen}


def cmd_sound(args) -> None:
    e, outdir = load_edit(args.edit, writing=False)
    rep = sound_report(e, outdir, args.names or e.get("private_names", []))
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{e['stem']}.sound.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    md = [f"# {e['stem']}: what can be heard", "",
          "| video | shot | source | heard | state |", "|---|---|---|---|---|"]
    for r in rep["lines"]:
        state = "muted" if r["muted"] else (f"CHECK ({r['flag']})" if r["flag"] else "audible")
        if r.get("doubtful"):
            state += ", doubtful: listen"
        md.append(f"| {fmt_t(r['video'])} | {r['shot']} | {r['src']} {fmt_t(r['source'][0])}-{fmt_t(r['source'][1])} "
                  f"| {r['text'].replace('|', '/')} | {state} |")
    md += ["", "Muted ranges (source seconds):", ""] + [f"- shot {m['shot']} {m['src']} {m['source']}" for m in rep["muted_ranges"]]
    (outdir / f"{e['stem']}.sound.md").write_text("\n".join(md) + "\n")
    for m in rep["missing"]:
        print(f"FAIL {m}")
    for r in rep["flagged_unmuted"]:
        print(f"FAIL shot {r['shot']} {r['src']} {r['source']}: '{r['text']}' ({r['flag']}): mute it or cut it")
    for r in rep["listen"]:
        print(f"LISTEN shot {r['shot']} {r['src']} {r['source']}: '{r['text'][:80]}' ({r['flag']}) is doubtful "
              "(likely Whisper noise on music, wind or water): listen, then mute it or leave it")
    print(f"wrote {e['stem']}.sound.md: {len(rep['lines'])} audible lines; read every line before upload")
    sys.exit(1 if rep["missing"] or rep["flagged_unmuted"] else 0)


def cmd_sheet(args) -> None:
    need_pillow()
    info = media_info(args.video)
    with tempfile.TemporaryDirectory() as td:
        grabs = frame_grabs(args.video, "flat", float(args.every), info["duration"], Path(td), 320)
        contact_sheet(grabs, Path(args.out), 6, f"{Path(args.video).name}  {fmt_t(info['duration'])}")
    print(f"sheet {args.out}")


def main() -> None:
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            die(f"{tool} not found on PATH")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("index", help="contact sheets, audio activity and a description stub per clip")
    p.add_argument("clips", nargs="+")
    p.add_argument("--out", required=True)
    p.add_argument("--every", type=float, default=10.0, help="seconds between sampled frames")
    p.add_argument("--max-frames", type=int, default=120, help="cap per clip; long clips sample less often")
    p.add_argument("--cols", type=int, default=6)
    p.add_argument("--rows", type=int, default=5)
    p.add_argument("--clock-offset-hours", type=float, default=0.0, help="local time minus camera clock")
    p.add_argument("--talk-db", type=float, default=-32.0, help="speech-band level that counts as loud")
    p.set_defaults(fn=cmd_index)
    p = sub.add_parser("name", help="check a stem (and title) against the naming convention")
    p.add_argument("stem")
    p.add_argument("--title")
    p.set_defaults(fn=cmd_name)
    for name, fn, hlp in (("render", cmd_render, "render an edit list to <stem>.mp4"),
                          ("thumb", cmd_thumb, "make <stem>.jpg, 1280x720 under 2 MB"),
                          ("verify", cmd_verify, "check the render, thumbnail and recipe; exit 1 if not ready")):
        p = sub.add_parser(name, help=hlp)
        p.add_argument("edit")
        if name == "render":
            p.add_argument("--draft", action="store_true", help="fast low-quality render for a look")
        p.set_defaults(fn=fn)
    p = sub.add_parser("transcribe", help="local Whisper transcript per clip, cached as <clip>.transcript.json")
    p.add_argument("clips", nargs="+")
    p.add_argument("--out", required=True)
    p.add_argument("--model", default="mlx-community/whisper-large-v3-turbo")
    p.add_argument("--language", help="force a language code; default detects it")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_transcribe)
    p = sub.add_parser("sound", help="list every audible line of an edit list, flag sensitive ones; exit 1 if any is unmuted")
    p.add_argument("edit")
    p.add_argument("--names", nargs="*", help="names that must not be heard (also 'private_names' in the edit list)")
    p.set_defaults(fn=cmd_sound)
    p = sub.add_parser("sheet", help="contact sheet of any video")
    p.add_argument("video")
    p.add_argument("--out", required=True)
    p.add_argument("--every", type=float, default=5.0)
    p.set_defaults(fn=cmd_sheet)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
