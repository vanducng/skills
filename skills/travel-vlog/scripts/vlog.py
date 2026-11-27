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
                 "shade": "#000000", "stroke": "#000000", "card_fade": "#000000",
                 "caption": {"font": None, "size": 54, "color": "#FFFFFF", "box": "#000000", "box_alpha": 0.6,
                             "radius": 16, "pad": [28, 14], "bottom": 112, "fade": 0.2, "max_chars": 42}}
STYLE = dict(STYLE_DEFAULT)


def use_style(e: dict) -> None:
    """Channel look from the edit list's `style` block (font and colours from the written style guide)."""
    STYLE.clear()
    STYLE.update(STYLE_DEFAULT, **(e.get("style") or {}))
    STYLE["caption"] = {**STYLE_DEFAULT["caption"], **((e.get("style") or {}).get("caption") or {})}
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
    if v.get("track"):
        return track_filter(v, w, h, dur, fps, path)
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


def track_at(track: list, t: float) -> tuple[float, float]:
    """Yaw and pitch at t (seconds into the source range) along [[t, yaw, pitch], ...], eased between keys,
    turning the short way round."""
    pts = sorted((float(k[0]), float(k[1]), float(k[2]) if len(k) > 2 else 0.0) for k in track)
    if t <= pts[0][0]:
        return pts[0][1], pts[0][2]
    for (t0, y0, p0), (t1, y1, p1) in zip(pts, pts[1:]):
        if t <= t1:
            f = (t - t0) / max(t1 - t0, 1e-6)
            e = f * f * (3 - 2 * f)
            dy = (y1 - y0 + 180) % 360 - 180
            return y0 + dy * e, p0 + (p1 - p0) * e
    return pts[-1][1], pts[-1][2]


def track_filter(v: dict, w: int, h: int, dur: float, fps: float, path: Path) -> str:
    """A 360 view that follows a subject: `view.track` keys of [t, yaw, pitch], t in seconds from the shot's in."""
    fov = float(v.get("fov", DEFAULT_FOV))
    vfov = 2 * math.degrees(math.atan(math.tan(math.radians(fov / 2)) * h / w))
    y0, p0 = track_at(v["track"], 0)
    lines, n, prev = [], max(2, int(dur * fps)), (y0, p0)
    for i in range(1, n + 1):
        t = i / n * dur
        y, p = track_at(v["track"], t)
        lines.append(f"{t:.4f} v360@sphere yaw {(y - prev[0]):.4f},v360@camera pitch {(p - prev[1]):.4f};")
        prev = (y, p)
    path.write_text("\n".join(lines) + "\n")
    lens_fov = float(v.get("lens_fov", 200))
    return (f"sendcmd=f='{path}',"
            f"v360@sphere=input=dfisheye:output=equirect:ih_fov={lens_fov}:iv_fov={lens_fov}"
            f":yaw={y0}:roll={float(v.get('roll', 0))}:w=4096:h=2048,"
            f"v360@camera=input=equirect:output=flat:pitch={p0}:h_fov={fov}"
            f":v_fov={vfov:.3f}:w={w}:h={h}:interp=lanczos")



def view_samples(v: dict) -> list[tuple[dict, bool]]:
    """Static views a 360 shot passes through: (view, two_stage), two_stage for a move or a track, which
    turn the sphere first and aim the camera second."""
    if v.get("track"):
        ts = sorted(float(k[0]) for k in v["track"])
        ts += [(a + b) / 2 for a, b in zip(ts, ts[1:])]
        return [({**v, "yaw": y, "pitch": p}, True) for y, p in (track_at(v["track"], t) for t in ts)]
    if any(f"{k}_end" in v for k in ("yaw", "pitch", "fov")):
        out = []
        for f in (0, 0.5, 1):
            s = dict(v)
            for k in ("yaw", "pitch", "fov"):
                if f"{k}_end" in v:
                    a = float(v.get(k, DEFAULT_FOV if k == "fov" else 0))
                    s[k] = a + (float(v[f"{k}_end"]) - a) * f
            out.append((s, True))
        return out
    return [(v, False)]


