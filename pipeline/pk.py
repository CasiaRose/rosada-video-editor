"""panelkit (approved house look): Ink header strip, Paper body, rounded 26,
soft drop shadow, Primary/Coral accents, no purple. All drawing in PIL RGBA at 1x (2x supersampled shapes)."""
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
INK = (28, 28, 28); PAPER = (247, 247, 245); PRI = (61, 90, 128); COR = (224, 122, 95)
TILE = (244, 241, 242); TILE_BD = (230, 225, 227); TXT = (40, 32, 36); MUTED = (128, 118, 123); EYEBROW = (247, 186, 170)
PRI_TINT = (252, 238, 243); COR_TINT = (255, 241, 236); TRACK = (231, 226, 228); GREY_BAR = (90, 85, 87); PINK = (232, 110, 150)
import os
FD = os.environ.get("PK_FONT_DIR", "/usr/share/fonts/truetype/dejavu/")   # approved panels used DejaVu Sans Bold; see SKILL.md re Inter
_fc = {}
def font(sz, bold=True, mono=False, italic=False):
    k = (sz, bold, mono, italic)
    if k not in _fc:
        nm = "DejaVuSansMono" + ("-Bold" if bold else "") if mono else "DejaVuSans" + ("-Bold" if bold else "") + ("Oblique" if italic and bold else ("-Oblique" if italic else ""))
        _fc[k] = ImageFont.truetype(FD + nm + ".ttf", sz)
    return _fc[k]
def rrect(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)
def rr_img(w, h, r, fill, outline=None, width=0, ss=3):
    im = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), r * ss, fill=fill, outline=outline, width=width * ss)
    return im.resize((w, h), Image.LANCZOS)
def paste(base, im, x, y): base.alpha_composite(im, (int(x), int(y)))
def text(d, xy, s, sz, col, bold=True, anchor="la", mono=False, italic=False):
    d.text(xy, s, font=font(sz, bold, mono, italic), fill=col, anchor=anchor)
def tw(s, sz, bold=True, mono=False): return font(sz, bold, mono).getlength(s)
def spaced(d, xy, s, sz, col, sp=1.6):
    x, y = xy
    for ch in s: d.text((x, y), ch, font=font(sz), fill=col); x += font(sz).getlength(ch) + sp
