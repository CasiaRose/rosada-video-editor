#!/usr/bin/env python3
"""Make a B-roll clip SMOOTH before it goes in an edit (v3.1). HQ captures often have duplicated frames (a renderer drawing 8-12 new frames/s
inside a 30 fps file) or a variable frame rate (screen recordings) -> choppy, stuttering motion even with no added drift.
  python3 smooth_clip.py in.mp4 out.mp4 [--ss 0 --t 5] [--slow 1.3] [--crop W:H:X:Y]
Steps: measure -> drop duplicate frames -> re-time the kept frames so the camera moves at an even speed (time proportional to motion)
-> motion-interpolate to a constant 30 fps (minterpolate mci) -> 1080x1920. --slow 1.3 = 30% slower (gentler). Prints smoothness before/after.
  python3 smooth_clip.py --check clip.mp4   # just report: fps, duplicate-frame %, jerk (0 = perfectly even motion)
Rule: a clip is OK for an edit when dup <= 3 % and jerk <= 0.30 at 30 fps CFR. make_edit runs this automatically on every B-roll it uses."""
import sys, os, json, argparse, subprocess, tempfile, numpy as np
def run(*a): subprocess.run(list(map(str, a)), check=True)
def gray(f, ss=None, t=None, w=96):
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", str(ss)] if ss else []) + ["-i", f] + (["-t", str(t)] if t else []) + ["-vf", f"scale={w}:{w*16//9}", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    b = subprocess.run(cmd, capture_output=True).stdout; return np.frombuffer(b, np.uint8).reshape(-1, w * 16 // 9, w).astype(np.float32)
def stats(F):
    d = np.abs(np.diff(F, axis=0)).mean((1, 2)); mv = d[d > 0.05]
    if len(mv) < 3: return dict(frames=len(F), dup=0.0, jerk=0.0, motion=0.0, still=True)
    med = np.median(mv); dup = float((d < 0.15 * med).mean()); jerk = float(np.median(np.abs(np.diff(d))) / med)
    return dict(frames=len(F), dup=round(dup, 3), jerk=round(jerk, 2), motion=round(float(med), 2), still=False)
def probe(f):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate,avg_frame_rate", "-of", "json", f], capture_output=True, text=True).stdout)["streams"][0]
    ev = lambda s: eval(s) if s and s != "0/0" else 0
    return ev(j["r_frame_rate"]), ev(j["avg_frame_rate"])
def smooth(inp, out, ss=0, t=None, slow=1.0, crop=None, log=print):
    """dedupe -> even-speed retime -> minterpolate to constant 30 fps 1080x1920. Returns True if the result passes ok()."""
    tmp = tempfile.mkdtemp(prefix="smooth_")
    if t is None: t = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", inp], capture_output=True, text=True).stdout) - ss
    vf = (f"crop={crop}," if crop else "") + "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920"
    run("ffmpeg", "-v", "error", "-y", *(["-ss", str(ss)] if ss else []), "-i", inp, "-t", str(t), "-vf", vf, "-fps_mode", "passthrough", f"{tmp}/a_%05d.png")
    fs = sorted(f for f in os.listdir(tmp) if f.endswith(".png"))
    G = [np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", f"{tmp}/{f}", "-vf", "scale=96:170", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout, np.uint8).astype(np.float32) for f in fs]
    keep = [0]
    for i in range(1, len(G)):                                  # unique frames only: renderer duplicates / VFR stalls removed
        if np.abs(G[i] - G[keep[-1]]).mean() > 0.12: keep.append(i)
    D = t * slow
    if len(keep) < 3:                                           # a still: hold it (make_edit adds a gentle subpixel push)
        run("ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", f"{tmp}/{fs[0]}", "-t", f"{D:.3f}", "-r", "30", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", out); return True
    disp = np.array([np.abs(G[keep[i + 1]] - G[keep[i]]).mean() for i in range(len(keep) - 1)])
    T = np.concatenate([[0], np.cumsum(disp)]); T = T / T[-1] * D        # even camera speed: time proportional to motion
    with open(f"{tmp}/l.txt", "w") as fh:
        for i, k in enumerate(keep):
            fh.write(f"file '{tmp}/{fs[k]}'\nduration {(T[i + 1] - T[i]) if i + 1 < len(keep) else 1 / 30:.5f}\n")
        fh.write(f"file '{tmp}/{fs[keep[-1]]}'\n")
    run("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{tmp}/l.txt", "-vf",
        "minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=none,fps=30,format=yuv420p", "-t", f"{D:.3f}", "-r", "30", "-c:v", "libx264", "-crf", "16", "-an", out)
    s1 = stats(gray(out)); good = ok(s1, probe(out))
    log(f"smooth_clip: {os.path.basename(inp)} {ss:.2f}+{t:.2f}s: {len(fs)} frames -> {len(keep)} unique -> {D:.2f}s @30 fps CFR {s1} {'OK' if good else 'STILL ROUGH'}"); return good
def ok(s, fps): return s["still"] or (s["dup"] <= 0.03 and s["jerk"] <= 0.30 and abs(fps[1] - 30) < 0.05)
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("inp"); ap.add_argument("out", nargs="?"); ap.add_argument("--ss", type=float, default=0); ap.add_argument("--t", type=float)
    ap.add_argument("--slow", type=float, default=1.0); ap.add_argument("--crop"); ap.add_argument("--check", action="store_true"); A = ap.parse_args()
    fps = probe(A.inp); s0 = stats(gray(A.inp, A.ss or None, A.t))
    print(f"before: r={fps[0]:.3f} avg={fps[1]:.3f} fps, {s0}")
    if A.check or not A.out: sys.exit(0 if ok(s0, fps) else 1)
    sys.exit(0 if smooth(A.inp, A.out, A.ss, A.t, A.slow, A.crop) else 1)