def join_in_view(v: dict, two_stage: bool, w: int = 192, h: int = 108) -> bool:
    """True when the line where the two lenses meet shows in this view: a red and a blue half-frame are
    reframed by the same filter as the render, and both colours turn up."""
    vfov = 2 * math.degrees(math.atan(math.tan(math.radians(float(v.get("fov", DEFAULT_FOV)) / 2)) * h / w))
    lf, fov = float(v.get("lens_fov", 200)), float(v.get("fov", DEFAULT_FOV))
    if two_stage:
        vf = (f"v360=input=dfisheye:output=equirect:ih_fov={lf}:iv_fov={lf}:yaw={float(v.get('yaw', 0))}"
              f":roll={float(v.get('roll', 0))}:w=1024:h=512,v360=input=equirect:output=flat"
              f":pitch={float(v.get('pitch', 0))}:h_fov={fov}:v_fov={vfov:.3f}:w={w}:h={h}")
    else:
        vf = view_filter({**v, "type": None}, "dfisheye", w, h)
    src = "color=red:s=512x512:d=0.04[a];color=blue:s=512x512:d=0.04[b];[a][b]hstack"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-filter_complex", f"{src},{vf},format=rgb24", "-frames:v", "1",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    red = sum(1 for i in range(0, len(raw), 3) if raw[i] > 128 and raw[i + 2] < 100)
    blue = sum(1 for i in range(0, len(raw), 3) if raw[i + 2] > 128 and raw[i] < 100)
    return min(red, blue) > w * h * 0.01


def seam_problems(e: dict) -> list[str]:
    """360 shots on the dual-fisheye path whose view holds the join between the lenses: a person or the horizon
    breaks along it. Aim so the subject sits inside one lens, or set `view.stitch: "flow"`."""
    out = []
    for i, s in enumerate(e.get("shots", [])):
        v = s.get("view") or {}
        if v.get("type") == "tiny-planet" or v.get("stitch") == "flow" or ("yaw" not in v and not v.get("track")):
            continue
        if any(join_in_view(sv, two) for sv, two in view_samples(v)):
            out.append(f"shot {i + 1}: the lens join shows in the view (yaw {v.get('yaw')}); "
                       "the frame splits along it")
    return out

# ---------- people in the frame ----------

PEOPLE_SWIFT = Path(__file__).with_name("people.swift")
STITCH = Path(__file__).with_name("stitch.py")


def people_cmd() -> list[str]:
    """Apple Vision person and face finder, compiled once into the cache (macOS); TRAVEL_VLOG_PEOPLE overrides it
    with any command that takes image paths and prints the same JSON lines."""
    env = os.environ.get("TRAVEL_VLOG_PEOPLE")
    if env:
        return env.split()
    src = PEOPLE_SWIFT.read_bytes()
    exe = Path.home() / ".cache" / "travel-vlog" / f"people-{hashlib.sha256(src).hexdigest()[:12]}"
    if not exe.exists():
        if not shutil.which("swiftc"):
            die("finding people needs macOS with swiftc (Apple Vision), or TRAVEL_VLOG_PEOPLE set to a detector")
        exe.parent.mkdir(parents=True, exist_ok=True)
        run(["swiftc", "-O", str(PEOPLE_SWIFT), "-o", str(exe)])
    return [str(exe)]


def detect_people(images: list[Path]) -> list[dict]:
    if not images:
        return []
    out = run(people_cmd() + [str(p) for p in images], capture=True).stdout
    found = {}
    for line in out.splitlines():
        d = json.loads(line)
        found[d["image"]] = d
    return [found.get(str(p), {"people": [], "faces": []}) for p in images]


def shot_people(s: dict, e: dict, tmp: Path, every: float) -> dict:
    """Sample a footage shot every `every` s: who is in the view, and for a 360 shot who is anywhere in the sphere
    (as yaw and pitch), so a view that misses the people can be told from a shot with nobody in it."""
    info = media_info(s["src"])
    proj = s.get("projection") or projection_of(info, s["src"])
    tin, tout = float(s["in"]), float(s["out"])
    view = s.get("view", {})
    times = [tin + k * every for k in range(int((tout - tin) / every) + 1) if tin + k * every < tout]
    w, h = 640, 360
    views, spheres, wides = [], [], []
    fov = float(view.get("fov", DEFAULT_FOV))
    wfov = min(150.0, fov + 45)
    for k, t in enumerate(times):
        if proj in ("dfisheye", "insv"):
            v = dict(view)
            if v.get("track"):
                v["yaw"], v["pitch"] = track_at(v["track"], t - tin)
            vf = view_filter(v, proj, w, h)
            sp, wp = tmp / f"s{k:04d}.jpg", tmp / f"w{k:04d}.jpg"
            ffmpeg(["-ss", f"{t}", "-i", s["src"], "-frames:v", "1", "-filter_complex",
                    f"{video_in(proj)}v360=input=dfisheye:output=equirect:ih_fov=200:iv_fov=200:w=2048:h=1024", str(sp)])
            ffmpeg(["-ss", f"{t}", "-i", s["src"], "-frames:v", "1", "-filter_complex",
                    f"{video_in(proj)}{view_filter({**v, 'fov': wfov}, proj, w * 3 // 2, h * 3 // 2)}", str(wp)])
            spheres.append(sp)
            wides.append(wp)
        else:
            lens = s.get("lens", e.get("lens"))
            vf = square_pixels(info) + lens_filter(lens, w, h) + view_filter(view, proj, w, h, is_portrait(info, view))
        vp = tmp / f"v{k:04d}.jpg"
        ffmpeg(["-ss", f"{t}", "-i", s["src"], "-frames:v", "1", "-filter_complex", f"{video_in(proj)}{vf}", str(vp)])
        views.append(vp)
    seen = detect_people(views)
    around = detect_people(spheres) if spheres else [None] * len(views)
    wide = detect_people(wides) if wides else [{}] * len(views)
    k = math.tan(math.radians(wfov / 2)) / math.tan(math.radians(fov / 2))
    samples = []
    for t, v, wd in zip(times, seen, wide):
        row = {"t": round(t - tin, 2), "in_view": len(v.get("people", [])) + len(v.get("faces", [])),
               "cut": edge_cuts(v, in_view(wd, k)), "words": sum(len(x["text"].split()) for x in v.get("text", []))}
        a = around[len(samples)]
        if a is not None:
            row["sphere"] = [[round((b[0] + b[2] / 2 - 0.5) * 360, 1), round((0.5 - b[1] - b[3] / 2) * 180, 1)]
                             for b in a.get("people", [])]
        samples.append(row)
    return {"projection": proj, "every": every, "samples": samples}


