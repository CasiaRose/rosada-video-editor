"""Kinetic hook type on a 1080x1920 still.

Two lines, mixed size, with a stroke and a soft scrim. Where the block sits
comes from the style profile (top, middle, or lower third). Pass bounds=(top, bottom)
when a profile limits the type to a vertical band.

Fonts: VEDIT_FONT_TEXT and VEDIT_FONT_DISPLAY, else DejaVu Sans Bold.
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
INK = (18, 6, 13)
WHITE = (255, 255, 255)
BLUSH = (244, 182, 194)
DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def _font(env, size):
    path = os.environ.get(env) or DEJAVU
    if not os.path.exists(path):
        path = DEJAVU
    return ImageFont.truetype(path, int(size))

def draw_hook(im, line1, line2, y0=220, scale=1.0, kind=None, bounds=None):
    """Return (RGB image, text bbox). bounds is an optional (top, bottom) limit."""
    im = im.convert("RGBA")
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS)
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    f1 = _font("VEDIT_FONT_TEXT", int(64 * scale))
    s2 = int(120 * scale)
    while True:
        f2 = _font("VEDIT_FONT_DISPLAY", s2)
        bb = d.textbbox((0, 0), line2, font=f2, stroke_width=6)
        if bb[2] - bb[0] <= 900 or s2 <= 72:
            break
        s2 -= 4
    lines2 = [line2]
    if s2 < 96 and " " in line2:
        words = line2.split()
        k = max(1, len(words) // 2)
        lines2 = [" ".join(words[:k]), " ".join(words[k:])]
        s2 = int(108 * scale)
        f2 = _font("VEDIT_FONT_DISPLAY", s2)
        while max(d.textbbox((0, 0), x, font=f2, stroke_width=6)[2] for x in lines2) > 900 and s2 > 64:
            s2 -= 4
            f2 = _font("VEDIT_FONT_DISPLAY", s2)
    hgt = 80 + len(lines2) * int(s2 * 1.02)
    scrim = Image.new("L", im.size, 0)
    ImageDraw.Draw(scrim).rounded_rectangle((80, y0 - 24, 1000, y0 + hgt), 48, fill=90)
    scrim = scrim.filter(ImageFilter.GaussianBlur(28))
    ink = Image.new("RGBA", im.size, INK + (255,))
    ink.putalpha(scrim)
    im.alpha_composite(ink)
    d.text((540, y0), line1, font=f1, fill=WHITE, anchor="mt", stroke_width=4, stroke_fill=INK)
    y = y0 + int(78 * scale)
    for line in lines2:
        d.text((540, y), line, font=f2, fill=BLUSH, anchor="mt", stroke_width=6, stroke_fill=INK)
        y += int(s2 * 1.02)
    im.alpha_composite(lay)
    box = (80, y0 - 24, 1000, y)
    if box[1] < 0 or box[3] > H:
        raise ValueError(f"type {box} leaves the frame")
    if bounds is not None:
        top, bottom = bounds
        if box[1] < top or box[3] > bottom:
            raise ValueError(f"type {box} is outside y {top}-{bottom}")
    return im.convert("RGB"), box
