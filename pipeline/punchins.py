#!/usr/bin/env python3
"""Stepped punch-ins: plain zoom only, no overlays. No extra Python packages: ffmpeg zoompan.
Each punch: 1.00 -> 1.12 on the emphasis word onset (4-frame smoothstep) -> 1.20 one beat later
-> eases back to 1.00 over 8 frames INSIDE the next silence gap (or is held until the next B-roll/panel covers it). v3: no hard resets (they read as jump cuts).
Face jump cuts (--joins) get a hard 1.00<->1.12 step exactly on the join instead of a glitch.

  # A) automatic from Whisper words (list of {"w","s","e"} in OUTPUT seconds, or a faster-whisper JSON with segments[].words[])
  python3 punchins.py in.mp4 out.mp4 --words words.json --emphasis "$10,000;six;Alex;sell" --skip 0-2.8,9.3-12.5
  # B) explicit cue list: [{"t": 4.2, "t2": 4.8, "end": 6.0}, ...]   (t2/end optional)
  python3 punchins.py in.mp4 out.mp4 --cues punch.json
Options: --anchor 540,740 (zoom centre = her eye line, px in the 1080x1920 frame) --every 3.0 (min seconds between punches)
Writes out.mp4 and out.mp4.punchins.json = {"punchins":[...], "cues":[{"t","event":"punch_in_small"|"punch_in_big"}]} -> merge the cues into finish's cues.json
(make_edit.py does this for you). Rules: punch on FACE shots only (pass B-roll/full-panel ranges in --skip), 1 punch per 3-6 s, at least 3 per 30 s."""
import sys, json, argparse, subprocess, re
ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("dst")
ap.add_argument("--words"); ap.add_argument("--emphasis", default=""); ap.add_argument("--cues"); ap.add_argument("--skip", default="")
ap.add_argument("--anchor", default="540,740"); ap.add_argument("--every", type=float, default=2.5); ap.add_argument("--crf", default="17")
ap.add_argument("--joins", help="JSON list of face jump-cut times (output s): each gets a HARD zoom step exactly on the join, which hides the jump")
A = ap.parse_args(); FPS = 30
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", A.src], capture_output=True, text=True).stdout)
skip = [tuple(map(float, r.split("-"))) for r in A.skip.split(",") if r.strip()]
inskip = lambda a, b: any(not (b <= s or a >= e) for s, e in skip)
def load_words(p):
    J = json.load(open(p))
    if isinstance(J, dict) and "segments" in J: return [dict(w=w["word"].strip(), s=w["start"], e=w["end"]) for s in J["segments"] for w in s.get("words", [])]
    return [dict(w=w.get("w") or w.get("word") or w.get("t"), s=w["s"] if "s" in w else w["start"], e=w["e"] if "e" in w else w["end"]) for w in J]
P = []; W = load_words(A.words) if A.words else []
gaps = [(W[k]["e"], W[k + 1]["s"]) for k in range(len(W) - 1) if W[k + 1]["s"] - W[k]["e"] >= 0.15] + ([(W[-1]["e"], dur)] if W else [])
def soft_end(t0, lo=1.2, hi=3.2):
    """end time for a zoom that started at t0: the first silence gap after t0+lo (ease-out finishes inside it); if a B-roll/panel starts
    within 1.8 s after that, hold the zoom until it (the reset is then hidden under the cover). Returns (end, hidden)."""
    g = next(((a, b) for a, b in gaps if a >= t0 + lo and a <= t0 + hi), None)
    end = (g[0] + min(0.27, max(0.12, g[1] - g[0]))) if g else t0 + hi
    nxt = min([a for a, b in skip if a > t0], default=99)
    if nxt - end < 1.8 or end > nxt: return round(nxt, 3), True
    return round(min(end, dur - 0.05), 3), False
