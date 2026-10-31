"""Per-OUTPUT-frame punch-in anchor (eye line) from the blink scan + aroll_map. Also lists output blink frames so ZOOM steps can avoid them.
Writes facetrack.json {ax, ay, blinks_out}. Usage: python facetrack.py"""
import json, numpy as np
def gauss1d(a, sig):
    r = int(3 * sig); k = np.exp(-0.5 * (np.arange(-r, r + 1) / sig) ** 2); k /= k.sum()
    return np.convolve(np.pad(np.asarray(a, float), r, mode="edge"), k, mode="valid")
R = json.load(open("scratch/blinks_raw.json")); idx = json.load(open("aroll_map.json"))
cx = np.array([r.get("cx", np.nan) if r.get("blink") is not None else np.nan for r in R]); cy = np.array([r.get("cy", np.nan) if r.get("blink") is not None else np.nan for r in R])
ok = ~np.isnan(cx); n = np.arange(len(cx)); cx = np.interp(n, n[ok], cx[ok]); cy = np.interp(n, n[ok], cy[ok])
ax = gauss1d(cx[idx] * 1080, 6); ay = gauss1d(cy[idx] * 1920, 6) - 60          # anchor ~60 px above landmark centroid = eye line
G = json.load(open("scratch/blink_groups.json")); bo = sorted({o for o, r in enumerate(idx) for a, b in G if a <= r <= b})
json.dump(dict(ax=[round(v, 1) for v in ax], ay=[round(v, 1) for v in ay], blinks_out=bo), open("facetrack.json", "w"))
print("blink output frames:", bo)