EDGE = 0.01  # a box this close to the frame edge is cut by it


def touches(b: list) -> bool:
    x, y, w, h = b
    return x <= EDGE or y <= EDGE or x + w >= 1 - EDGE or y + h >= 1 - EDGE


def in_view(wide: dict, k: float) -> dict:
    """Boxes found in a wider look around the same view, in the view's own 0-1 frame (they may run past it): a
    subject cut by the view's edge is often not found inside the view at all."""
    def m(b):
        x0, y0, x1, y1 = (0.5 + (c - 0.5) * k for c in (b[0], b[1], b[0] + b[2], b[1] + b[3]))
        return [x0, y0, x1 - x0, y1 - y0]

    def seen(b):
        return b[0] < 1 and b[1] < 1 and b[0] + b[2] > 0 and b[1] + b[3] > 0

    out = {key: [m(b) for b in wide.get(key, []) if seen(m(b))] for key in ("people", "faces", "objects")}
    out["text"] = [{**x, "box": m(x["box"])} for x in wide.get("text", []) if seen(m(x["box"]))]
    return out


def edge_cuts(found: dict, around: dict | None = None) -> dict:
    """What the frame edge cuts in one view: a face at any edge, a person at the top or the sides (a body may run
    out at the bottom), text, and the largest salient object; `around` adds what a wider look saw."""
    around = around or {}
    faces = found.get("faces", []) + around.get("faces", [])
    bodies = found.get("people", []) + around.get("people", [])
    texts = [x["box"] for x in found.get("text", []) + around.get("text", [])]
    objs = sorted(found.get("objects", []), key=lambda b: b[2] * b[3], reverse=True)[:1]
    side = lambda b: b[3] > 0.25 and (b[0] <= EDGE or b[1] <= EDGE or b[0] + b[2] >= 1 - EDGE)
    return {"people": sum(touches(b) for b in faces) + sum(side(b) for b in bodies),
            "sign": sum(touches(b) for b in texts),
            "object": sum(touches(b) for b in objs)}


def read_time(words: int) -> float:
    """Seconds a viewer needs to read a sign: 2 s plus 0.3 s a word, at most 5 s."""
    return min(5.0, 2 + 0.3 * words)


def subject_problems(e: dict, rep: dict | None) -> list[str]:
    """The shot's `subject` (people, by default; or sign, object) whole in the frame for all but one sample, and a
    sign held long enough to read."""
    if rep is None:
        return []
    probs = []
    for i, s in enumerate(e["shots"]):
        r = rep["shots"].get(str(i + 1))
        if s.get("still") or not r or "cut" not in (r["samples"] or [{}])[0]:
            continue
        kind = s.get("subject", "people")
        cut = [sm["t"] for sm in r["samples"] if sm["cut"].get(kind)]
        if len(cut) > 1:
            probs.append(f"shot {i + 1}: the frame edge cuts the {kind} at {', '.join(f'{t:g}' for t in cut[:4])} s; "
                         "frame all of it with a margin (`vlog.py fit` for a 360 view)")
        if kind == "sign":
            words = max((sm["words"] for sm in r["samples"]), default=0)
            held = (float(s["out"]) - float(s["in"])) / float(s.get("speed", 1))
            if held < read_time(words):
                probs.append(f"shot {i + 1}: a sign of {words} words needs {read_time(words):.1f} s; it is held {held:.1f} s")
    return probs