def pill(s, sz, bg, fg, padx=16, h=None):
    h = h or int(sz * 1.9); w = int(tw(s, sz) + 2 * padx)
    im = rr_img(w, h, h // 2, bg); d = ImageDraw.Draw(im); d.text((w / 2, h / 2 + 1), s, font=font(sz), fill=fg, anchor="mm"); return im
def panel(w, h, eyebrow, title, badge=None, badge_bg=PRI, header=104, r=26):
    """returns (RGBA image, body_top)"""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    body = rr_img(w, h, r, PAPER + (255,)); im.alpha_composite(body)
    hd = rr_img(w, header + r, r, INK + (255,)); hd = hd.crop((0, 0, w, header)); im.alpha_composite(hd)
    d = ImageDraw.Draw(im)
    spaced(d, (34, 22), eyebrow.upper(), 21, EYEBROW, 1.2)
    text(d, (34, 50), title, 37, (255, 255, 255))
    if badge:
        p = pill(badge, 22, badge_bg, (255, 255, 255), padx=16, h=44); im.alpha_composite(p, (w - p.width - 30, (header - 44) // 2))
    return im, header
def tile(w, h, fill=TILE, bd=TILE_BD, bw=2, r=16):
    return rr_img(w, h, r, fill + (255,), bd + (255,), bw)
def ease(t): t = min(max(t, 0), 1); return t * t * (3 - 2 * t)
def ease_out(t): t = min(max(t, 0), 1); return 1 - (1 - t) ** 3
def back_out(t, s=1.4):
    t = min(max(t, 0), 1) - 1; return 1 + (s + 1) * t ** 3 + s * t ** 2
def check_icon(sz, on):
    im = Image.new("RGBA", (sz, sz), (0, 0, 0, 0)); ss = 3; big = Image.new("RGBA", (sz * ss, sz * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(big)
    if on:
        d.ellipse((0, 0, sz * ss - 1, sz * ss - 1), fill=PRI)
        d.line([(sz * ss * .27, sz * ss * .52), (sz * ss * .44, sz * ss * .68), (sz * ss * .74, sz * ss * .34)], fill=(255, 255, 255), width=int(sz * ss * .11), joint="curve")
    else:
        d.ellipse((2 * ss, 2 * ss, sz * ss - 1 - 2 * ss, sz * ss - 1 - 2 * ss), outline=(200, 192, 196), width=3 * ss)
    return big.resize((sz, sz), Image.LANCZOS)
# ---------- compositing helpers (numpy float RGB frames) ----------
def shadow_of(alpha, blur=16, off=8, a=0.32):
    sh = cv2.GaussianBlur(alpha, (0, 0), blur); M = np.float32([[1, 0, 0], [0, 1, off]])
    return cv2.warpAffine(sh, M, (alpha.shape[1], alpha.shape[0])) * a
def place(frame, rgba, cx, cy, scale=1.0, alpha=1.0, shadow=True, sweep=None):
    """composite PIL RGBA centred at (cx,cy) with scale/alpha onto float32 frame (H,W,3). sweep: 0..1 light band position or None."""
    a = np.asarray(rgba, np.float32)
    if abs(scale - 1) > 1e-3:
        a = cv2.resize(a, (max(1, int(round(a.shape[1] * scale))), max(1, int(round(a.shape[0] * scale)))), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
    h, w = a.shape[:2]; pad = 40
    x0 = int(round(cx - w / 2)); y0 = int(round(cy - h / 2))
    H, W = frame.shape[:2]
    rgb = a[..., :3]; al = a[..., 3:4] / 255 * alpha
    if sweep is not None and 0 <= sweep <= 1:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); pos = (xx + 0.45 * yy) - (sweep * (w + 0.45 * h + 320) - 160)
        band = (np.exp(-(pos / 70) ** 2) * 0.30)[..., None]; rgb = rgb + (255 - rgb) * band
    # shadow
    if shadow:
        big = np.zeros((h + 2 * pad, w + 2 * pad), np.float32); big[pad:pad + h, pad:pad + w] = al[..., 0]
        sh = shadow_of(big)[..., None]
        _blend(frame, np.zeros((h + 2 * pad, w + 2 * pad, 3), np.float32), sh, x0 - pad, y0 - pad)
    _blend(frame, rgb, al, x0, y0)
    return frame
def _blend(frame, rgb, al, x0, y0):
    H, W = frame.shape[:2]; h, w = rgb.shape[:2]
    fx0, fy0 = max(0, x0), max(0, y0); fx1, fy1 = min(W, x0 + w), min(H, y0 + h)
    if fx1 <= fx0 or fy1 <= fy0: return
    sx0, sy0 = fx0 - x0, fy0 - y0
    sub = frame[fy0:fy1, fx0:fx1]; A = al[sy0:sy0 + fy1 - fy0, sx0:sx0 + fx1 - fx0]
    sub *= (1 - A); sub += rgb[sy0:sy0 + fy1 - fy0, sx0:sx0 + fx1 - fx0] * A
def backdrop():
    """blurred brand-green backdrop + faint 60 px grid for full-frame panels."""
    H, W = 1920, 1080; yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    base = np.array([8, 27, 25.]) + (np.array([24, 40, 36.]) - np.array([8, 27, 25.])) * (np.clip(1 - yy / 1500, 0, 1) ** 1.6)[..., None]
    glow = np.exp(-(((xx - 540) / 520) ** 2 + ((yy - 230) / 330) ** 2))[..., None] * np.array([26, 22, 8.])
    img = base + glow
    rng = np.random.default_rng(3); n = cv2.GaussianBlur(rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32), (0, 0), 0.8)
    img += cv2.resize(n, (W, H))[..., None] * 3.2
    g = np.zeros((H, W), np.float32); g[:, 30::60] = 1; g[30::60, :] = 1; g = cv2.GaussianBlur(g, (0, 0), 0.6)
    img += g[..., None] * np.array([10, 16, 15.])
    return np.clip(img, 0, 255).astype(np.float32)

def draw_callout(l, s):
    """Terminal type-on callout, l = frames since it appeared. 3 frames of empty box, then the whole string types in over 18 frames,
    block cursor blinks every 8 frames once typing is done. First char ('>') in Primary, rest in near-white mono. Dark box, Primary-tinted rim."""
    nch = len(s); n = min(nch, max(0, int((l - 3) * nch / 18) + 1)) if l >= 3 else 0
    cur = (l // 8) % 2 == 0 or n < nch
    fz = 36; w = int(tw(s + " \u2588", fz, mono=True) + 52); h = 88
    im = Image.new("RGBA", (w + 4, h + 4), (0, 0, 0, 0))
    im.alpha_composite(rr_img(w + 4, h + 4, 15, (190, 49, 90, 115))); im.alpha_composite(rr_img(w, h, 13, (24, 21, 29, 240)), (2, 2))
    d = ImageDraw.Draw(im); x = 28; vis = s[:n]
    if vis:
        text(d, (x, 2 + h / 2), vis[0], fz, PRI, mono=True, anchor="lm"); x += tw(vis[0], fz, mono=True)
        text(d, (x, 2 + h / 2), vis[1:], fz, (246, 242, 244), mono=True, bold=False, anchor="lm"); x += tw(vis[1:], fz, mono=True, bold=False)
    if cur: d.rectangle((x + 8, 2 + h / 2 - 20, x + 26, 2 + h / 2 + 20), fill=(246, 242, 244))
    return im
def callout_keys(f0, s):
    """SFX cue frames for the type-on: a soft key tick every 3 characters at -34 dB."""
    return [(f0 + 3 + int(k * 18 / len(s)), "key", -34) for k in range(0, len(s), 3)]
CALLOUT_ALPHA_IN = {0: .155, 1: .5, 2: .85}; CALLOUT_ALPHA_OUT = {3: .89, 2: .64, 1: .45, 0: .11}
