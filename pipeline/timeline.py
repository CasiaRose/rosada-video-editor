"""keeps.json (raw video s) -> timeline.json: output length N, speed, and every word mapped to OUTPUT time.
Usage: python timeline.py   (needs keeps.json {"keeps": [[a,b],...]} and audio_medium.json)
Put manual transcript fixes in fixes.json: [{"op":"set","find":"$10","near":4.28,"t":"$10,000"},
  {"op":"insert_before","find":"currently","near":8.42,"t":"There","s":7.77,"e":8.08}, {"op":"delete","find":"you","near":49.86}, ...]
(fixes come from clip-pass ASR + listening; captions must spell names/brand/numbers right)."""
import json, os
cfg = json.load(open("config.json")); SPEED, FPS = cfg.get("speed", 1.1), cfg.get("fps", 30)
K = json.load(open("keeps.json"))["keeps"]
def out(x):
    o = 0
    for a, b in K:
        if x < a: return o / SPEED
        if x <= b: return (o + x - a) / SPEED
        o += b - a
    return o / SPEED
TOTAL = out(K[-1][1]); N = round(TOTAL * FPS)
M = []
for s in json.load(open("audio_medium.json")):
    for w in s["words"]:
        t = w["w"].strip()
        if M and t.startswith(",000"): M[-1]["t"] += t; M[-1]["e"] = w["e"]; continue   # Whisper splits "$10" ",000"
        M.append(dict(t=t, s=w["s"], e=w["e"]))
def find(t, near): return min((i for i, w in enumerate(M) if w["t"].strip(",.?!").lower() == t.strip(",.?!").lower()), key=lambda i: abs(M[i]["s"] - near))
for fx in (json.load(open("fixes.json")) if os.path.exists("fixes.json") else []):
    i = find(fx["find"], fx["near"])
    if fx["op"] == "set": M[i].update({k: fx[k] for k in ("t", "s", "e") if k in fx})
    elif fx["op"] == "insert_before": M.insert(i, dict(t=fx["t"], s=fx["s"], e=fx["e"]))
    elif fx["op"] == "insert_after": M.insert(i + 1, dict(t=fx["t"], s=fx["s"], e=fx["e"]))
    elif fx["op"] == "delete": del M[i]
M = [w for w in M if any(a - 0.05 <= w["s"] <= b for a, b in K)]          # drop words that fall in cut regions
words = []
for i, w in enumerate(M):
    s = out(w["s"]); nxt = out(M[i + 1]["s"]) if i + 1 < len(M) else TOTAL
    words.append(dict(i=i, t=w["t"], s=round(s, 3), e=round(max(min(out(w["e"]), nxt), s + 0.12), 3), raw=w["s"]))
json.dump(dict(keeps=K, total=TOTAL, N=N, speed=SPEED, fps=FPS, words=words), open("timeline.json", "w"), indent=1)
print(N, round(TOTAL, 3)); print(" ".join(w["t"] for w in words))