joins = json.load(open(A.joins)) if A.joins else []
for j in joins:
    if inskip(j - 0.05, j + 0.05): continue
    end, hid = soft_end(j); P.append(dict(t=round(j, 3), t2=None, end=end, hidden=hid, hard=True, word="(join)"))
if A.cues:
    C = json.load(open(A.cues)); C = C.get("punchins", C) if isinstance(C, dict) else C
    for c in C:
        end, hid = soft_end(c["t"]) if "end" not in c else (c["end"], False)
        P.append(dict(t=c["t"], t2=c.get("t2", c["t"] + 0.6), end=end, hidden=hid, hard=False))
elif W:
    emph = [e.strip().lower() for e in A.emphasis.split(";") if e.strip()]
    norm = lambda s: re.sub(r"[^\w$]", "", s.lower())
    def is_emph(w):
        n = norm(w["w"])
        return (w["w"].startswith("*")) or any(n == norm(e) or (len(norm(e)) > 3 and norm(e) in n) for e in emph) or ("$" in w["w"]) or bool(re.search(r"\d", n))
    last = -99
    for i, w in enumerate(W):
        if not is_emph(w) or w["s"] - last < A.every or inskip(w["s"] - 0.1, w["s"] + 0.8): continue
        if any(p["t"] - 0.3 <= w["s"] <= p["end"] + 0.6 for p in P): continue          # never on top of a join zoom
        end, hid = soft_end(w["s"])
        t2 = W[i + 1]["s"] if i + 1 < len(W) and W[i + 1]["s"] < end - 0.6 else w["s"] + 0.45
        P.append(dict(t=round(w["s"], 3), t2=round(max(t2, w["s"] + 0.3), 3), end=end, hidden=hid, hard=False, word=w["w"])); last = w["s"]
elif not joins: sys.exit("give --words, --cues or --joins")
P = sorted([p for p in P if p["end"] - p["t"] >= 0.7], key=lambda p: p["t"])
for k in range(len(P) - 1): P[k]["end"] = min(P[k]["end"], P[k + 1]["t"] - 0.02)
for p in P:
    if p["t2"] is not None and p["t2"] > p["end"] - 0.5: p["t2"] = None
if not P: sys.exit("punchins: no punch-ins found (add --emphasis words or a --cues list)")
ax, ay = map(float, A.anchor.split(","))
ss = lambda x: f"(clip({x},0,1)*clip({x},0,1)*(3-2*clip({x},0,1)))"
T = f"(on/{FPS})"
def term(p):
    up = f"gte({T},{p['t']})" if p["hard"] else ss(f"({T}-{p['t']}+0.0334)/0.1334")
    t2 = p["t2"]; lvl = f"0.12*{up}" + (f"+0.08*{ss(f'({T}-{t2}+0.0334)/0.1334')}" if t2 is not None else "")
    down = "1" if p["hidden"] else f"(1-{ss(f'({T}-{p['end']}+0.267)/0.267')})"
    return f"+between({T},{p['t']},{p['end']})*({lvl})*{down}"
z = "1" + "".join(term(p) for p in P)
zp = f"zoompan=z='{z}':x='{ax}-{ax}/zoom':y='{ay}-{ay}/zoom':d=1:s=1080x1920:fps={FPS}"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", A.src, "-vf", zp + ",format=yuv420p", "-map", "0:v", "-map", "0:a?", "-c:v", "libx264", "-crf", A.crf, "-preset", "medium", "-c:a", "copy", "-t", str(dur), A.dst], check=True)
cues = []
for p in P:
    cues.append({"t": p["t"], "event": "punch_in_big" if p["t2"] is not None else "punch_in_small"})   # one sound per punch (a 2nd pop 0.5 s later gets masked)
json.dump({"punchins": P, "cues": cues}, open(A.dst + ".punchins.json", "w"), indent=1)
print(f"punchins: {len(P)} punch-ins ->", ", ".join(f"{p['t']:.2f}-{p['end']:.2f}s {p.get('word','')}".strip() for p in P))
