"""Silence map -> keep list (raw video seconds). Usage: python silences_keeps.py [audio/raw48_vc.wav]
Rule (approved house style): every silence longer than silence_min (0.40 s) is cut down to ~2*pad (0.22 s, 0.11 s each side);
micro-pauses under 0.40 s stay (they keep her rhythm). keep_in = ~0.3 s before the first voiced word.
keep_out = last word END from the WAVEFORM (not Whisper; Whisper ends are early on fricatives) + enough room that
(keep_out - last_word_end)/speed >= 0.8 s, and before any blink / lean / reach-for-the-phone at the tail.
Writes scratch/silences.json, keeps_draft.json, keep_table.md. ALWAYS eyeball the table and the waveform at each join."""
import json, subprocess, sys, re, os
cfg = json.load(open("config.json")); SP = cfg.get("speed", 1.1)
wav = sys.argv[1] if len(sys.argv) > 1 else "audio/raw48_vc.wav"
r = subprocess.run(["ffmpeg", "-nostats", "-i", wav, "-af", f"silencedetect=noise={cfg.get('silence_db', -40)}dB:d=0.12", "-f", "null", "-"], capture_output=True, text=True).stderr
st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r)]; en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r)]
S = list(zip(st, en)); os.makedirs("scratch", exist_ok=True); json.dump(S, open("scratch/silences.json", "w"))
words = []
for f in ("audio_medium.json",):
    if os.path.exists(f): words = [w for s in json.load(open(f)) for w in s["words"]]
first = words[0]["s"] if words else (S[0][1] if S else 0); last_e = words[-1]["e"] if words else None
START = cfg.get("keep_in") or max(0, round(first - 0.30, 3))
END = cfg.get("keep_out") or (round(last_e + 0.30 + cfg.get("last_word_hold_min", 0.8) * SP, 3) if last_e else en[-1])
PAD, MIN = cfg.get("silence_pad", 0.11), cfg.get("silence_min", 0.40)
cuts = [(s + PAD, e - PAD) for s, e in S if s > START + 0.1 and e < END - 0.1 and e - s > MIN]
keeps = []; t = START
for a, b in cuts: keeps.append([round(t, 3), round(a, 3)]); t = b
keeps.append([round(t, 3), END])
def out(x):
    o = 0
    for a, b in keeps:
        if x < a: return o / SP
        if x <= b: return (o + x - a) / SP
        o += b - a
    return o / SP
total = out(END)
json.dump(dict(keeps=keeps, total=total, N=round(total * cfg.get("fps", 30))), open("keeps_draft.json", "w"), indent=1)
L = ["| # | keep raw (s) | out (s) | words |", "|---|---|---|---|"]
for i, (a, b) in enumerate(keeps):
    ws = " ".join(w["w"].strip() for w in words if a - 0.05 <= (w["s"] + w["e"]) / 2 < b)
    L.append(f"| K{i+1} | {a:.2f}-{b:.2f} | {out(a):.2f}-{out(b):.2f} | {ws} |")
if last_e: L.append(f"\nLast word ends raw {last_e:.2f} (Whisper - verify on waveform); hold after it = {(END - last_e) / SP:.2f} s (need >= {cfg.get('last_word_hold_min', 0.8)})")
open("keep_table.md", "w").write("\n".join(L) + f"\n\nTotal {total:.2f} s ({round(total * 30)} fr)\n"); print("\n".join(L)); print("total", round(total, 3))