def empty_runs(samples: list[dict], every: float, need_elsewhere: bool) -> float:
    """Longest stretch (s) with nobody in the view; for 360 only while somebody is elsewhere in the sphere."""
    best = cur = 0.0
    for sm in samples:
        empty = sm["in_view"] == 0 and (not need_elsewhere or bool(sm.get("sphere")))
        cur = cur + every if empty else 0.0
        best = max(best, cur)
    return best


def people_problems(e: dict, rep: dict | None) -> list[str]:
    """A shot may show nobody only when it says what it shows instead (`landmark`)."""
    if rep is None:
        return ["no people check: run `vlog.py people` on the edit list"]
    probs = []
    for i, s in enumerate(e["shots"]):
        r = rep["shots"].get(str(i + 1))
        if s.get("still") or s.get("landmark") or not r:
            continue
        is360 = r["projection"] in ("dfisheye", "insv")
        run_s = empty_runs(r["samples"], r["every"], need_elsewhere=is360)
        if run_s > 3:
            where = "while people are elsewhere in the sphere: aim the view at them (view.track)" if is360 \
                else "with nobody in it: pick a range with the people, or name the `landmark` it shows"
            probs.append(f"shot {i + 1}: {run_s:.1f} s of view {where}")
    return probs


def subject_boxes(found: dict, subject: str) -> list:
    """Boxes of the shot's subject in one view: people are their faces and heads (the top of a body box)."""
    if subject == "people":
        return found.get("faces", []) + [[x, y, w, min(h, w)] for x, y, w, h in found.get("people", [])]
    if subject == "sign":
        return [t["box"] for t in found.get("text", [])]
    return sorted(found.get("objects", []), key=lambda b: b[2] * b[3], reverse=True)[:1]


def fit_step(view: dict, boxes: list, margin: float = 0.08, w: int = 16, h: int = 9) -> dict:
    """The next view: aim at the middle of the boxes and widen (at most MAX_FOV) or narrow so they fill the frame
    inside the margin. Small-angle steps; `fit` repeats it on a fresh look."""
    x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    x1, y1 = max(b[0] + b[2] for b in boxes), max(b[1] + b[3] for b in boxes)
    fov = float(view.get("fov", DEFAULT_FOV))
    vfov = 2 * math.degrees(math.atan(math.tan(math.radians(fov / 2)) * h / w))
    need = max((x1 - x0) * fov, 2 * math.degrees(math.atan(math.tan(math.radians((y1 - y0) * vfov / 2)) * w / h)))
    return {**view, "yaw": round(float(view.get("yaw", 0)) + ((x0 + x1) / 2 - 0.5) * fov, 1),
            "pitch": round(float(view.get("pitch", 0)) - ((y0 + y1) / 2 - 0.5) * vfov, 1),
            "fov": round(min(MAX_FOV, max(50.0, need * (1 + 2 * margin) * 1.1)), 1)}


def cmd_fit(args) -> None:
    """Suggest a 360 view that holds the whole subject at one moment: start from --yaw/--pitch/--fov, look, aim at
    the subject and size the view to it, and repeat until it sits inside the margin."""
    info = media_info(args.src)
    proj = projection_of(info, args.src)
    if proj not in ("dfisheye", "insv"):
        die("fit is for 360 footage; on flat footage pick a crop that keeps the subject whole")
    view = {"yaw": args.yaw, "pitch": args.pitch, "fov": args.fov, "roll": args.roll}
    with tempfile.TemporaryDirectory() as td:
        for k in range(6):
            vp = Path(td) / f"v{k}.jpg"
            ffmpeg(["-ss", f"{args.t}", "-i", args.src, "-frames:v", "1", "-filter_complex",
                    f"{video_in(proj)}{view_filter(view, proj, 640, 360)}", str(vp)])
            boxes = subject_boxes(detect_people([vp])[0], args.subject)
            if not boxes:
                die(f"no {args.subject} in the view at {args.t} s: aim nearer with --yaw/--pitch")
            whole = not any(touches(b) for b in boxes)
            inside = all(b[0] >= 0.08 and b[1] >= 0.08 and b[0] + b[2] <= 0.92 and b[1] + b[3] <= 0.92 for b in boxes)
            if inside or (whole and k):
                break
            view = fit_step(view, boxes)
    print(json.dumps({"t": args.t, **view, "whole": whole}))
    if not whole:
        print(f"the {args.subject} does not fit at fov {MAX_FOV}: frame the faces (or the text) first and show the "
              "rest with a pan or a second angle", file=sys.stderr)
        sys.exit(1)


