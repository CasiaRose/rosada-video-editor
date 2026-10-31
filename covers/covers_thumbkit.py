#!/usr/bin/env python3
"""Series cover layout: hero still, paper headline panel, series badge, chip.
Cover type must sit inside y 300-1000. Previews include the y 240-1680 grid crop
and a safe-zone overlay (top 150 px, bottom 350 px).
Env: COVER_OUT (default ./covers), INTER_FONT or INTER_FONT_DIR, COVER_KICKER, COVER_BADGE."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
OUT = Path(os.environ.get("COVER_OUT", "covers")); OUT.mkdir(parents=True, exist_ok=True)

def hexrgb(h): return tuple(int(h[i:i+2], 16) for i in (1, 3, 5))
INK, PRIMARY, CORAL, PAPER = map(hexrgb, ["#1C1C1C", "#3D5A80", "#E07A5F", "#F7F7F5"])
W, H = 1080, 1920
KICK = os.environ.get("COVER_KICKER", "")
S = OUT / "src"

def _inter_file(wght):
    """Variable font via INTER_FONT, else a static Inter TTF. INTER_FONT_DIR overrides the search."""
    env = os.environ.get("INTER_FONT", "")
    if env and os.path.exists(env):
        return env, True
    names = ["Inter-Black.ttf", "Inter-ExtraBold.ttf", "Inter-Bold.ttf"] if wght >= 850 else ["Inter-Bold.ttf", "Inter-SemiBold.ttf"]
    roots = [os.environ.get("INTER_FONT_DIR", ""), "/usr/share/fonts/truetype/inter", "/usr/share/fonts/truetype/macos", "/usr/share/fonts/inter"]
    for root in roots:
        if not root or not os.path.isdir(root): continue
        for name in names:
            path = os.path.join(root, name)
            if os.path.exists(path): return path, False
    raise SystemExit("Inter was not found. Set INTER_FONT to a .ttf, or INTER_FONT_DIR to the folder that holds it.")

def font(size, wght):
    path, variable = _inter_file(wght)
    f = ImageFont.truetype(path, size)
    if variable:
        try: f.set_variation_by_axes([32, wght])
        except Exception: pass
    return f

def load(name, fn):
    p = S / name
    return Image.open(p).convert("RGB") if p.exists() else fn(p)

def hist_match(src, ref, src_box, ref_box):
    """per-channel CDF match of src to ref (LUT fitted on the boxes, applied to the whole src)"""
    a = np.asarray(src); b = np.asarray(ref); out = np.empty_like(a)
    ra = a[src_box[1]:src_box[3], src_box[0]:src_box[2]]; rb = b[ref_box[1]:ref_box[3], ref_box[0]:ref_box[2]]
    for c in range(3):
        ca = np.cumsum(np.bincount(ra[..., c].ravel(), minlength=256)).astype(float); ca /= ca[-1]
        cb = np.cumsum(np.bincount(rb[..., c].ravel(), minlength=256)).astype(float); cb /= cb[-1]
        lut = np.interp(ca, cb, np.arange(256)); out[..., c] = np.clip(lut[a[..., c]] + 0.5, 0, 255).astype(np.uint8)
    return Image.fromarray(out)

def _ramps(size, x0, y0, fe):
    w, h = size; xs = np.arange(w)[None, :].astype(float); ys = np.arange(h)[:, None].astype(float); r = np.ones((h, w))
    if x0 > 0: r = np.minimum(r, np.clip(xs / fe, 0, 1))
    if y0 > 0: r = np.minimum(r, np.clip(ys / fe, 0, 1))
    if x0 + w < W: r = np.minimum(r, np.clip((w - 1 - xs) / fe, 0, 1))
    if y0 + h < H: r = np.minimum(r, np.clip((h - 1 - ys) / fe, 0, 1))
    return Image.fromarray((r * 255).astype("uint8"), "L")

def compose(im, s, src_xy, dst_xy, inset=0, feather=60, dim=0.55):
    """scale frame by s, put src_xy at dst_xy; uncovered area = blurred, darkened cover of the same frame (feathered join)"""
    im = im.crop((inset, inset, W - inset, H - inset)); sx, sy = src_xy[0] - inset, src_xy[1] - inset; cw, ch = im.size
    bs = max(W / cw, H / ch) * 1.1
    bg = im.resize((round(cw * bs), round(ch * bs)), Image.LANCZOS)
    bg = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H))
    bg = Image.blend(bg.filter(ImageFilter.GaussianBlur(40)), Image.new("RGB", (W, H), INK), 1 - dim)
    fg = im.resize((round(cw * s), round(ch * s)), Image.LANCZOS)
    x0, y0 = round(dst_xy[0] - sx * s), round(dst_xy[1] - sy * s)
    out = bg.copy(); out.paste(fg, (x0, y0), _ramps(fg.size, x0, y0, feather)); return out

def card(base_im, src, box, s, center, radius=30):
    """lift a rounded card (box in frame px) out of src, scale it, drop it on base_im with a soft shadow"""
    c = src.crop(box); c = c.resize((round(c.width * s), round(c.height * s)), Image.LANCZOS)
    m = Image.new("L", c.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, c.width - 1, c.height - 1], radius, fill=255)
    x0, y0 = round(center[0] - c.width / 2), round(center[1] - c.height / 2)
    base = base_im.convert("RGBA"); sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x0 + 4, y0 + 16, x0 + c.width + 4, y0 + c.height + 16], radius, fill=(0, 0, 0, 150))
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(22))); base.paste(c, (x0, y0), m)
    return base.convert("RGB"), (x0, y0, x0 + c.width, y0 + c.height)

def panel_bg(src):
    """the generated panels' own dark-green backdrop (band above the card, inside the border), stretched + blurred"""
    return src.crop((40, 60, 1040, 400)).resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(24))

