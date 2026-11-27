#!/usr/bin/env python3
"""stitch.py: flat view from an Insta360 X5 .insv with a flow-aligned join (no hard seam).

uv run --no-project --with numpy --with opencv-python-headless python stitch.py SRC T_IN T_OUT OUT.mp4
    [--yaw Y --pitch P | --track JSON] [--roll R] [--fov F] [--size 1920x1080] [--fps 25]
    [--band 7] [--flow-smooth 0.5] [--seam-only] [--crf 12]

Geometry (checked against ffmpeg v360 dfisheye ih_fov=200, same yaw/pitch/roll/fov to within a frame of motion):
    ray = normalise((u, -v, 1)); world = R @ ray, R = Ry(yaw) Rx(-pitch) Rz(-roll)
    lens 0 (stream v:0) sees `world` at angle theta0 = acos(z); lens 1 (stream v:1) is turned 180 deg about y.
    equidistant fisheye, 100 deg half angle at the circle edge.
The join is at theta0 = 90 deg. Hard join = what the skill does now. Here, inside theta0 = 90 +- BAND deg:
    1. render the view from each lens separately;
    2. dense optical flow lens0 -> lens1 on locally normalised grey (DIS), smoothed in space and in time;
    3. warp both views to the in-between position (t = 0 at the lens 0 edge of the band, 1 at the lens 1 edge) and mix (1-t, t).
Faces, caps and the horizon land on each other before they mix, so there is no step and no ghost.
Audio is copied from the source range. Output: H.264 CRF 12 flat clip, usable as a flat source in an edit list.
--track JSON: list of [t, yaw, pitch] (t from the start of the range), smoothstep between keys.
"""
import argparse, json, math, os, subprocess, time
import numpy as np
import cv2

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("tin", type=float); ap.add_argument("tout", type=float); ap.add_argument("out")
ap.add_argument("--yaw", type=float, default=0); ap.add_argument("--pitch", type=float, default=0)
ap.add_argument("--roll", type=float, default=0); ap.add_argument("--fov", type=float, default=95)
ap.add_argument("--track"); ap.add_argument("--size", default="1920x1080"); ap.add_argument("--fps", type=float, default=25)
ap.add_argument("--band", type=float, default=7.0)
ap.add_argument("--flow-smooth", type=float, default=0.5)
ap.add_argument("--seam-only", action="store_true")
ap.add_argument("--crf", type=int, default=12)
ap.add_argument("--roll-track", help="json list of [t, roll]")
a = ap.parse_args()
W, H = (int(v) for v in a.size.split("x"))
DUR = a.tout - a.tin
N = int(round(DUR * a.fps))
LENS = 2880
rad = math.radians


def interp(track, t):
    pts = sorted(tuple(float(v) for v in k) for k in track)
    if t <= pts[0][0]: return pts[0][1:]
    for p, q in zip(pts, pts[1:]):
        if t <= q[0]:
            f = (t - p[0]) / max(q[0] - p[0], 1e-6); e = f * f * (3 - 2 * f)
            out = []
            for i in range(1, len(p)):
                d = q[i] - p[i]
                out.append(p[i] + d * e)
            return tuple(out)
    return pts[-1][1:]


def Rx(a_): c, s = math.cos(a_), math.sin(a_); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], np.float32)
def Ry(a_): c, s = math.cos(a_), math.sin(a_); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], np.float32)
def Rz(a_): c, s = math.cos(a_), math.sin(a_); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], np.float32)


f_px = (W / 2) / math.tan(rad(a.fov / 2))
xs, ys = np.meshgrid(np.arange(W, dtype=np.float32) + 0.5, np.arange(H, dtype=np.float32) + 0.5)
RAY = np.stack([(xs - W / 2) / f_px, -(ys - H / 2) / f_px, np.ones_like(xs)], -1)
RAY /= np.linalg.norm(RAY, axis=-1, keepdims=True)
RAY = RAY.reshape(-1, 3)


def maps(yaw, pitch, roll):
    M = Ry(rad(yaw)) @ Rx(rad(-pitch)) @ Rz(rad(-roll))
    w = (RAY @ M.T).reshape(H, W, 3)
    th0 = np.arccos(np.clip(w[..., 2], -1, 1))
    th1 = np.arccos(np.clip(-w[..., 2], -1, 1))
    ph0 = np.arctan2(w[..., 1], w[..., 0])
    ph1 = np.arctan2(w[..., 1], -w[..., 0])
    R0 = LENS / 2
    def mp(th, ph):
        r = th / rad(100) * R0
        return (np.ascontiguousarray(R0 + r * np.cos(ph), np.float32), np.ascontiguousarray(R0 - r * np.sin(ph), np.float32))
    return th0, mp(th0, ph0), mp(th1, ph1)


base = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error"]
def lens_cmd(lens):
    return base + ["-ss", f"{a.tin}", "-t", f"{DUR}", "-i", a.src, "-map", f"0:v:{lens}", "-vf", f"fps={a.fps}",
                   "-frames:v", str(N), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]


def frames_of(p):
    n = LENS * LENS * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n: return
        yield np.frombuffer(buf, np.uint8).reshape(LENS, LENS, 3)


p0 = subprocess.Popen(lens_cmd(0), stdout=subprocess.PIPE, bufsize=LENS * LENS * 3 * 2)
p1 = subprocess.Popen(lens_cmd(1), stdout=subprocess.PIPE, bufsize=LENS * LENS * 3 * 2)
enc = base + ["-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", f"{a.fps}", "-i", "-",
              "-ss", f"{a.tin}", "-t", f"{DUR}", "-i", a.src, "-map", "0:v", "-map", "1:a:0?",
              "-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf), "-pix_fmt", "yuv420p",
              "-c:a", "aac", "-b:a", "192k", "-shortest", a.out]
pe = subprocess.Popen(enc, stdin=subprocess.PIPE)

dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
S = 2
prev_flow = None
GX, GY = xs - 0.5, ys - 0.5
track = json.load(open(a.track)) if a.track else None
rtrack = json.load(open(a.roll_track)) if a.roll_track else None


def norm_grey(img):
    g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)
    m = cv2.GaussianBlur(g, (0, 0), 12)
    s = np.sqrt(cv2.GaussianBlur((g - m) ** 2, (0, 0), 12)) + 6
    return np.clip((g - m) / s * 40 + 128, 0, 255).astype(np.uint8)


t_start = time.time(); count = 0
for i, (L0, L1) in enumerate(zip(frames_of(p0), frames_of(p1))):
    t = i / a.fps
    yaw, pitch = interp(track, t) if track else (a.yaw, a.pitch)
    roll = interp(rtrack, t)[0] if rtrack else a.roll
    th0, m0, m1 = maps(yaw, pitch, roll)
    A0 = cv2.remap(L0, m0[0], m0[1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    A1 = cv2.remap(L1, m1[0], m1[1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    deg = np.degrees(th0)
    out = np.where((deg < 90)[..., None], A0, A1)
    if not a.seam_only:
        lo, hi = 90 - a.band, 90 + a.band
        tt_full = np.clip((deg - lo) / (hi - lo), 0, 1)
        band = (tt_full > 0) & (tt_full < 1)
        if band.sum() > 600:
            ys_, xs_ = np.where(band)
            y0_, y1_ = max(ys_.min() - 8, 0), min(ys_.max() + 9, H)
            x0_, x1_ = max(xs_.min() - 8, 0), min(xs_.max() + 9, W)
            c0 = np.ascontiguousarray(A0[y0_:y1_, x0_:x1_]); c1 = np.ascontiguousarray(A1[y0_:y1_, x0_:x1_])
            sm0 = cv2.resize(norm_grey(c0), None, fx=1 / S, fy=1 / S, interpolation=cv2.INTER_AREA)
            sm1 = cv2.resize(norm_grey(c1), None, fx=1 / S, fy=1 / S, interpolation=cv2.INTER_AREA)
            f = dis.calc(sm0, sm1, None)
            f = cv2.resize(f, (c0.shape[1], c0.shape[0]), interpolation=cv2.INTER_LINEAR) * S
            f = cv2.GaussianBlur(f, (0, 0), 9)
            if a.flow_smooth > 0 and prev_flow is not None and prev_flow.shape == f.shape:
                f = a.flow_smooth * prev_flow + (1 - a.flow_smooth) * f
            prev_flow = f
            tt = tt_full[y0_:y1_, x0_:x1_]
            gx, gy = GX[y0_:y1_, x0_:x1_], GY[y0_:y1_, x0_:x1_]
            F = lambda m: np.ascontiguousarray(m, dtype=np.float32)
            w0 = cv2.remap(c0, F(gx - tt * f[..., 0] - x0_), F(gy - tt * f[..., 1] - y0_), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            w1 = cv2.remap(c1, F(gx + (1 - tt) * f[..., 0] - x0_), F(gy + (1 - tt) * f[..., 1] - y0_), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            mix = ((1 - tt)[..., None] * w0 + tt[..., None] * w1).astype(np.uint8)
            bm = band[y0_:y1_, x0_:x1_][..., None]
            out[y0_:y1_, x0_:x1_] = np.where(bm, mix, out[y0_:y1_, x0_:x1_])
        else:
            prev_flow = None
    pe.stdin.write(np.ascontiguousarray(out).tobytes())
    count += 1
pe.stdin.close(); pe.wait()
for p in (p0, p1): p.stdout.close(); p.wait()
el = time.time() - t_start
print(f"{count} frames, {count / a.fps:.1f} s of footage in {el:.1f} s ({el / max(count / a.fps, 1e-6):.1f} s per second of footage)")
