#!/usr/bin/env python3
"""Cut a talking-head take. Joins snap into silence gaps between words.
Speed comes from --speed or from a style profile's pacing.speed (default 1.0).
Face shots shorter than the profile minimum are reported for the recipe to cover.
  python3 cut_vo.py raw.mov raw_words.json keeps.json out_dir [--offset 0.775] [--fix "misheard=intended"]
raw_words: faster-whisper JSON or [{"w","s","e"}] in AUDIO seconds of the raw file (--offset = audio start_time, iPhone ~0.775).
keeps.json: [[start, end], ...] raw VIDEO seconds (rough is fine; they get snapped).
Writes out_dir/aroll_vo.mov, words.json (output seconds), joins.json (output seconds of every face join), cut_report.txt."""
import sys, os, json, subprocess, argparse, numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("raw"); ap.add_argument("words"); ap.add_argument("keeps"); ap.add_argument("out")
ap.add_argument("--offset", type=float, default=0.0); ap.add_argument("--speed", type=float, default=None); ap.add_argument("--style", default=""); ap.add_argument("--fix", default=""); A = ap.parse_args()
if A.style:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from style.profile import load_profile
    A.speed = load_profile(A.style)["pacing"]["speed"]
elif A.speed is None:
    A.speed = 1.0
os.makedirs(A.out, exist_ok=True); SR = 16000
J = json.load(open(A.words))
W = [dict(w=w["word"].strip(), s=w["start"] + A.offset, e=w["end"] + A.offset) for s in J["segments"] for w in s["words"]] if isinstance(J, dict) \
    else [dict(w=(w.get("w") or w.get("word")).strip(), s=w.get("s", w.get("start")) + A.offset, e=w.get("e", w.get("end")) + A.offset) for w in J]
au = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", A.raw, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout, np.float32)
au = np.concatenate([np.zeros(int(A.offset * SR), np.float32), au])        # audio on the video clock
hop = 160; env = 20 * np.log10(np.array([np.sqrt(np.mean(au[i:i + 640] ** 2) + 1e-12) for i in range(0, len(au) - 640, hop)]))
speech = np.percentile(env, 90)
inword = lambda t: any(w["s"] + 0.03 < t < w["e"] - 0.03 for w in W)
def snap(t):
    best = None
    for c in np.arange(t - 0.25, t + 0.25, 0.01):
        if inword(c) or c < 0: continue
        i = int(c * 100); e = env[max(0, i - 2):i + 2].mean() if i < len(env) else -99
        if best is None or e < best[1]: best = (round(float(c), 3), e)
    if best is None or best[1] > speech - 12: return None, best
    return best[0], best
K = json.load(open(A.keeps)); SK = []; rep = []
for a, b in K:
    sa, ia = snap(a); sb, ib = snap(b)
    if sa is None or sb is None: sys.exit(f"cut_vo: keep [{a},{b}] has no silence gap near its {'start' if sa is None else 'end'} -> move it to a pause between words")
    SK.append((sa, sb)); rep.append(f"keep {a:.2f}-{b:.2f} -> {sa:.2f}-{sb:.2f}")
fc, cat = "", ""
for i, (a, b) in enumerate(SK):
    fc += f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS[v{i}];[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st={max(0,b-a-0.03)}:d=0.03[a{i}];"; cat += f"[v{i}][a{i}]"
fc += f"{cat}concat=n={len(SK)}:v=1:a=1[v][a];[v]setpts=PTS/{A.speed},fps=30[vo];[a]atempo={A.speed},aresample=48000[ao]"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", A.raw, "-filter_complex", fc, "-map", "[vo]", "-map", "[ao]", "-c:v", "libx264", "-crf", "17", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", os.path.join(A.out, "aroll_vo.mov")], check=True)
out, cum, joins = [], 0.0, []
for k, (a, b) in enumerate(SK):
    for w in W:
        m = (w["s"] + w["e"]) / 2
        if a <= m < b: out.append(dict(w=w["w"], s=round((cum + max(a, w["s"]) - a) / A.speed, 3), e=round((cum + min(b, w["e"]) - a) / A.speed, 3)))
    cum += b - a
    if k < len(SK) - 1: joins.append(round(cum / A.speed, 3))
m2 = []
for x in out:
    if m2 and x["w"].startswith(","): m2[-1]["w"] += x["w"]; m2[-1]["e"] = x["e"]
    else: m2.append(x)
fx = dict(kv.split("=") for kv in A.fix.split(",") if "=" in kv)
for x in m2:
    core = x["w"].strip(",.?!"); x["w"] = x["w"].replace(core, fx.get(core, core)) if core else x["w"]
json.dump(m2, open(os.path.join(A.out, "words.json"), "w"), indent=0); json.dump(joins, open(os.path.join(A.out, "joins.json"), "w"))
sh = np.diff([0] + joins + [cum / A.speed])
rep += [f"joins (output s): {joins}", "face shot lengths: " + ", ".join(f"{x:.2f}" for x in sh),
        "shots < 2.5 s (cover these with B-roll/panel in the recipe, or merge keeps): " + str([(round(([0]+joins)[i],2), round(x,2)) for i, x in enumerate(sh) if x < 2.5])]
open(os.path.join(A.out, "cut_report.txt"), "w").write("\n".join(rep) + "\n"); print("\n".join(rep))
