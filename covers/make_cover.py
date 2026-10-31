#!/usr/bin/env python3
"""Series cover. Profile grids crop 1080x1920 to y 240-1680, so every text pixel must sit inside y 300-1000.
The series badge is always at x=90, y=312. No burned-in captions. The still is never mirrored.
  python make_cover.py hero.png "Meet Alex · builder" cover_a --shift 100 --lines "The lesson|in *one line*"
Lines are separated by '|'; wrap a phrase in *...* to colour it Primary. --shift moves the still down (px).
--blur x0,y0,x1,y1 (repeatable) softens lettering that peeks out. Check the _safezones and _crop3x4 previews."""
import argparse, os, re, sys
from PIL import Image, ImageDraw, ImageFilter
from covers_thumbkit import compose, headline_panel, chip, previews, font, INK, PRIMARY, KICK
BADGE = os.environ.get("COVER_BADGE", "")
ap = argparse.ArgumentParser(); ap.add_argument("hero"); ap.add_argument("chip"); ap.add_argument("name")
ap.add_argument("--lines", required=True); ap.add_argument("--shift", type=int, default=100); ap.add_argument("--scale", type=float, default=1.0)
ap.add_argument("--size", type=int, default=72); ap.add_argument("--top", type=int, default=380); ap.add_argument("--panel_w", type=int, default=1011)
ap.add_argument("--blur", action="append", default=[])
a = ap.parse_args()
im = Image.open(a.hero).convert("RGB").resize((1080, 1920), Image.LANCZOS)
for b in a.blur:
    box = tuple(int(v) for v in b.split(",")); im.paste(im.crop(box).filter(ImageFilter.GaussianBlur(22)), box[:2])
lines = [[(seg.strip("*"), PRIMARY if seg.startswith("*") else INK) for seg in re.split(r"(\*[^*]+\*)", ln) if seg] for ln in a.lines.split("|")]
B = compose(im, a.scale, (540, 960), (540, 960 + a.shift))
B, box = headline_panel(B, lines, top=a.top, size=a.size, kicker=KICK, panel_w=a.panel_w)
d = ImageDraw.Draw(B)
if BADGE:
    d.text((90, 312), BADGE, font=font(34, 700), fill=PRIMARY)
chip_cy = box[3] + 70
B = chip(B, a.chip, 540, chip_cy); previews(B, a.name); print(a.name, "panel", box)
