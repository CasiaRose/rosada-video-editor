"""Runtime progress border: accent #3D5A80 -> #E07A5F stroke that travels clockwise around the frame, one step per video frame
(fill = (n+1)/N, so it closes exactly on the last frame). Spec (inset 10, stroke 6, radius 26, start top edge after TL corner, clockwise,
progress (n+1)/N, gradient by absolute path position, glow ~sigma 6.4 / gain 0.55, Paper 10% track, Paper dot r7 + Coral glow)."""
import numpy as np
import json, os
W, H = 1080, 1920
N = int(os.environ.get("PB_N", 1800))   # set by border.py from the video frame count
PRI = np.array([61, 90, 128.]); COR = np.array([224, 122, 95.]); PAP = np.array([247, 247, 245.])
C = 12.35; R = 26.0; SW = 6.0; BAND = 44
x0, y0, x1, y1 = C, C, W - 1 - C, H - 1 - C
segs = []  # (kind, params, length)
def _build():
    L = 0; out = []
    out.append(("L", (x0 + R, y0, x1 - R, y0))); out.append(("A", (x1 - R, y0 + R, -np.pi / 2, 0)))
    out.append(("L", (x1, y0 + R, x1, y1 - R))); out.append(("A", (x1 - R, y1 - R, 0, np.pi / 2)))
    out.append(("L", (x1 - R, y1, x0 + R, y1))); out.append(("A", (x0 + R, y1 - R, np.pi / 2, np.pi)))
    out.append(("L", (x0, y1 - R, x0, y0 + R))); out.append(("A", (x0 + R, y0 + R, np.pi, 1.5 * np.pi)))
    res = []
    for k, p in out:
        l = np.hypot(p[2] - p[0], p[3] - p[1]) if k == "L" else R * (p[3] - p[2])
        res.append((k, p, L, l)); L += l
    return res, L
SEGS, LEN = _build()
yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
inband = (xx < BAND) | (xx > W - 1 - BAND) | (yy < BAND) | (yy > H - 1 - BAND)
PY, PX = yy[inband], xx[inband]
best_d = np.full(PX.shape, 1e9); best_s = np.zeros(PX.shape)
for k, p, s0, l in SEGS:
    if k == "L":
        ax, ay, bx, by = p; vx, vy = bx - ax, by - ay
        t = np.clip(((PX - ax) * vx + (PY - ay) * vy) / (l * l), 0, 1)
        d = np.hypot(PX - (ax + t * vx), PY - (ay + t * vy)); s = s0 + t * l
    else:
        cx, cy, a0, a1 = p; ang = np.arctan2(PY - cy, PX - cx)
        ang = np.where(ang < a0 - 1e-9, ang + 2 * np.pi, ang); ang = np.where(ang > a1 + np.pi, ang - 2 * np.pi, ang)
        ta = np.clip(ang, a0, a1); d = np.hypot(PX - (cx + R * np.cos(ta)), PY - (cy + R * np.sin(ta))); s = s0 + (ta - a0) * R
    m = d < best_d; best_d[m] = d[m]; best_s[m] = s[m]
DIST, ARC = best_d, best_s
def head_xy(sh):
    for k, p, s0, l in SEGS:
        if s0 <= sh <= s0 + l + 1e-6:
            t = (sh - s0) / l
            if k == "L": return p[0] + t * (p[2] - p[0]), p[1] + t * (p[3] - p[1])
            a = p[2] + t * (p[3] - p[2]); return p[0] + R * np.cos(a), p[1] + R * np.sin(a)
    return x0 + R, y0
GLOW_G, GLOW_S, TRACK_A = 0.55, 6.4, 0.10
DOT_R, DOT_GLOW_G, DOT_GLOW_S, DOT_BACK = 7.0, 0.38, 4.0, 1.5
def apply(img, n):
    """composite the border for output frame n onto img (H,W,3 uint8 RGB)."""
    out = img.astype(np.float64); sub = out[inband]
    sh = min(1.0, (n + 1) / N) * LEN
    stroke = np.clip(SW / 2 + 0.5 - DIST, 0, 1)
    filled = np.clip(sh - ARC + 0.5, 0, 1)
    col = PRI[None] + (COR - PRI)[None] * (ARC / LEN)[:, None]
    # track
    a = TRACK_A * stroke * (1 - filled); sub = sub * (1 - a[:, None]) + PAP[None] * a[:, None]
    # glow (fades in behind the head over the last ~10 px)
    ga = GLOW_G * np.exp(-np.maximum(DIST - 0.0, 0) ** 2 / (2 * GLOW_S ** 2)) * np.clip((sh - ARC) / 10 + 0.5, 0, 1)
    ga = np.maximum(ga - stroke * filled, 0); sub = sub * (1 - ga[:, None]) + col * ga[:, None]
    a = stroke * filled; sub = sub * (1 - a[:, None]) + col * a[:, None]
    # dot at the head
    hx, hy = head_xy(max(0, sh - DOT_BACK)); dd = np.hypot(PX - hx, PY - hy)
    dg = DOT_GLOW_G * np.exp(-np.maximum(dd - DOT_R, 0) ** 2 / (2 * DOT_GLOW_S ** 2)) * (dd > DOT_R - 1)
    sub = sub * (1 - dg[:, None]) + COR[None] * dg[:, None]
    a = np.clip(DOT_R + 0.5 - dd, 0, 1); sub = sub * (1 - a[:, None]) + PAP[None] * a[:, None]
    out[inband] = sub
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)