def headline_panel(im, lines, top, size=112, kicker=None, panel_w=None):
    f = font(size, 900); fk = font(34, 700); d0 = ImageDraw.Draw(im)
    lh = int(size * 1.12); padx, pady = 56, 44
    widths = [sum(d0.textlength(t, font=f) for t, _ in ln) for ln in lines]
    kh = 58 if kicker else 0
    pw = panel_w or int(max(widths + [d0.textlength(kicker or "", font=fk)]) + 2 * padx + 24)
    ph = int(pady * 2 + kh + lh * len(lines) - (lh - size) + 6)
    x0 = (W - pw) // 2; y0 = top
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x0 + 4, y0 + 14, x0 + pw + 4, y0 + ph + 14], 36, fill=(18, 6, 13, 120))
    base = im.convert("RGBA"); base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    pl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); pd = ImageDraw.Draw(pl)
    pd.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], 36, fill=PAPER + (255,))
    pd.rounded_rectangle([x0 + 26, y0 + pady + kh + 8, x0 + 36, y0 + ph - pady - 4], 5, fill=CORAL + (255,))
    base.alpha_composite(pl); d = ImageDraw.Draw(base); tx = x0 + padx + 14
    if kicker: d.text((tx, y0 + pady - 6), kicker, font=fk, fill=PRIMARY)
    y = y0 + pady + kh
    for ln in lines:
        x = tx
        for t, col in ln: d.text((x, y), t, font=f, fill=col); x += d.textlength(t, font=f)
        y += lh
    return base.convert("RGB"), (x0, y0, x0 + pw, y0 + ph)

def chip(im, text, cx, cy, fill=INK, fg=PAPER, dot=CORAL, size=40):
    f = font(size, 700); base = im.convert("RGBA"); d = ImageDraw.Draw(base)
    tw = d.textlength(text, font=f); pw, ph = int(tw + 110), size + 40; x0, y0 = int(cx - pw / 2), int(cy - ph / 2)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([x0, y0 + 8, x0 + pw, y0 + ph + 8], ph // 2, fill=(0, 0, 0, 110))
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12))); d = ImageDraw.Draw(base)
    d.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], ph // 2, fill=fill + (240,))
    d.ellipse([x0 + 30, cy - 11, x0 + 52, cy + 11], fill=dot); d.text((x0 + 72, cy), text, font=f, fill=fg, anchor="lm")
    return base.convert("RGB")

def previews(img, name):
    img.save(OUT / f"{name}.png"); img.save(OUT / f"{name}.jpg", quality=92)
    c = img.crop((0, 240, W, 1680)); c.save(OUT / f"{name}_crop3x4.jpg", quality=90)
    c.resize((270, 360), Image.LANCZOS).save(OUT / f"{name}_grid270.png")
    img.resize((270, 480), Image.LANCZOS).save(OUT / f"{name}_full270.png")
    g = img.convert("RGBA"); ov = Image.new("RGBA", g.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rectangle([0, 0, W, 150], fill=(255, 0, 0, 90)); od.rectangle([0, H - 350, W, H], fill=(255, 0, 0, 90))
    od.rectangle([0, 240, W - 1, 1680], outline=(0, 255, 0, 255), width=6)
    g.alpha_composite(ov); g.convert("RGB").resize((540, 960)).save(OUT / f"{name}_safezones.jpg", quality=85)