def cmd_people(args) -> None:
    e, outdir = load_edit(args.edit, writing=False)
    shots = {}
    with tempfile.TemporaryDirectory() as td:
        for i, s in enumerate(e["shots"]):
            if s.get("still"):
                continue
            d = Path(td) / f"{i:03d}"
            d.mkdir()
            shots[str(i + 1)] = shot_people(s, e, d, args.every)
    rep = {"edit_sha256": sha256(Path(args.edit)), "every_s": args.every, "shots": shots}
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{e['stem']}.people.json").write_text(json.dumps(rep, indent=1))
    probs = people_problems(e, rep) + subject_problems(e, rep)
    for p in probs:
        print(f"FAIL {p}")
    print(f"wrote {e['stem']}.people.json: {len(shots)} shots; {len(probs)} problems")
    sys.exit(1 if probs else 0)


def cmd_find_people(args) -> None:
    """Where the people are in whole clips, as source ranges, for picking shots."""
    for src in args.clips:
        dur = media_info(src)["duration"]
        with tempfile.TemporaryDirectory() as td:
            r = shot_people({"src": src, "in": 0, "out": dur}, {}, Path(td), args.every)
        ranges, start = [], None
        for sm in r["samples"] + [{"t": dur, "in_view": 0}]:
            on = sm["in_view"] > 0 or bool(sm.get("sphere"))
            if on and start is None:
                start = sm["t"]
            if not on and start is not None:
                ranges.append((start, sm["t"]))
                start = None
        print(f"{Path(src).name}: people at " + (", ".join(f"{a:.0f}-{b:.0f}" for a, b in ranges if b - a >= args.every) or "none"))


# ---------- text overlays ----------

def title_png(title: dict, w: int, h: int, out: Path) -> None:
    """Lower-left place/time title with a soft shadow, transparent PNG."""
    from PIL import Image, ImageDraw, ImageFilter
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shade = float(STYLE.get("title_shade") or 0)
    if shade:
        # style.title_shade: the shade colour at this opacity in the lower-left corner, gone at 60 % of the width
        # and 45 % of the height, so a pale background cannot wash out the title
        from PIL import ImageChops
        ramp = Image.linear_gradient("L")  # 0 at the top, 255 at the bottom
        fy = ramp.resize((w, h)).point(lambda v: max(0, int((v - 255 * 0.55) / 0.45)))
        fx = ramp.transpose(Image.Transpose.ROTATE_270).resize((w, h)).point(lambda v: max(0, int((v - 255 * 0.4) / 0.6)))
        mask = ImageChops.darker(fx, fy).point(lambda v: int(v * shade)).filter(ImageFilter.GaussianBlur(60 * h / 1080))
        img.paste(Image.new("RGBA", (w, h), rgb(STYLE["shade"], 255)), (0, 0), mask)
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


def caption_png(text: str, w: int, h: int, out: Path) -> None:
    """One line centred low in the frame on a rounded translucent box (style.caption, sizes in 1080p pixels)."""
    from PIL import Image, ImageDraw, ImageFont
    c, k = STYLE["caption"], h / 1080
    font = ImageFont.truetype(c["font"], int(c["size"] * k)) if c.get("font") and Path(c["font"]).is_file() \
        else load_font(int(c["size"] * k))
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    left, top, right, bottom = d.textbbox((0, 0), text, font=font, anchor="ls")
    px, py = int(c["pad"][0] * k), int(c["pad"][1] * k)
    bw, bh = right - left + 2 * px, bottom - top + 2 * py
    x0, y1 = (w - bw) // 2, h - int(c["bottom"] * k)
    d.rounded_rectangle([x0, y1 - bh, x0 + bw, y1], int(c["radius"] * k), fill=rgb(c["box"], int(255 * float(c["box_alpha"]))))
    d.text((x0 + px, y1 - bh + py - top), text, font=font, fill=rgb(c["color"], 255), anchor="ls")
    img.save(out)


def caption_of(s: dict) -> dict | None:
    c = s.get("caption")
    if not c:
        return None
    c = dict(c) if isinstance(c, dict) else {"text": c}
    n = len(c["text"])
    c.setdefault("at", 0.5)
    c.setdefault("dur", c.get("hold", min(3.0, max(2.0, 0.6 + 0.07 * n))))
    return c


