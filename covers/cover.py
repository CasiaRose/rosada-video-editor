#!/usr/bin/env python3
"""Cover still from a frame and two lines of type. No burned-in captions.

Placement comes from --y0. A style profile's cover.layout decides whether to
also write a center crop (--crop-top and --crop-bottom). --text-top and
--text-bottom reject type that leaves that band. The photo is not flipped.

  python covers/cover.py frame.jpg out/cover --line1 "Small line" --line2 "THE BIG LINE" --y0 240
"""
import argparse, os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "graphics"))
from hooks import draw_hook

GRID_TOP, GRID_BOTTOM = 240, 1680

def shift_down(rgb, dy):
    """Move the photo down by dy px. The gap is the blurred mean of the top rows, feathered in."""
    import cv2
    s = rgb.astype(np.float32)
    row = cv2.GaussianBlur(s[:80].mean(0)[None], (0, 0), sigmaX=60)[0]
    out = np.empty_like(s)
    out[:dy] = row[None]
    out[dy:] = s[:1920 - dy]
    feather = 160
    w = np.linspace(0, 1, feather)[:, None, None] ** 1.5
    out[dy:dy + feather] = row[None] * (1 - w) + s[:feather] * w
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)

def build(image, line1, line2, y0=420, scale=1.0, shift=0, bounds=None):
    im = image.convert("RGB").resize((1080, 1920), Image.LANCZOS)
    if shift:
        im = Image.fromarray(shift_down(np.asarray(im), int(shift)))
    framed, box = draw_hook(im, line1, line2, y0=y0, scale=scale, bounds=bounds)
    return framed, box

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("frame")
    ap.add_argument("prefix")
    ap.add_argument("--line1", required=True)
    ap.add_argument("--line2", required=True)
    ap.add_argument("--y0", type=int, default=240)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--shift", type=int, default=0)
    ap.add_argument("--text-top", type=int)
    ap.add_argument("--text-bottom", type=int)
    ap.add_argument("--crop-top", type=int)
    ap.add_argument("--crop-bottom", type=int)
    a = ap.parse_args(argv)
    bounds = (a.text_top, a.text_bottom) if a.text_top is not None and a.text_bottom is not None else None
    framed, box = build(Image.open(a.frame), a.line1, a.line2, y0=a.y0, scale=a.scale, shift=a.shift, bounds=bounds)
    os.makedirs(os.path.dirname(os.path.abspath(a.prefix)) or ".", exist_ok=True)
    framed.save(a.prefix + ".jpg", quality=95)
    if a.crop_top is not None and a.crop_bottom is not None:
        framed.crop((0, a.crop_top, 1080, a.crop_bottom)).save(a.prefix + "_crop.jpg", quality=95)
    print("cover", a.prefix, "bbox", box)

def _self_test():
    grad = np.zeros((1920, 1080, 3), np.uint8)
    grad[:, :, 0] = np.linspace(20, 180, 1920)[:, None]
    grad[:, :, 1] = 90
    grad[:, :, 2] = 110
    # asymmetric so a mirror would be obvious, and bright on the left only
    grad[:, :200, :] = (240, 240, 240)
    framed, box = build(Image.fromarray(grad), "A short line", "BIG LINE", y0=1100, shift=120)
    assert box[1] > 900, box
    arr = np.asarray(framed)
    assert arr.shape == (1920, 1080, 3)
    assert arr[200, 20].mean() > 200
    assert arr[200, 600].mean() < 160
    try:
        build(Image.fromarray(grad), "too low", "TOO LOW", y0=1100, bounds=(200, 600))
    except ValueError:
        pass
    else:
        raise SystemExit("cover: bounds were ignored")
    print("cover self-test ok", box)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        _self_test()
    else:
        main()
