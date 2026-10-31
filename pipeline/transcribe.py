"""Word-level transcription with faster-whisper (CTranslate2). Usage:
   python transcribe.py audio/audio_vc_16k.wav [model=medium] [out=audio_medium.json] [t0 t1]
Run 'small' first for a quick topic read, then 'medium' for the timings you build on. Optional t0/t1 re-transcribes a
short CLIP (clip pass): use it where the full pass dropped words ("$10" for "$10,000", swallowed "There are", "AI").
Output: [{start,end,text,words:[{w,s,e,p}]}] in VIDEO seconds (input must already be on the video clock)."""
import json, sys, wave, numpy as np, os
from faster_whisper import WhisperModel
cfg = json.load(open("config.json")) if os.path.exists("config.json") else {}
src = sys.argv[1]; model = sys.argv[2] if len(sys.argv) > 2 else cfg.get("whisper_model", "medium")
out = sys.argv[3] if len(sys.argv) > 3 else f"audio_{model}.json"
t0 = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0; t1 = float(sys.argv[5]) if len(sys.argv) > 5 else None
m = WhisperModel(model, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
wf = wave.open(src); sr = wf.getframerate(); a = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768
a = a[int(t0 * sr): int(t1 * sr) if t1 else None]
segs, info = m.transcribe(a, language="en", word_timestamps=True, beam_size=5, condition_on_previous_text=False,
                          vad_filter=False, hotwords=cfg.get("hotwords"), initial_prompt=cfg.get("initial_prompt"))
res = []
for s in segs:
    res.append(dict(start=round(t0 + s.start, 3), end=round(t0 + s.end, 3), text=s.text,
                    words=[dict(w=w.word, s=round(t0 + w.start, 3), e=round(t0 + w.end, 3), p=round(w.probability, 3)) for w in s.words]))
    print(f"[{t0 + s.start:6.2f}-{t0 + s.end:6.2f}] {s.text}", flush=True)
json.dump(res, open(out, "w"), indent=1)
with open(out.replace(".json", "_words.txt"), "w") as f:
    for s in res:
        for w in s["words"]: f.write(f"{w['s']:7.3f} {w['e']:7.3f} {w['p']:.2f} {w['w'].strip()}\n")
print("wrote", out)