def card_problems(e: dict) -> list[str]:
    """Map cards and captions: the limits the style guide sets."""
    probs, stills, pos, last_cap = [], 0, 0.0, None
    max_chars = int(STYLE["caption"]["max_chars"])
    for i, s in enumerate(e["shots"]):
        dur = (float(s["out"]) - float(s["in"])) / float(s.get("speed", 1))
        if s.get("still"):
            stills += 1
            if s.get("caption") or s.get("title") or s.get("hook"):
                probs.append(f"shot {i + 1}: a card draws no caption, title or hook; put it on a footage shot")
            if not 2.5 <= dur <= 4:
                probs.append(f"shot {i + 1}: a card holds 2.5 to 4 s, not {dur:.1f}")
        c = caption_of(s)
        if c:
            a, b = float(c["at"]), float(c["at"]) + float(c["dur"])
            if i == 0:
                probs.append("shot 1: no caption on the opening shot (the title is there)")
            if len(c["text"]) > max_chars or "\n" in c["text"]:
                probs.append(f"shot {i + 1}: caption over {max_chars} characters or more than one line")
            if b > dur:
                probs.append(f"shot {i + 1}: caption ends after the shot")
            if s.get("title") or s.get("hook"):
                probs.append(f"shot {i + 1}: caption and a title on the same shot")
            if last_cap is not None and pos + a - last_cap < 10:
                probs.append(f"shot {i + 1}: captions less than 10 s apart")
            last_cap = pos + b
        pos += dur
    if stills > 1:
        probs.append(f"{stills} cards; one map card per video")
    return probs


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
        if s.get("kind") == "still":
            s["still"] = s["src"]
        if s.get("still"):
            # A card (map, title): a PNG held for dur seconds, silent, faded in and out.
            dur = float(s["dur"]) if "dur" in s else float(s.get("out", 4)) - float(s.get("in", 0))
            s.update(src=s["still"], **{"in": 0.0, "out": dur}, audio=0)
        if not Path(s["src"]).is_file():
            die(f"shot {i}: source not found: {s['src']}")
        if float(s["out"]) <= float(s["in"]):
            die(f"shot {i}: out must be after in")
        if writing and not s.get("still") and outdir.resolve() == Path(s["src"]).resolve().parent:
            die("output_dir is the footage folder; originals stay read-only, write elsewhere")
    return e, outdir


def planned_duration(e: dict) -> float:
    return sum((float(s["out"]) - float(s["in"])) / float(s.get("speed", 1)) for s in e["shots"])


