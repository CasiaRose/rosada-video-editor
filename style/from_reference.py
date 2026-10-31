#!/usr/bin/env python3
"""Draft a style profile by measuring a reference reel the creator supplies.

  python style/from_reference.py reference.mp4 style.yaml

The measurement is a draft: cut rate, a sampled accent color, and where
high-contrast rows sit vertically (a stand-in for caption or title placement).
It does not copy frames, audio, or on-screen wording from the reference.
"""
import argparse, json, os, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from style.profile import dump_yaml, profile_from_measurements

def _run(args):
    return subprocess.run(args, capture_output=True)

def measure_reference(path, samples=8):
    """Return cuts_per_minute, accent hex, caption_y_ratio, mean_shot_s."""
    probe = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path])
    duration = float(probe.stdout.decode().strip() or "0")
    if duration <= 0:
        raise RuntimeError(f"could not read duration of {path}")
    raw = _run(["ffmpeg", "-v", "error", "-i", path, "-vf", "fps=4,scale=96:170,format=gray", "-f", "rawvideo", "-"]).stdout
    frame = 96 * 170
    count = len(raw) // frame
    if count < 2:
        raise RuntimeError("reference is too short to measure")
    gray = np.frombuffer(raw, np.uint8)[:count * frame].reshape(count, 170, 96).astype(np.float32)
    diff = np.abs(np.diff(gray, axis=0)).mean(axis=(1, 2))
    cuts = int(np.sum(diff > 18))
    # a cut every few sampled frames; samples are 4 fps
    cuts_per_minute = cuts / duration * 60.0
    shot_count = max(1, cuts + 1)
    color = _run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps=1/{max(duration / samples, 0.25):.3f},scale=32:32", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]).stdout
    pix = 32 * 32 * 3
    n = len(color) // pix
    rgb = np.frombuffer(color, np.uint8)[:n * pix].reshape(n, 32, 32, 3).astype(np.float32)
    # ignore the outer rim; sample the middle so a border does not dominate
    mid = rgb[:, 8:24, 8:24].mean(axis=(0, 1, 2))
    accent = "#{:02X}{:02X}{:02X}".format(int(mid[0]), int(mid[1]), int(mid[2]))
    row_energy = gray.mean(axis=(0, 2))
    # high row-to-row change often marks a type band
    row_delta = np.abs(np.diff(gray.mean(axis=0), axis=0)).mean(axis=1)
    y = int(np.argmax(row_delta))
    return {
        "cuts_per_minute": round(cuts_per_minute, 2),
        "mean_shot_s": round(duration / shot_count, 2),
        "accent": accent,
        "caption_y_ratio": round(y / max(1, row_energy.shape[0]), 3),
        "duration_s": round(duration, 2),
    }

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("reference")
    ap.add_argument("out")
    ap.add_argument("--measurements")
    args = ap.parse_args(argv)
    measured = json.load(open(args.measurements, encoding="utf-8")) if args.measurements else measure_reference(args.reference)
    profile = profile_from_measurements(measured)
    if args.out.endswith((".yaml", ".yml")):
        open(args.out, "w", encoding="utf-8").write(dump_yaml(profile))
    else:
        json.dump(profile, open(args.out, "w", encoding="utf-8"), indent=2)
        open(args.out, "a", encoding="utf-8").write("\n")
    print(json.dumps({"measurements": measured, "name": profile["name"], "out": args.out}, indent=2))

if __name__ == "__main__":
    main()