def upright(img: Path, tmp: Path) -> Path:
    """A phone photo as it is meant to be seen: ffmpeg reads the stored pixels and ignores the EXIF orientation, so a
    portrait photo comes out on its side or, squeezed into a frame, stretched."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return img
    with Image.open(img) as im:
        if im.getexif().get(0x0112, 1) == 1:
            return img
        out = tmp / f"upright-{img.stem}.png"
        ImageOps.exif_transpose(im).save(out)
        return out


def render_still(i: int, s: dict, w: int, h: int, fps: float, tmp: Path, draft: bool) -> Path:
    dur = float(s["out"])
    fin, fout = float(s.get("fade_in", s.get("fade", 0.4))), float(s.get("fade_out", s.get("fade", 0.4)))
    col = STYLE["card_fade"].replace("#", "0x")
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:{col},setsar=1,"
          f"fps={fps},format=yuv420p")
    if fin:
        vf += f",fade=t=in:d={fin}:color={col}"
    if fout:
        vf += f",fade=t=out:st={max(0.0, dur - fout)}:d={fout}:color={col}"
    out = tmp / f"shot{i:02d}.mov"
    ffmpeg(["-loop", "1", "-t", f"{dur}", "-i", str(upright(Path(s["src"]), tmp)), "-f", "lavfi", "-t", f"{dur}", "-i", "anullsrc=r=48000:cl=stereo",
            "-vf", vf, "-map", "0:v", "-map", "1:a", "-t", f"{dur}", "-c:v", "libx264",
            "-preset", "ultrafast" if draft else "medium", "-crf", "26" if draft else "17", "-c:a", "pcm_s16le", str(out)])
    return out


def stitched(s: dict, view: dict, w: int, h: int, fps: float) -> Path:
    """A 360 shot with `view.stitch: "flow"` as a flat clip whose lens join is flow-aligned (stitch.py), cached by its
    inputs: the view never splits along the join, even with a person on it."""
    if projection_of(media_info(s["src"]), s["src"]) != "insv":
        die(f"{s['src']}: stitch needs the .insv master (two fisheye streams)")
    args = [s["src"], f"{float(s['in'])}", f"{float(s['out'])}"]
    opts = ["--yaw", f"{float(view.get('yaw', 0))}", "--pitch", f"{float(view.get('pitch', 0))}",
            "--roll", f"{float(view.get('roll', 0))}", "--fov", f"{float(view.get('fov', DEFAULT_FOV))}",
            "--size", f"{w}x{h}", "--fps", f"{fps}"]
    key = hashlib.sha256(json.dumps([args, opts, view.get("track"), view.get("roll_track"),
                                     STITCH.read_bytes().hex()]).encode()).hexdigest()[:16]
    cache = Path.home() / ".cache" / "travel-vlog" / "stitch"
    out = cache / f"{key}.mp4"
    if out.is_file():
        return out
    cache.mkdir(parents=True, exist_ok=True)
    for k, flag in (("track", "--track"), ("roll_track", "--roll-track")):
        if view.get(k):
            jf = cache / f"{key}.{k}.json"
            jf.write_text(json.dumps(view[k]))
            opts += [flag, str(jf)]
    if not shutil.which("uv"):
        die("stitch needs uv (it runs stitch.py with numpy and opencv)")
    part = cache / f"{key}.part.mp4"
    run(["uv", "run", "--no-project", "--with", "numpy", "--with", "opencv-python-headless", "python3",
         str(STITCH), *args, str(part), *opts])
    part.rename(out)
    return out


def render_shot(i: int, s: dict, e: dict, w: int, h: int, fps: float, tmp: Path, draft: bool) -> Path:
    if s.get("still"):
        return render_still(i, s, w, h, fps, tmp, draft)
    src = s["src"]
    info = media_info(src)
    proj = s.get("projection") or projection_of(info, src)
    tin, tout = float(s["in"]), float(s["out"])
    speed = float(s.get("speed", 1))
    dur = (tout - tin) / speed
    view = s.get("view", {})
    lens = s.get("lens", e.get("lens")) if proj == "flat" else None
    if view.get("stitch") == "flow" and proj in ("dfisheye", "insv"):
        src, proj, view, lens = str(stitched(s, view, w, h, fps)), "flat", {}, None
        tin, tout = 0.0, tout - tin
        info = media_info(src)
    vf = []
    cmdfile = tmp / f"shot{i:02d}.cmd"
    pan = proj in ("dfisheye", "insv") and pan_filter(view, w, h, dur * speed, info.get("fps", fps) or fps, cmdfile)
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
        overlays.append((hp, 0.15, min(dur - 0.1, float(s.get("hook_s", 2.6))), 0.35))
    if s.get("title"):
        tp = tmp / f"title{i:02d}.png"
        title_png(s["title"], w, h, tp)
        t0 = float(s["title"].get("at", 0.4))
        overlays.append((tp, t0, min(dur - 0.1, t0 + float(s["title"].get("hold", 3.2))), 0.35))
    c = caption_of(s)
    if c:
        cp = tmp / f"caption{i:02d}.png"
        caption_png(c["text"], w, h, cp)
        c0 = float(c["at"])
        overlays.append((cp, c0, min(dur - 0.1, c0 + float(c["dur"])), float(STYLE["caption"]["fade"])))
    for k, (png, a, b, fd) in enumerate(overlays):
        inputs += ["-loop", "1", "-t", f"{dur}", "-i", str(png)]
        fc += (f";[{n_in}:v]format=rgba,fade=t=in:st={a}:d={fd}:alpha=1,fade=t=out:st={max(a, b - fd)}:d={fd}:alpha=1[o{k}]"
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
    probs = fov_problems(e) + seam_problems(e) + holder_problems(e) + card_problems(e)
    if probs:
        die("; ".join(probs))
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
        fc = ""
        music = e.get("music") or []
        if music:
            duck = e.get("duck", {"threshold": 0.03, "ratio": 6, "attack": 80, "release": 600})
            mus_labels = []
            fc += "[0:a]asplit=2[cam][sc];" if duck else "[0:a]anull[cam];"
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
        # The audio is mixed in its own pass: in one graph with the video encode, ffmpeg 9 starved the looped
        # music input behind a slow video chain and wrote seconds of digital silence under a card.
        mix_wav = tmp / "mix.wav"
        ffmpeg([*inputs, "-filter_complex", fc, "-map", "[am]", "-t", f"{total}", "-c:a", "pcm_s16le", str(mix_wav)])
        mixed = tmp / "mixed.mov"
        ffmpeg(["-i", str(joined), "-i", str(mix_wav), "-filter_complex",
                f"[0:v]fade=t=in:d={fade},fade=t=out:st={max(0, total - fade)}:d={fade}[v]",
                "-map", "[v]", "-map", "1:a", "-t", f"{total}",
                "-c:v", "libx264", "-preset", "ultrafast" if args.draft else "slow", "-crf", "26" if args.draft else "18",
                "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", str(mixed)])
        meas = loudnorm_pass(mixed, target, tp)
        finite = all(math.isfinite(float(meas[k])) for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset"))
        ln = f"loudnorm=I={target}:TP={tp}:LRA=11" if not finite else (f"loudnorm=I={target}:TP={tp}:LRA=11:measured_I={meas['input_i']}:measured_TP={meas['input_tp']}"
              f":measured_LRA={meas['input_lra']}:measured_thresh={meas['input_thresh']}"
              f":offset={meas['target_offset']}:linear=true")
        ffmpeg(["-i", str(mixed), "-map", "0:v", "-map", "0:a", "-c:v", "copy", "-af", f"{ln},aresample=48000,apad", "-shortest",
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


def silent_gaps(video: Path, min_s: float = 1.0, floor_db: int = -45) -> list[tuple[float, float]]:
    """Stretches of near-silence: with a music bed under the whole video there should be none."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(video), "-vn", "-af",
                        f"silencedetect=n={floor_db}dB:d={min_s}", "-f", "null", "-"], capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", p.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", p.stderr)]
    return list(zip(starts, ends + [media_info(video)["duration"]] * (len(starts) - len(ends))))


def bed_gaps(video: Path, dur: float) -> list[tuple[float, float]]:
    """Silent stretches with at least 1 s inside the video's middle (the first and last 1.5 s may fade)."""
    return [(a, b) for a, b in silent_gaps(video) if min(b, dur - 1.5) - max(a, 1.5) >= 1.0]


def cmd_verify(args) -> None:
    need_pillow()
    from PIL import Image
    e, outdir = load_edit(args.edit, writing=False)
    stem = e["stem"]
    video = outdir / f"{stem}.mp4"
    fails, notes = [], []
    w, h = e.get("size", [1920, 1080])
    lo, hi = e.get("length_s", [180, 360])
    use_style(e)
    fails += fov_problems(e) + seam_problems(e) + holder_problems(e) + card_problems(e)
    pj = outdir / f"{stem}.people.json"
    prep = json.loads(pj.read_text()) if pj.is_file() else None
    if prep and prep.get("edit_sha256") != sha256(Path(args.edit)):
        prep = None
    fails += people_problems(e, prep) + subject_problems(e, prep)
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
    if e.get("music"):
        for a, b in bed_gaps(video, info["duration"]):
            fails.append(f"silent {a:.2f}-{b:.2f}s under the music bed: the music must play through")
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
    r"\d(?:[ .,-]?\d){5,}|password|passcode|\bpin\b|m[aậ]t kh[aẩ]u|\bcard\b|\bthẻ\b|\bvisa\b|mastercard|\bbank\b|ng[aâ]n h[aà]ng|"
    r"t[aà]i kho[aả]n|\baccount\b|\bti[eề]n\b|dollar|NT\$|booking|[đd][aặ]t ph[oò]ng|passport|h[oộ] chi[eế]u|address|"
    r"[đd][iị]a ch[iỉ]|hotel|kh[aá]ch s[aạ]n|ph[oò]ng s[oố]|room number|\balo\b|\bg[oọ]i\b|(?<!-)\bcall(ed|ing)?\b(?! market)|\bslack\b|"
    r"密碼|信用卡|護照|地址|飯店|房號", re.I)


# a short number is a secret only next to one of these (a PIN, a card); a year or a time is not
SECRET_WORD_RE = re.compile(r"\bpin\b|passcode|password|m[aậ]t kh[aẩ]u|\bm[aã] s[oố]\b|\bcard\b|\bthẻ\b|密碼", re.I)


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
    tdir = Path(e.get("transcripts") or (outdir / "index" if (outdir / "index").is_dir() else outdir))
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
                    hit = (FLAG_RE.search(sg["text"]) or (name_re.search(sg["text"]) if name_re else None)
                           or (re.search(r"\b\d{4,5}\b", sg["text"]) if SECRET_WORD_RE.search(sg["text"]) else None))
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
    p = sub.add_parser("people", help="who is in each shot's view (and the 360 sphere); fail empty views over 3 s")
    p.add_argument("edit")
    p.add_argument("--every", type=float, default=1.0)
    p.set_defaults(fn=cmd_people)
    p = sub.add_parser("fit", help="a 360 view (yaw, pitch, fov) that holds the whole subject at one moment")
    p.add_argument("src")
    p.add_argument("t", type=float)
    for k, d in (("yaw", 0.0), ("pitch", 0.0), ("roll", 0.0), ("fov", float(DEFAULT_FOV))):
        p.add_argument(f"--{k}", type=float, default=d, help="the view to start from")
    p.add_argument("--subject", choices=["people", "sign", "object"], default="people")
    p.set_defaults(fn=cmd_fit)
    p = sub.add_parser("find-people", help="source ranges where people are in whole clips, for picking shots")
    p.add_argument("clips", nargs="+")
    p.add_argument("--every", type=float, default=1.0)
    p.set_defaults(fn=cmd_find_people)
    p = sub.add_parser("sheet", help="contact sheet of any video")
    p.add_argument("video")
    p.add_argument("--out", required=True)
    p.add_argument("--every", type=float, default=5.0)
    p.set_defaults(fn=cmd_sheet)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
